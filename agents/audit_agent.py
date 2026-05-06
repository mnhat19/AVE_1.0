from __future__ import annotations

import json
from typing import Dict, List

import pandas as pd

from config.llm import get_llm_client


AUDIT_REASONING_PROMPT = """You are a senior auditor performing {stage} audit procedures.

CONTEXT:
- Audit Stage: {stage}
- Documents analyzed: {doc_summaries}
- Anomalies detected by automated rules: {anomaly_flags}
- Internal controls identified: {controls_identified}

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


async def generate_audit_findings(
    stage: str,
    doc_summaries: list,
    anomaly_flags: list,
    controls_identified: list,
) -> list:
    llm = get_llm_client("reasoning")
    prompt = AUDIT_REASONING_PROMPT.format(
        stage=stage,
        doc_summaries=json.dumps(doc_summaries[:5], ensure_ascii=False),
        anomaly_flags=json.dumps(anomaly_flags, ensure_ascii=False),
        controls_identified=json.dumps(controls_identified[:10], ensure_ascii=False),
    )
    raw = await llm(prompt)
    try:
        findings = json.loads(raw.strip())
        return findings if isinstance(findings, list) else []
    except Exception:
        return []


def build_risk_register(findings: list, session_id: str) -> list:
    risks = []
    for idx, finding in enumerate(findings):
        severity = finding.get("severity", "MEDIUM")
        score = RISK_SCORE_MAP.get(severity, 5)
        risks.append(
            {
                "id": f"RISK-{session_id[:4]}-{idx + 1:03d}",
                "session_id": session_id,
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
    for finding in findings:
        related_rules = finding.get("related_anomaly_rules") or []
        evidence_links: list[dict] = []
        for rule in related_rules:
            match = next((flag for flag in anomaly_flags if flag.get("rule") == rule), None)
            if not match:
                continue
            ref_parts = []
            if match.get("source_page") is not None:
                ref_parts.append(f"page:{match['source_page']}")
            if match.get("source_sheet"):
                ref_parts.append(f"sheet:{match['source_sheet']}")
            if match.get("rows"):
                rows = ",".join(str(r) for r in match["rows"])
                ref_parts.append(f"rows:{rows}")
            reference = " ".join(ref_parts) if ref_parts else f"rule:{rule}"
            evidence_links.append(
                {
                    "source_file_id": match.get("source_file_id"),
                    "reference": reference,
                }
            )

        finding["evidence_links"] = evidence_links
        if evidence_links:
            finding["source_reference"] = "; ".join(
                link["reference"] for link in evidence_links if link.get("reference")
            )
    return findings


def build_consolidated_findings(stage: str, findings: list) -> list:
    if stage != "BOTH":
        return []

    consolidated: list[dict] = []
    for idx, finding in enumerate(findings, 1):
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
