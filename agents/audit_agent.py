from __future__ import annotations

import json
from typing import Dict, List

import pandas as pd

from config.llm import get_llm_client
from services.anomaly_detector import detect_journal_anomalies, detect_trial_balance_anomalies
from services.evidence_linker import create_evidence_link
from services.reconciliation import reconcile_trial_balance
from services.rule_engine import run_controls


AUDIT_REASONING_PROMPT = """You are a senior auditor performing {stage} audit procedures.

CONTEXT:
- Audit Stage: {stage}
- Documents analyzed: {doc_summaries}
- Anomalies detected by automated rules: {anomaly_flags}
- Internal controls identified: {controls_identified}
- Control test results: {control_test_results}
- Knowledge base hints: {knowledge_entries}

Based on the above, identify audit findings. For each finding provide:
1. Clear description of the issue
2. Root cause analysis
3. Potential impact on financial statements
4. Severity (LOW/MEDIUM/HIGH/CRITICAL)
5. Confidence score (0.0-1.0) based on evidence strength

Return JSON array:
[
  {{
    "description": "<specific finding description>",
    "root_cause": "<identified root cause>",
    "expected_impact": "<impact on financial statements>",
    "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "confidence_score": <0.0-1.0>,
    "related_anomaly_rules": ["list of anomaly rules that triggered this finding"],
    "recommended_action": "<next audit step recommended>"
  }}
]

Return ONLY valid JSON array. Be specific and actionable, not generic."""

RISK_SCORE_MAP = {"LOW": 2, "MEDIUM": 5, "HIGH": 8, "CRITICAL": 10}
MATERIALITY_MAP = {
    "LOW": "IMMATERIAL",
    "MEDIUM": "MATERIAL",
    "HIGH": "HIGHLY_MATERIAL",
    "CRITICAL": "HIGHLY_MATERIAL",
}


def _normalize_findings(findings: list) -> list[dict]:
    return [finding for finding in findings if isinstance(finding, dict)]


def run_test_of_controls(normalized_tables: list[dict]) -> list[dict]:
    """Run test of controls on available transaction tables."""
    results: list[dict] = []
    for table in normalized_tables:
        if not isinstance(table, dict):
            continue
        schema_type = table.get("schema", {}).get("schema_type")
        if schema_type not in {"JOURNAL", "TRANSACTION_LOG"}:
            continue
        df = pd.DataFrame(table.get("data", []), columns=table.get("columns", []))
        rule_results = run_controls(df)
        for rule in rule_results:
            rule["source_file_id"] = table.get("file_id")
            rule["source_sheet"] = table.get("sheet_name")
        results.extend(rule_results)
    return results


def build_risk_control_matrix(controls_identified: list, test_results: list[dict]) -> list[dict]:
    """Link identified controls with their test outcomes for interim audit."""
    matrix: list[dict] = []
    known_controls = [str(control) for control in controls_identified]
    for result in test_results:
        control_desc = result.get("description") or result.get("name")
        related = next((c for c in known_controls if c.lower() in str(control_desc).lower()), None)
        matrix.append(
            {
                "control_id": result.get("rule_id"),
                "control_description": control_desc,
                "related_control": related,
                "test_result": result.get("result"),
                "severity": result.get("severity"),
                "source_file_id": result.get("source_file_id"),
                "source_sheet": result.get("source_sheet"),
            }
        )
    return matrix


async def generate_audit_findings(
    stage: str,
    doc_summaries: list,
    anomaly_flags: list,
    controls_identified: list,
    control_test_results: list,
    knowledge_entries: list,
) -> list:
    llm = get_llm_client("reasoning")
    prompt = AUDIT_REASONING_PROMPT.format(
        stage=stage,
        doc_summaries=json.dumps(doc_summaries[:5], ensure_ascii=False),
        anomaly_flags=json.dumps(anomaly_flags, ensure_ascii=False),
        controls_identified=json.dumps(controls_identified[:10], ensure_ascii=False),
        control_test_results=json.dumps(control_test_results[:10], ensure_ascii=False),
        knowledge_entries=json.dumps(knowledge_entries[:10], ensure_ascii=False),
    )
    raw = await llm(prompt)
    try:
        findings = json.loads(raw.strip())
        if not isinstance(findings, list):
            return []
        return _normalize_findings(findings)
    except Exception:
        return []


def build_risk_register(findings: list, session_id: str) -> list:
    risks = []
    interim_idx = 0
    fieldwork_idx = 0
    for idx, finding in enumerate(_normalize_findings(findings)):
        stage = finding.get("stage", "INTERIM")
        if stage == "FIELDWORK":
            fieldwork_idx += 1
            stage_index = fieldwork_idx
        else:
            interim_idx += 1
            stage_index = interim_idx
        severity = finding.get("severity", "MEDIUM")
        score = RISK_SCORE_MAP.get(severity, 5)
        risks.append(
            {
                "id": f"RISK-{session_id[:4]}-{idx + 1:03d}",
                "session_id": session_id,
                "finding_index": idx + 1,
                "finding_stage": stage,
                "finding_stage_index": stage_index,
                "finding_id": f"FND-{session_id[:4].upper()}-{idx + 1:03d}",
                "description": finding.get("description", ""),
                "probability": 0.7 if severity in ["HIGH", "CRITICAL"] else 0.4,
                "impact": score / 10,
                "risk_score": score,
                "owner": "Audit Team",
                "related_controls": finding.get("related_anomaly_rules", []),
            }
        )
    return risks


def attach_evidence_links(findings: list, anomaly_flags: list) -> list:
    safe_findings = _normalize_findings(findings)
    for finding in safe_findings:
        related_rules = finding.get("related_anomaly_rules") or []
        evidence_links: list[dict] = []
        for rule in related_rules:
            match = next((flag for flag in anomaly_flags if flag.get("rule") == rule), None)
            if not match:
                continue
            location = {
                "sheet": match.get("source_sheet"),
                "page": match.get("source_page"),
                "rows": match.get("rows") or None,
            }
            evidence_links.append(
                create_evidence_link(
                    None,
                    match.get("source_file_id"),
                    location,
                )
            )

        finding["evidence_links"] = evidence_links
        if evidence_links:
            finding["source_reference"] = "; ".join(
                link["reference"] for link in evidence_links if link.get("reference")
            )
    return safe_findings


def _fieldwork_severity_from_amount(amount: float) -> str:
    if amount >= 5_000_000:
        return "CRITICAL"
    if amount >= 1_000_000:
        return "HIGH"
    if amount >= 100_000:
        return "MEDIUM"
    return "LOW"


def run_reconciliation_checks(normalized_tables: list[dict]) -> list[dict]:
    """Generate reconciliation findings from trial balance and reconciliation tables."""
    trial_tables = [
        table for table in normalized_tables
        if table.get("schema", {}).get("schema_type") == "TRIAL_BALANCE"
    ]
    recon_tables = [
        table for table in normalized_tables
        if table.get("schema", {}).get("schema_type") == "RECONCILIATION"
    ]

    findings: list[dict] = []
    if not trial_tables or not recon_tables:
        return findings

    trial = trial_tables[0]
    recon = recon_tables[0]
    trial_df = pd.DataFrame(trial.get("data", []), columns=trial.get("columns", []))
    recon_df = pd.DataFrame(recon.get("data", []), columns=recon.get("columns", []))

    summary = reconcile_trial_balance(trial_df, recon_df)
    difference = float(summary.get("difference", 0.0) or 0.0)
    if difference <= 1:
        return findings

    severity = _fieldwork_severity_from_amount(difference)
    finding = {
        "stage": "FIELDWORK",
        "rule_id": "FW-RECON-001",
        "description": f"Reconciliation difference detected: {difference:,.2f}",
        "root_cause": "Unreconciled roll-forward differences",
        "expected_impact": "Potential misstatement in closing balances",
        "severity": severity,
        "confidence_score": 0.7,
        "source_file_id": recon.get("file_id"),
        "location_ref": "summary",
        "evidence_links": [
            create_evidence_link(
                None,
                recon.get("file_id"),
                {"sheet": recon.get("sheet_name"), "row": 1, "page": recon.get("source_page")},
            )
        ],
    }
    findings.append(finding)
    return findings


def run_ageing_analysis(normalized_tables: list[dict]) -> list[dict]:
    """Analyze ageing tables and raise findings for overdue concentrations."""
    findings: list[dict] = []
    for table in normalized_tables:
        if table.get("schema", {}).get("schema_type") != "AGEING":
            continue
        df = pd.DataFrame(table.get("data", []), columns=table.get("columns", []))
        if df.empty or "bucket_90_plus" not in df.columns or "total" not in df.columns:
            continue
        bucket = pd.to_numeric(df["bucket_90_plus"], errors="coerce").fillna(0).sum()
        total = pd.to_numeric(df["total"], errors="coerce").fillna(0).sum()
        if total <= 0:
            continue
        ratio = bucket / total
        if ratio >= 0.2:
            severity = _fieldwork_severity_from_amount(bucket)
            findings.append(
                {
                    "stage": "FIELDWORK",
                    "rule_id": "FW-AGE-001",
                    "description": f"Overdue 90+ bucket exceeds 20% of total ({ratio:.0%})",
                    "root_cause": "Slow collections or credit control issues",
                    "expected_impact": "Potential impairment on receivables",
                    "severity": severity,
                    "confidence_score": 0.6,
                    "source_file_id": table.get("file_id"),
                    "location_ref": "summary",
                    "evidence_links": [
                        create_evidence_link(
                            None,
                            table.get("file_id"),
                            {"sheet": table.get("sheet_name"), "row": 1, "page": table.get("source_page")},
                        )
                    ],
                }
            )
    return findings


def cross_validate_evidence(extracted_docs: list[dict], findings: list[dict]) -> list[dict]:
    """Flag findings that lack corroborating evidence in extracted documents."""
    doc_texts: dict[str, str] = {}
    for doc in extracted_docs:
        if not isinstance(doc, dict):
            continue
        file_id = doc.get("file_id")
        raw = doc.get("raw") or {}
        if isinstance(raw, dict) and raw.get("type") == "text":
            doc_texts[file_id] = raw.get("content", "") or ""

    for finding in findings:
        source_id = finding.get("source_file_id")
        if not source_id:
            finding["manual_review_required"] = True
            continue
        content = doc_texts.get(source_id, "")
        reference = finding.get("source_reference") or finding.get("description", "")
        if content and any(token.isdigit() for token in reference.split()):
            digits = [token for token in reference.split() if token.isdigit()]
            if not any(digit in content for digit in digits):
                finding["manual_review_required"] = True
        elif not content:
            finding["manual_review_required"] = True
    return findings


def build_consolidated_findings(stage: str, findings: list) -> list:
    if stage != "BOTH":
        return []

    consolidated: list[dict] = []
    for idx, finding in enumerate(_normalize_findings(findings), 1):
        severity = finding.get("severity", "MEDIUM")
        materiality = MATERIALITY_MAP.get(severity, "MATERIAL")
        confidence = float(finding.get("confidence_score", 0.0) or 0.0)
        review_flag = confidence < 0.5 or not finding.get("evidence_links")
        consolidated.append(
            {
                "source_finding_index": idx,
                "materiality": materiality,
                "review_flag": review_flag,
                "confidence_score": confidence,
            }
        )
    return consolidated
