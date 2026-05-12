import pandas as pd

from agents.audit_agent import build_risk_control_matrix, run_test_of_controls


def test_test_of_controls_runner_segregation():
    df = pd.DataFrame(
        [
            {"creator": "A", "approver": "A", "amount": 500000, "voucher_number": 1},
            {"creator": "B", "approver": "C", "amount": 2000000, "approval_level": 1, "voucher_number": 2},
        ]
    )
    tables = [
        {
            "schema": {"schema_type": "JOURNAL"},
            "data": df.to_dict(orient="records"),
            "columns": list(df.columns),
            "file_id": "F1",
            "sheet_name": "Sheet1",
        }
    ]

    results = run_test_of_controls(tables)
    rule_ids = {result["rule_id"] for result in results}

    assert "TOC-001" in rule_ids
    assert "TOC-002" in rule_ids


def test_risk_control_matrix_builder():
    controls = ["Manager approval"]
    test_results = [
        {
            "rule_id": "TOC-001",
            "description": "Creator and approver must be different.",
            "result": "DEFICIENT",
            "severity": "HIGH",
            "source_file_id": "F1",
            "source_sheet": "Sheet1",
        }
    ]

    matrix = build_risk_control_matrix(controls, test_results)

    assert matrix
    assert matrix[0]["control_id"] == "TOC-001"
    assert matrix[0]["test_result"] == "DEFICIENT"
