import pandas as pd

from agents.audit_agent import run_ageing_analysis, run_reconciliation_checks
from services.evidence_linker import format_reference


def test_format_reference():
    ref = format_reference({"sheet": "Sheet1", "row": 3, "page": 2})
    assert "Sheet1" in ref
    assert "Row 3" in ref
    assert "Page 2" in ref


def test_reconciliation_check():
    trial = {
        "schema": {"schema_type": "TRIAL_BALANCE"},
        "data": [{"balance": 1000}, {"balance": 2000}],
        "columns": ["balance"],
        "file_id": "F1",
        "sheet_name": "Trial",
        "source_page": None,
    }
    recon = {
        "schema": {"schema_type": "RECONCILIATION"},
        "data": [{"difference": 500}],
        "columns": ["difference"],
        "file_id": "F2",
        "sheet_name": "Recon",
        "source_page": None,
    }

    findings = run_reconciliation_checks([trial, recon])
    assert findings
    assert findings[0]["rule_id"] == "FW-RECON-001"


def test_ageing_analysis():
    table = {
        "schema": {"schema_type": "AGEING"},
        "data": [
            {"bucket_90_plus": 300, "total": 1000},
            {"bucket_90_plus": 200, "total": 1000},
        ],
        "columns": ["bucket_90_plus", "total"],
        "file_id": "F3",
        "sheet_name": "Ageing",
        "source_page": None,
    }

    findings = run_ageing_analysis([table])
    assert findings
    assert findings[0]["rule_id"] == "FW-AGE-001"
