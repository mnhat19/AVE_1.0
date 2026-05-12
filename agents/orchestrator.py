from __future__ import annotations

import json
import operator
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Annotated, List, TypedDict

from langgraph.graph import END, StateGraph

from agents.audit_agent import (
    attach_evidence_links,
    build_risk_control_matrix,
    build_risk_register,
    cross_validate_evidence,
    generate_audit_findings,
    run_ageing_analysis,
    run_reconciliation_checks,
    run_test_of_controls,
)
from services.consolidator import consolidate_findings
from services.normalizer import detect_table_schema, normalize_table
from services.anomaly_detector import detect_journal_anomalies, detect_trial_balance_anomalies
from agents.doc_agent import build_internal_process_map, classify_document, extract_process_info
from config.llm import get_llm_client
from db.database import SessionLocal
from db.models import AccuracyMetric
from db.models import AuditScope as AuditScopeModel
from db.models import ExecutionPlan as ExecutionPlanModel
from services.extractor import extract
from services.output_generator import (
    generate_evidence_pdf,
    generate_issue_log,
    generate_memo,
    generate_risk_register,
    generate_versioned_notes,
)
from services.task_dispatcher import dispatch_tasks
from services.feedback_processor import load_relevant_knowledge


class AuditState(TypedDict):
    session_id: str
    stage: str
    file_records: List[dict]
    audit_tasks: List[dict]
    execution_plan: dict
    extracted_docs: List[dict]
    normalized_tables: List[dict]
    anomaly_flags: List[dict]
    audit_findings: List[dict]
    risk_entries: List[dict]
    consolidated_findings: List[dict]
    control_test_results: List[dict]
    risk_control_matrix: List[dict]
    control_candidates: List[str]
    fieldwork_findings: List[dict]
    interim_findings: List[dict]
    knowledge_entries: List[dict]
    versioned_notes: Annotated[List[str], operator.add]
    errors: List[str]
    output_paths: dict


def _has_formats(file_records: list[dict], formats: set[str]) -> bool:
    return any(record.get("format") in formats for record in file_records)


def _build_tasks(session_id: str, stage: str, file_records: list[dict]) -> list[dict]:
    tasks: list[dict] = []
    has_tables = _has_formats(file_records, {"XLSX", "CSV", "TXT"})
    stage = stage or "BOTH"
    include_interim = stage in {"INTERIM", "BOTH"}
    include_fieldwork = stage in {"FIELDWORK", "BOTH"}

    def add_task(task_type: str, agent: str, priority: int, deps: list[str] | None = None) -> str:
        task_id = f"TASK-{session_id[:4].upper()}-{len(tasks) + 1:03d}"
        tasks.append(
            {
                "id": task_id,
                "task_type": task_type,
                "priority": priority,
                "assigned_agent": agent,
                "status": "PENDING",
                "dependencies": deps or [],
            }
        )
        return task_id

    extract_id = add_task("EXTRACT_DOCUMENTS", "DOC_AGENT", 1)
    normalize_id = None
    anomaly_id = None
    if has_tables:
        normalize_id = add_task("NORMALIZE_TABLES", "DATA_AGENT", 2, [extract_id])
        anomaly_id = add_task("ANOMALY_DETECTION", "DATA_AGENT", 3, [normalize_id])

    task_refs: list[str | None] = [anomaly_id or extract_id]

    if include_interim:
        task_refs.append(add_task("TEST_OF_CONTROLS", "AUDIT_AGENT", 4, [normalize_id or extract_id]))
        task_refs.append(add_task("RISK_MATRIX", "AUDIT_AGENT", 4, [extract_id]))

    if include_fieldwork:
        task_refs.append(add_task("RECONCILIATION", "AUDIT_AGENT", 4, [normalize_id or extract_id]))
        task_refs.append(add_task("AGEING_ANALYSIS", "AUDIT_AGENT", 4, [normalize_id or extract_id]))
        task_refs.append(add_task("EVIDENCE_VALIDATION", "DOC_AGENT", 4, [extract_id]))

    reasoning_deps = [task_id for task_id in task_refs if task_id]
    reasoning_id = add_task("AUDIT_REASONING", "AUDIT_AGENT", 5, reasoning_deps)
    consolidation_id = add_task("CONSOLIDATION", "AUDIT_AGENT", 6, [reasoning_id])
    add_task("GENERATE_OUTPUTS", "AUDIT_AGENT", 7, [consolidation_id])

    return tasks


async def build_audit_scope(session_id: str, stage: str, file_records: list[dict]) -> dict:
    """Derive the audit scope from the current document bundle and metadata."""
    filenames = [record.get("filename") for record in file_records if record.get("filename")]
    formats = sorted({record.get("format") for record in file_records if record.get("format")})
    llm = get_llm_client("reasoning")
    prompt = (
        "Analyze the audit files and propose audit objectives and a risk profile.\n"
        f"Stage: {stage}\n"
        f"Filenames: {filenames}\n"
        f"Formats: {formats}\n\n"
        "Return JSON:\n"
        "{\n"
        '  "objectives": ["objective 1", "objective 2"],\n'
        '  "risk_profile": "summary of inherent risk level"\n'
        "}\n"
        "Return only valid JSON."
    )
    raw = await llm(prompt)
    objectives: list[str] = []
    risk_profile = ""
    try:
        parsed = json.loads(raw.strip())
        if isinstance(parsed, dict):
            objectives = parsed.get("objectives") or []
            risk_profile = parsed.get("risk_profile") or ""
    except Exception:
        objectives = [f"Assess {stage} audit readiness", "Validate core financial data sources"]
        risk_profile = "MEDIUM"

    if not isinstance(objectives, list):
        objectives = []

    return {
        "session_id": session_id,
        "stage": stage,
        "objectives": objectives,
        "risk_profile": risk_profile or "MEDIUM",
    }


def generate_execution_plan(audit_scope: dict, file_records: list[dict]) -> dict:
    """Create a task plan with priorities and dependencies from the audit scope."""
    stage = audit_scope.get("stage") or "BOTH"
    tasks = _build_tasks(audit_scope.get("session_id", ""), stage, file_records)
    ordered = [task["id"] for task in sorted(tasks, key=lambda t: t["priority"])]
    return {
        "scope": audit_scope,
        "tasks": tasks,
        "ordered_task_ids": ordered,
    }


def _save_audit_scope(scope: dict) -> str:
    """Persist the audit scope so downstream phases can reference it."""
    db = SessionLocal()
    try:
        record = AuditScopeModel(
            session_id=scope.get("session_id"),
            objectives=scope.get("objectives") or [],
            stage=scope.get("stage"),
            risk_profile=scope.get("risk_profile"),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record.id
    finally:
        db.close()


def _save_execution_plan(audit_scope_id: str, plan: dict) -> None:
    """Store the execution plan to keep a versioned record of task planning."""
    db = SessionLocal()
    try:
        record = ExecutionPlanModel(
            audit_scope_id=audit_scope_id,
            tasks=plan,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
    finally:
        db.close()


def _apply_accuracy_priorities(session_id: str, execution_plan: dict) -> dict:
    db = SessionLocal()
    try:
        metrics = db.query(AccuracyMetric).filter_by(session_id=session_id).all()
    finally:
        db.close()

    if not metrics:
        return execution_plan

    category_map = {
        "TEST_OF_CONTROLS": {"TEST_OF_CONTROLS", "RISK_MATRIX"},
        "FIELDWORK_CHECKS": {"RECONCILIATION", "AGEING_ANALYSIS", "EVIDENCE_VALIDATION"},
        "GENERAL": {"AUDIT_REASONING"},
    }

    task_priority = {}
    for metric in metrics:
        if metric.accuracy_rate is None or metric.accuracy_rate >= 0.6:
            continue
        targets = category_map.get(metric.finding_category or "GENERAL", set())
        for task_type in targets:
            task_priority[task_type] = min(task_priority.get(task_type, 3), 1)

    if not task_priority:
        return execution_plan

    for task in execution_plan.get("tasks", []):
        task_type = task.get("task_type")
        if task_type in task_priority:
            task["priority"] = task_priority[task_type]

    ordered = [task["id"] for task in sorted(execution_plan["tasks"], key=lambda t: t["priority"]) ]
    execution_plan["ordered_task_ids"] = ordered
    return execution_plan


def on_task_completed(task: dict, result: dict, execution_plan: dict) -> dict:
    """Autonomously add follow-up tasks when new risks emerge from task results."""
    if not result or not result.get("has_unexpected_risk"):
        return execution_plan

    new_risk = result.get("new_risk", "unclassified")
    additional_task = {
        "id": f"TASK-AUTO-{len(execution_plan.get('tasks', [])) + 1:03d}",
        "task_type": "DEEP_DIVE_INVESTIGATION",
        "priority": 1,
        "assigned_agent": "AUDIT_AGENT",
        "status": "PENDING",
        "dependencies": [task.get("id")] if task else [],
        "description": f"Deep dive: {new_risk}",
    }
    execution_plan.setdefault("tasks", []).append(additional_task)
    ordered = sorted(execution_plan.get("tasks", []), key=lambda t: t["priority"])
    execution_plan["ordered_task_ids"] = [item.get("id") for item in ordered]
    return execution_plan


def _mark_task_status(tasks: list[dict], task_type: str, status: str) -> None:
    for task in tasks:
        if task.get("task_type") == task_type:
            task["status"] = status

def _collect_controls(extracted_docs: list[dict]) -> list[str]:
    controls: list[str] = []
    for doc in extracted_docs:
        if not isinstance(doc, dict):
            continue
        classification = doc.get("classification", {})
        if not isinstance(classification, dict):
            classification = {}
        controls.extend(classification.get("internal_controls_mentioned", []))
        process_info = doc.get("process_info") or {}
        if not isinstance(process_info, dict):
            process_info = {}
        for control in process_info.get("key_controls", []) or []:
            if isinstance(control, dict):
                desc = control.get("description") or control.get("control_id")
                if desc:
                    controls.append(desc)
            else:
                controls.append(str(control))
        for objective in process_info.get("control_objectives", []) or []:
            controls.append(f"objective:{objective}")
    return controls


async def node_plan_tasks(state: AuditState) -> AuditState:
    audit_scope = await build_audit_scope(state["session_id"], state["stage"], state["file_records"])
    execution_plan = generate_execution_plan(audit_scope, state["file_records"])
    execution_plan = _apply_accuracy_priorities(state["session_id"], execution_plan)
    dispatch_map = dispatch_tasks(execution_plan["tasks"])
    execution_plan["dispatch_map"] = dispatch_map

    knowledge_entries = [
        {
            "pattern_type": entry.pattern_type,
            "description": entry.description,
            "confidence": entry.confidence,
            "applicable_stages": entry.applicable_stages,
        }
        for entry in load_relevant_knowledge(state["stage"])
    ]

    scope_id = _save_audit_scope(audit_scope)
    _save_execution_plan(scope_id, execution_plan)
    return {
        **state,
        "audit_tasks": execution_plan["tasks"],
        "execution_plan": execution_plan,
        "knowledge_entries": knowledge_entries,
        "versioned_notes": [f"Planned {len(execution_plan['tasks'])} tasks"],
    }


async def node_extract_documents(state: AuditState) -> AuditState:
    extracted = []
    for record in state["file_records"]:
        raw = extract(SimpleNamespace(**record))
        if raw.get("type") == "text" and raw.get("content"):
            classification = await classify_document(raw["content"])
            if not isinstance(classification, dict):
                classification = {}
            doc_type = classification.get("doc_type")
            process_info = None
            if doc_type in {"SOP", "PROCESS_DESC", "WALKTHROUGH"}:
                process_info = await extract_process_info(raw["content"])
                if not isinstance(process_info, dict):
                    process_info = {}
            process_map_id = None
            if process_info and doc_type in {"SOP", "PROCESS_DESC", "WALKTHROUGH"}:
                process_map = build_internal_process_map(
                    state["session_id"],
                    record.get("id"),
                    process_info,
                )
                process_map_id = process_map.get("id") if isinstance(process_map, dict) else None
            extracted.append(
                {
                    "file_id": record.get("id"),
                    "filename": record.get("filename"),
                    "format": record.get("format"),
                    "raw": raw,
                    "classification": classification,
                    "process_info": process_info,
                    "process_map_id": process_map_id,
                }
            )
        else:
            extracted.append(
                {
                    "file_id": record.get("id"),
                    "filename": record.get("filename"),
                    "format": record.get("format"),
                    "raw": raw,
                    "classification": {},
                    "process_info": None,
                }
            )
    _mark_task_status(state.get("audit_tasks", []), "EXTRACT_DOCUMENTS", "COMPLETED")
    return {
        **state,
        "audit_tasks": state.get("audit_tasks", []),
        "extracted_docs": extracted,
        "versioned_notes": [f"Extracted {len(extracted)} documents"],
    }


async def node_normalize_tables(state: AuditState) -> AuditState:
    import pandas as pd

    normalized = []
    for doc in state["extracted_docs"]:
        if not isinstance(doc, dict):
            continue
        raw = doc.get("raw", {})
        if not isinstance(raw, dict):
            continue
        if raw.get("type") == "table":
            content = raw.get("content")
            if isinstance(content, dict):
                for sheet_name, rows in content.items():
                    if not rows:
                        continue
                    df = pd.DataFrame(rows)
                    schema = await detect_table_schema(list(df.columns), rows[:3])
                    df_norm = normalize_table(df, schema)
                    normalized.append(
                        {
                            "file_id": doc.get("file_id"),
                            "sheet_name": sheet_name,
                            "schema": schema,
                            "data": df_norm.to_dict(orient="records"),
                            "columns": list(df_norm.columns),
                            "rows_count": len(df_norm),
                            "source_page": None,
                        }
                    )
            elif isinstance(content, list):
                # CSV
                rows = content
                df = pd.DataFrame(rows)
                schema = await detect_table_schema(list(df.columns), rows[:3])
                df_norm = normalize_table(df, schema)
                normalized.append(
                    {
                        "file_id": doc.get("file_id"),
                        "sheet_name": "csv_sheet",
                        "schema": schema,
                        "data": df_norm.to_dict(orient="records"),
                        "columns": list(df_norm.columns),
                        "rows_count": len(df_norm),
                        "source_page": None,
                    }
                )

        tables = raw.get("tables") or []
        for table_info in tables:
            if not isinstance(table_info, dict):
                continue
            rows = table_info.get("rows") or []
            if len(rows) < 2:
                continue
            header = rows[0]
            data_rows = rows[1:]
            df = pd.DataFrame(data_rows, columns=header)
            schema = await detect_table_schema(list(df.columns), data_rows[:3])
            df_norm = normalize_table(df, schema)
            page = table_info.get("page")
            table_index = table_info.get("index")
            sheet_name = f"page_{page}_table_{table_index}"
            normalized.append(
                {
                    "file_id": doc.get("file_id"),
                    "sheet_name": sheet_name,
                    "schema": schema,
                    "data": df_norm.to_dict(orient="records"),
                    "columns": list(df_norm.columns),
                    "rows_count": len(df_norm),
                    "source_page": page,
                }
            )
    _mark_task_status(state.get("audit_tasks", []), "NORMALIZE_TABLES", "COMPLETED")
    return {
        **state,
        "audit_tasks": state.get("audit_tasks", []),
        "normalized_tables": normalized,
        "versioned_notes": [f"Normalized {len(normalized)} tables"],
    }


async def node_detect_anomalies(state: AuditState) -> AuditState:
    import pandas as pd
    all_flags = []
    for table in state["normalized_tables"]:
        if not isinstance(table, dict):
            continue
        df = pd.DataFrame(table["data"], columns=table.get("columns", []))
        schema_type = table.get("schema", {}).get("schema_type", "OTHER")
        if schema_type == "JOURNAL":
            flags = detect_journal_anomalies(df)
        elif schema_type == "TRIAL_BALANCE":
            flags = detect_trial_balance_anomalies(df)
        else:
            flags = []
        for flag in flags:
            flag["source_file_id"] = table.get("file_id")
            flag["source_sheet"] = table.get("sheet_name")
            if table.get("source_page") is not None:
                flag["source_page"] = table.get("source_page")
        all_flags.extend(flags)
    _mark_task_status(state.get("audit_tasks", []), "ANOMALY_DETECTION", "COMPLETED")
    return {
        **state,
        "audit_tasks": state.get("audit_tasks", []),
        "anomaly_flags": all_flags,
        "versioned_notes": [f"Detected {len(all_flags)} anomaly flags"],
    }


async def node_test_controls(state: AuditState) -> AuditState:
    results = run_test_of_controls(state.get("normalized_tables", []))
    controls = _collect_controls(state.get("extracted_docs", []))
    matrix = build_risk_control_matrix(controls, results)
    _mark_task_status(state.get("audit_tasks", []), "TEST_OF_CONTROLS", "COMPLETED")
    _mark_task_status(state.get("audit_tasks", []), "RISK_MATRIX", "COMPLETED")
    return {
        **state,
        "audit_tasks": state.get("audit_tasks", []),
        "control_test_results": results,
        "risk_control_matrix": matrix,
        "control_candidates": controls,
        "versioned_notes": [f"Completed {len(results)} control tests"],
    }


async def node_fieldwork(state: AuditState) -> AuditState:
    if state.get("stage") not in {"FIELDWORK", "BOTH"}:
        return state

    findings = []
    findings.extend(run_reconciliation_checks(state.get("normalized_tables", [])))
    findings.extend(run_ageing_analysis(state.get("normalized_tables", [])))

    findings = cross_validate_evidence(state.get("extracted_docs", []), findings)

    _mark_task_status(state.get("audit_tasks", []), "RECONCILIATION", "COMPLETED")
    _mark_task_status(state.get("audit_tasks", []), "AGEING_ANALYSIS", "COMPLETED")
    _mark_task_status(state.get("audit_tasks", []), "EVIDENCE_VALIDATION", "COMPLETED")

    execution_plan = state.get("execution_plan", {})
    if any(finding.get("severity") in {"HIGH", "CRITICAL"} for finding in findings):
        updated_plan = on_task_completed(
            None,
            {"has_unexpected_risk": True, "new_risk": "Fieldwork discrepancy"},
            execution_plan,
        )
        execution_plan = updated_plan

    return {
        **state,
        "audit_tasks": state.get("audit_tasks", []),
        "fieldwork_findings": findings,
        "execution_plan": execution_plan,
        "versioned_notes": [f"Fieldwork checks generated {len(findings)} findings"],
    }


async def node_audit_reasoning(state: AuditState) -> AuditState:
    doc_summaries = []
    for doc in state["extracted_docs"]:
        if not isinstance(doc, dict):
            continue
        classification = doc.get("classification")
        if not isinstance(classification, dict):
            continue
        doc_summaries.append(
            {
                "filename": doc.get("filename"),
                "summary": classification.get("summary", ""),
            }
        )
    controls = _collect_controls(state["extracted_docs"])

    findings_raw = await generate_audit_findings(
        stage=state["stage"],
        doc_summaries=doc_summaries,
        anomaly_flags=state["anomaly_flags"],
        controls_identified=controls,
        control_test_results=state.get("control_test_results", []),
        knowledge_entries=state.get("knowledge_entries", []),
    )
    if state["stage"] == "BOTH":
        for finding in findings_raw:
            if isinstance(finding, dict):
                finding.setdefault("stage", "INTERIM")
    else:
        for finding in findings_raw:
            if isinstance(finding, dict):
                finding.setdefault("stage", state["stage"])
    findings_with_evidence = attach_evidence_links(findings_raw, state["anomaly_flags"])
    if state.get("fieldwork_findings"):
        findings_with_evidence.extend(state.get("fieldwork_findings", []))
    risk_entries = build_risk_register(findings_with_evidence, state["session_id"])
    _mark_task_status(state.get("audit_tasks", []), "AUDIT_REASONING", "COMPLETED")
    return {
        **state,
        "audit_tasks": state.get("audit_tasks", []),
        "audit_findings": findings_with_evidence,
        "risk_entries": risk_entries,
        "control_candidates": controls,
        "interim_findings": [f for f in findings_with_evidence if f.get("stage") == "INTERIM"],
        "versioned_notes": [
            f"Identified {len(controls)} controls from process docs",
            f"Generated {len(findings_raw)} audit findings",
        ],
    }


async def node_consolidation(state: AuditState) -> AuditState:
    fieldwork_findings = [f for f in state.get("audit_findings", []) if f.get("stage") == "FIELDWORK"]
    interim_findings = state.get("interim_findings", [])

    for idx, finding in enumerate(interim_findings, 1):
        finding["index"] = idx
    for idx, finding in enumerate(fieldwork_findings, 1):
        finding["index"] = idx

    consolidated = consolidate_findings(interim_findings, fieldwork_findings)
    _mark_task_status(state.get("audit_tasks", []), "CONSOLIDATION", "COMPLETED")
    return {
        **state,
        "consolidated_findings": consolidated,
        "versioned_notes": [f"Consolidated {len(consolidated)} findings"],
    }


async def node_generate_outputs(state: AuditState) -> AuditState:
    issue_log_path = await generate_issue_log(state)
    memo_path = await generate_memo(state)
    risk_register_path = await generate_risk_register(state)
    evidence_path = await generate_evidence_pdf(state)
    notes_path = await generate_versioned_notes(state)
    _mark_task_status(state.get("audit_tasks", []), "GENERATE_OUTPUTS", "COMPLETED")
    return {
        **state,
        "audit_tasks": state.get("audit_tasks", []),
        "output_paths": {
            "issue_log": issue_log_path,
            "memo": memo_path,
            "risk_register": risk_register_path,
            "evidence_pdf": evidence_path,
            "versioned_notes": notes_path,
        },
        "versioned_notes": ["Output files generated"],
    }


def build_audit_graph():
    graph = StateGraph(AuditState)

    graph.add_node("plan_tasks", node_plan_tasks)
    graph.add_node("extract_documents", node_extract_documents)
    graph.add_node("normalize_tables", node_normalize_tables)
    graph.add_node("detect_anomalies", node_detect_anomalies)
    graph.add_node("test_controls", node_test_controls)
    graph.add_node("fieldwork_checks", node_fieldwork)
    graph.add_node("audit_reasoning", node_audit_reasoning)
    graph.add_node("consolidation", node_consolidation)
    graph.add_node("generate_outputs", node_generate_outputs)

    graph.set_entry_point("plan_tasks")
    graph.add_edge("plan_tasks", "extract_documents")
    graph.add_edge("extract_documents", "normalize_tables")
    graph.add_edge("normalize_tables", "detect_anomalies")
    graph.add_edge("detect_anomalies", "test_controls")
    graph.add_edge("test_controls", "fieldwork_checks")
    graph.add_edge("fieldwork_checks", "audit_reasoning")
    graph.add_edge("audit_reasoning", "consolidation")
    graph.add_edge("consolidation", "generate_outputs")
    graph.add_edge("generate_outputs", END)

    return graph.compile()


AUDIT_GRAPH = build_audit_graph()


async def run_audit_pipeline(session_id: str, stage: str, file_records: list) -> dict:
    initial_state: AuditState = {
        "session_id": session_id,
        "stage": stage,
        "file_records": file_records,
        "audit_tasks": [],
        "execution_plan": {},
        "extracted_docs": [],
        "normalized_tables": [],
        "anomaly_flags": [],
        "audit_findings": [],
        "risk_entries": [],
        "consolidated_findings": [],
        "control_test_results": [],
        "risk_control_matrix": [],
        "control_candidates": [],
        "fieldwork_findings": [],
        "interim_findings": [],
        "knowledge_entries": [],
        "versioned_notes": [],
        "errors": [],
        "output_paths": {},
    }
    final_state = await AUDIT_GRAPH.ainvoke(initial_state)
    return final_state
