from __future__ import annotations

import operator
from types import SimpleNamespace
from typing import Annotated, List, TypedDict

from langgraph.graph import END, StateGraph

from agents.audit_agent import (
    attach_evidence_links,
    build_risk_register,
    build_consolidated_findings,
    detect_journal_anomalies,
    detect_trial_balance_anomalies,
    generate_audit_findings,
)
from services.normalizer import detect_table_schema, normalize_table
from agents.doc_agent import classify_document, extract_process_info
from services.extractor import extract
from services.output_generator import generate_issue_log, generate_memo, generate_risk_register


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
    versioned_notes: Annotated[List[str], operator.add]
    errors: List[str]
    output_paths: dict


def _has_formats(file_records: list[dict], formats: set[str]) -> bool:
    return any(record.get("format") in formats for record in file_records)


def _build_tasks(session_id: str, stage: str, file_records: list[dict]) -> list[dict]:
    tasks: list[dict] = []
    has_tables = _has_formats(file_records, {"XLSX", "CSV", "TXT"})

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

    reasoning_deps = [anomaly_id or extract_id]
    reasoning_id = add_task("AUDIT_REASONING", "AUDIT_AGENT", 4, reasoning_deps)
    add_task("GENERATE_OUTPUTS", "AUDIT_AGENT", 5, [reasoning_id])

    return tasks


def _mark_task_status(tasks: list[dict], task_type: str, status: str) -> None:
    for task in tasks:
        if task.get("task_type") == task_type:
            task["status"] = status


async def node_plan_tasks(state: AuditState) -> AuditState:
    tasks = _build_tasks(state["session_id"], state["stage"], state["file_records"])
    ordered = [task["id"] for task in sorted(tasks, key=lambda t: t["priority"])]
    execution_plan = {
        "scope": {"session_id": state["session_id"], "stage": state["stage"]},
        "tasks": tasks,
        "ordered_task_ids": ordered,
    }
    return {
        **state,
        "audit_tasks": tasks,
        "execution_plan": execution_plan,
        "versioned_notes": [f"Planned {len(tasks)} tasks"],
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
            extracted.append(
                {
                    "file_id": record.get("id"),
                    "filename": record.get("filename"),
                    "format": record.get("format"),
                    "raw": raw,
                    "classification": classification,
                    "process_info": process_info,
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
        raw = doc.get("raw", {})
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


async def node_audit_reasoning(state: AuditState) -> AuditState:
    doc_summaries = []
    for doc in state["extracted_docs"]:
        classification = doc.get("classification")
        if not isinstance(classification, dict):
            continue
        doc_summaries.append(
            {
                "filename": doc.get("filename"),
                "summary": classification.get("summary", ""),
            }
        )
    controls = []
    for doc in state["extracted_docs"]:
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

    findings_raw = await generate_audit_findings(
        stage=state["stage"],
        doc_summaries=doc_summaries,
        anomaly_flags=state["anomaly_flags"],
        controls_identified=controls,
    )
    findings_with_evidence = attach_evidence_links(findings_raw, state["anomaly_flags"])
    consolidated = build_consolidated_findings(state["stage"], findings_with_evidence)
    risk_entries = build_risk_register(findings_with_evidence, state["session_id"])
    _mark_task_status(state.get("audit_tasks", []), "AUDIT_REASONING", "COMPLETED")
    return {
        **state,
        "audit_tasks": state.get("audit_tasks", []),
        "audit_findings": findings_with_evidence,
        "risk_entries": risk_entries,
        "consolidated_findings": consolidated,
        "versioned_notes": [
            f"Identified {len(controls)} controls from process docs",
            f"Generated {len(findings_raw)} audit findings",
        ],
    }


async def node_generate_outputs(state: AuditState) -> AuditState:
    issue_log_path = await generate_issue_log(state)
    memo_path = await generate_memo(state)
    risk_register_path = await generate_risk_register(state)
    _mark_task_status(state.get("audit_tasks", []), "GENERATE_OUTPUTS", "COMPLETED")
    return {
        **state,
        "audit_tasks": state.get("audit_tasks", []),
        "output_paths": {
            "issue_log": issue_log_path,
            "memo": memo_path,
            "risk_register": risk_register_path,
        },
        "versioned_notes": ["Output files generated"],
    }


def build_audit_graph():
    graph = StateGraph(AuditState)

    graph.add_node("plan_tasks", node_plan_tasks)
    graph.add_node("extract_documents", node_extract_documents)
    graph.add_node("normalize_tables", node_normalize_tables)
    graph.add_node("detect_anomalies", node_detect_anomalies)
    graph.add_node("audit_reasoning", node_audit_reasoning)
    graph.add_node("generate_outputs", node_generate_outputs)

    graph.set_entry_point("plan_tasks")
    graph.add_edge("plan_tasks", "extract_documents")
    graph.add_edge("extract_documents", "normalize_tables")
    graph.add_edge("normalize_tables", "detect_anomalies")
    graph.add_edge("detect_anomalies", "audit_reasoning")
    graph.add_edge("audit_reasoning", "generate_outputs")
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
        "versioned_notes": [],
        "errors": [],
        "output_paths": {},
    }
    final_state = await AUDIT_GRAPH.ainvoke(initial_state)
    return final_state
