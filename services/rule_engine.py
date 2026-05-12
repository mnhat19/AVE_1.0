from __future__ import annotations

from typing import Callable

import pandas as pd


ControlRule = dict
def _has_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    return all(column in df.columns for column in columns)


def _empty_like(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[0:0]



def _detect_gaps(series: pd.Series) -> list[int]:
    numeric = pd.to_numeric(series, errors="coerce").dropna().astype(int)
    if numeric.empty:
        return []
    sorted_vals = sorted(numeric.unique())
    gaps: list[int] = []
    for idx in range(1, len(sorted_vals)):
        expected = sorted_vals[idx - 1] + 1
        actual = sorted_vals[idx]
        if actual > expected:
            gaps.extend(range(expected, actual))
    return gaps


CONTROL_RULES: list[ControlRule] = [
    {
        "id": "TOC-001",
        "name": "Segregation of Duties",
        "description": "Creator and approver must be different.",
        "severity": "HIGH",
        "check": lambda df: (
            _empty_like(df)
            if not _has_columns(df, ["creator", "approver"])
            else df[df["creator"] == df["approver"]]
        ),
    },
    {
        "id": "TOC-002",
        "name": "Authorization Limit",
        "description": "Transactions above limit require sufficient approval level.",
        "severity": "CRITICAL",
        "check": lambda df: (
            _empty_like(df)
            if not _has_columns(df, ["amount", "approval_level"])
            else df[(df["amount"] > 1_000_000) & (df["approval_level"] < 2)]
        ),
    },
    {
        "id": "TOC-003",
        "name": "Sequential Numbering",
        "description": "Voucher numbers must be sequential without gaps.",
        "severity": "MEDIUM",
        "check": lambda df: (
            []
            if not _has_columns(df, ["voucher_number"])
            else _detect_gaps(df["voucher_number"])
        ),
    },
]


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df.copy()


def run_controls(df: pd.DataFrame) -> list[dict]:
    """Evaluate control rules on transaction data."""
    results: list[dict] = []
    safe_df = _normalize_df(df)

    for rule in CONTROL_RULES:
        rule_id = rule["id"]
        check: Callable = rule["check"]
        if safe_df.empty:
            results.append(
                {
                    "rule_id": rule_id,
                    "name": rule["name"],
                    "description": rule["description"],
                    "severity": rule["severity"],
                    "result": "NOT_TESTED",
                    "failing_rows": [],
                }
            )
            continue

        failing = check(safe_df)
        failing_rows: list[int] = []
        if isinstance(failing, pd.DataFrame):
            failing_rows = failing.index.tolist()[:10]
            result = "DEFICIENT" if not failing.empty else "EFFECTIVE"
        elif isinstance(failing, list):
            failing_rows = failing[:10]
            result = "DEFICIENT" if failing else "EFFECTIVE"
        else:
            result = "NOT_TESTED"

        results.append(
            {
                "rule_id": rule_id,
                "name": rule["name"],
                "description": rule["description"],
                "severity": rule["severity"],
                "result": result,
                "failing_rows": failing_rows,
            }
        )

    return results
