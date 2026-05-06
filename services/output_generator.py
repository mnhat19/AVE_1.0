from __future__ import annotations

import json
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from docx import Document

from config.llm import get_llm_client
from config.settings import settings

OUTPUT_DIR = Path(settings.output_dir)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SEVERITY_COLORS = {
    "CRITICAL": "FF0000",
    "HIGH": "FF6600",
    "MEDIUM": "FFCC00",
    "LOW": "99CC00",
}

MEMO_GENERATION_PROMPT = """You are a senior auditor writing an audit memo in Vietnamese.

Session: {session_id}
Stage: {stage}
Findings: {findings_json}
Anomaly Summary: {anomaly_summary}

Structure:
1. Audit objective
2. Summary of procedures performed
3. Key findings (prioritized)
4. Root cause and expected impact
5. Recommended next steps

Write in formal Vietnamese audit language. Be specific and reference the finding IDs (FND-xxx)."""


async def generate_issue_log(state: dict) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Issue Log"

    headers = [
        "Finding ID",
        "Stage",
        "Description",
        "Root Cause",
        "Expected Impact",
        "Severity",
        "Assignee",
        "Status",
        "Confidence Score",
        "Source",
    ]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E79")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    ws.row_dimensions[1].height = 30

    session_id = state["session_id"]
    for idx, finding in enumerate(state["audit_findings"], 1):
        row_num = idx + 1
        finding_id = f"FND-{session_id[:4].upper()}-{idx:03d}"
        severity = finding.get("severity", "MEDIUM")

        row_data = [
            finding_id,
            state["stage"],
            finding.get("description", ""),
            finding.get("root_cause", ""),
            finding.get("expected_impact", ""),
            severity,
            "Audit Team",
            "OPEN",
            f"{finding.get('confidence_score', 0.0):.0%}",
            finding.get("source_reference")
            or ", ".join(finding.get("related_anomaly_rules", [])),
        ]
        for col, val in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col, value=val)

        sev_cell = ws.cell(row=row_num, column=6)
        sev_cell.fill = PatternFill("solid", fgColor=SEVERITY_COLORS.get(severity, "CCCCCC"))
        sev_cell.font = Font(bold=True)

    col_widths = [15, 10, 60, 50, 50, 12, 15, 12, 15, 30]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

    ws2 = wb.create_sheet("Risk Register")
    risk_headers = [
        "Risk ID",
        "Description",
        "Probability",
        "Impact",
        "Risk Score",
        "Owner",
        "Controls",
    ]
    for col, header in enumerate(risk_headers, 1):
        ws2.cell(row=1, column=col, value=header).font = Font(bold=True)

    for idx, risk in enumerate(state["risk_entries"], 2):
        ws2.cell(row=idx, column=1, value=risk.get("id", f"RISK-{idx}"))
        ws2.cell(row=idx, column=2, value=risk.get("description", ""))
        ws2.cell(row=idx, column=3, value=risk.get("probability", 0))
        ws2.cell(row=idx, column=4, value=risk.get("impact", 0))
        ws2.cell(row=idx, column=5, value=risk.get("risk_score", 0))
        ws2.cell(row=idx, column=6, value=risk.get("owner", ""))
        ws2.cell(row=idx, column=7, value=str(risk.get("related_controls", [])))

    path = OUTPUT_DIR / f"issue_log_{session_id}.xlsx"
    wb.save(path)
    return str(path)


async def generate_risk_register(state: dict) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Risk Register"

    headers = [
        "Risk ID",
        "Description",
        "Probability",
        "Impact",
        "Risk Score",
        "Owner",
        "Controls",
    ]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)

    for idx, risk in enumerate(state.get("risk_entries", []), 2):
        ws.cell(row=idx, column=1, value=risk.get("id", f"RISK-{idx}"))
        ws.cell(row=idx, column=2, value=risk.get("description", ""))
        ws.cell(row=idx, column=3, value=risk.get("probability", 0))
        ws.cell(row=idx, column=4, value=risk.get("impact", 0))
        ws.cell(row=idx, column=5, value=risk.get("risk_score", 0))
        ws.cell(row=idx, column=6, value=risk.get("owner", ""))
        ws.cell(row=idx, column=7, value=str(risk.get("related_controls", [])))

    session_id = state["session_id"]
    path = OUTPUT_DIR / f"risk_register_{session_id}.xlsx"
    wb.save(path)
    return str(path)


async def generate_memo(state: dict) -> str:
    llm = get_llm_client("generation")
    anomaly_rules = {flag.get("rule") for flag in state["anomaly_flags"] if flag.get("rule")}
    anomaly_summary = f"{len(state['anomaly_flags'])} anomalies flagged: {', '.join(sorted(anomaly_rules))}"

    prompt = MEMO_GENERATION_PROMPT.format(
        session_id=state["session_id"],
        stage=state["stage"],
        findings_json=json.dumps(state["audit_findings"][:10], ensure_ascii=False),
        anomaly_summary=anomaly_summary,
    )
    memo_text = await llm(prompt)

    doc = Document()
    doc.add_heading(f"AUDIT MEMO - {state['stage']}", 0)
    doc.add_paragraph(f"Session ID: {state['session_id']}")
    doc.add_paragraph("")

    for line in memo_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(("1.", "2.", "3.", "4.", "5.")):
            doc.add_heading(line, level=1)
        else:
            doc.add_paragraph(line)

    path = OUTPUT_DIR / f"audit_memo_{state['session_id']}.docx"
    doc.save(path)
    return str(path)
