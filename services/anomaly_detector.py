from __future__ import annotations

from typing import Dict, List

import pandas as pd


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def detect_journal_anomalies(df: pd.DataFrame) -> List[Dict]:
    flags: List[Dict] = []
    if df.empty:
        return flags

    if "amount" in df.columns:
        amounts = _coerce_numeric(df["amount"])
        round_amounts = df[amounts.notna() & (amounts % 1_000_000 == 0)]
        if not round_amounts.empty:
            flags.append(
                {
                    "rule": "ROUND_AMOUNT",
                    "severity": "LOW",
                    "count": len(round_amounts),
                    "description": (
                        f"{len(round_amounts)} journal entries with round amounts (multiples of 1M)"
                    ),
                    "rows": round_amounts.index.tolist()[:10],
                }
            )

        zero_amounts = df[amounts.fillna(0) == 0]
        if not zero_amounts.empty:
            flags.append(
                {
                    "rule": "ZERO_AMOUNT",
                    "severity": "LOW",
                    "count": len(zero_amounts),
                    "description": f"{len(zero_amounts)} journal entries with zero amount",
                    "rows": zero_amounts.index.tolist()[:10],
                }
            )

    if "date" in df.columns:
        dates = pd.to_datetime(df["date"], errors="coerce")
        weekend = df[dates.dt.dayofweek >= 5]
        if not weekend.empty:
            flags.append(
                {
                    "rule": "WEEKEND_ENTRY",
                    "severity": "MEDIUM",
                    "count": len(weekend),
                    "description": f"{len(weekend)} journal entries posted on weekends",
                    "rows": weekend.index.tolist()[:10],
                }
            )

    if "amount" in df.columns and len(df) > 10:
        amounts = _coerce_numeric(df["amount"]).dropna()
        if not amounts.empty:
            mean = amounts.mean()
            std = amounts.std()
            if std and std > 0:
                outliers = df[abs(_coerce_numeric(df["amount"]) - mean) > 3 * std]
                if not outliers.empty:
                    flags.append(
                        {
                            "rule": "LARGE_AMOUNT_OUTLIER",
                            "severity": "HIGH",
                            "count": len(outliers),
                            "description": (
                                f"{len(outliers)} entries with amounts >3σ from mean ({mean:,.0f})"
                            ),
                            "rows": outliers.index.tolist()[:10],
                        }
                    )

    if {"debit", "credit"}.issubset(df.columns):
        debit = _coerce_numeric(df["debit"]).fillna(0)
        credit = _coerce_numeric(df["credit"]).fillna(0)
        if "reference" in df.columns:
            df_ref = df.assign(debit=debit, credit=credit).groupby("reference")[["debit", "credit"]].sum()
            unbalanced = df_ref[abs(df_ref["debit"] - df_ref["credit"]) > 1]
            if not unbalanced.empty:
                flags.append(
                    {
                        "rule": "UNBALANCED_JOURNAL",
                        "severity": "CRITICAL",
                        "count": len(unbalanced),
                        "description": (
                            f"{len(unbalanced)} journal references where debit ≠ credit"
                        ),
                        "rows": unbalanced.index.tolist()[:10],
                    }
                )

    if "voucher_number" in df.columns:
        duplicates = df[df["voucher_number"].duplicated()]
        if not duplicates.empty:
            flags.append(
                {
                    "rule": "DUPLICATE_VOUCHER",
                    "severity": "MEDIUM",
                    "count": len(duplicates),
                    "description": f"{len(duplicates)} duplicated voucher numbers",
                    "rows": duplicates.index.tolist()[:10],
                }
            )

    return flags


def detect_trial_balance_anomalies(df: pd.DataFrame) -> List[Dict]:
    flags: List[Dict] = []
    if df.empty:
        return flags

    if {"debit", "credit"}.issubset(df.columns):
        total_debit = _coerce_numeric(df["debit"]).fillna(0).sum()
        total_credit = _coerce_numeric(df["credit"]).fillna(0).sum()
        diff = abs(total_debit - total_credit)
        if diff > 1:
            flags.append(
                {
                    "rule": "TB_OUT_OF_BALANCE",
                    "severity": "CRITICAL",
                    "count": 1,
                    "description": f"Trial balance out of balance by {diff:,.2f}",
                    "rows": [],
                }
            )

    if "balance" in df.columns:
        account_code = df.get("account_code")
        balance = _coerce_numeric(df["balance"]).fillna(0)
        if account_code is not None:
            is_asset = account_code.astype(str).str.startswith("1")
            neg_asset = df[is_asset & (balance < 0)]
            if not neg_asset.empty:
                flags.append(
                    {
                        "rule": "NEGATIVE_ASSET_BALANCE",
                        "severity": "HIGH",
                        "count": len(neg_asset),
                        "description": (
                            f"{len(neg_asset)} asset accounts with negative balances"
                        ),
                        "rows": neg_asset.index.tolist()[:10],
                    }
                )

    return flags
