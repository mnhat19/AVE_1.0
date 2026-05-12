from __future__ import annotations

import pandas as pd


def _coerce(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def reconcile_trial_balance(trial_balance: pd.DataFrame, reconciliation: pd.DataFrame) -> dict:
    """Compare trial balance vs reconciliation table and return summary differences."""
    tb_total = 0.0
    if "balance" in trial_balance.columns:
        tb_total = _coerce(trial_balance["balance"]).fillna(0).sum()

    rec_diff_total = 0.0
    if "difference" in reconciliation.columns:
        rec_diff_total = _coerce(reconciliation["difference"]).fillna(0).sum()

    return {
        "trial_balance_total": tb_total,
        "reconciliation_diff_total": rec_diff_total,
        "difference": abs(tb_total - rec_diff_total),
    }
