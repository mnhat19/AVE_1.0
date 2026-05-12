import json
from difflib import SequenceMatcher

import pandas as pd

from config.llm import get_llm_client

SCHEMA_DETECT_PROMPT = """You are an accounting data analyst. Examine these column headers and sample rows.

Columns: {columns}
Sample rows (first 3): {sample}

Identify the schema type and column mapping. Return JSON:
{{
  "schema_type": "<TRIAL_BALANCE | JOURNAL | LEAD_SCHEDULE | AGEING | RECONCILIATION | TRANSACTION_LOG | OTHER>",
  "column_mapping": {{
    "account_code": "<column name or null>",
    "account_name": "<column name or null>",
    "debit": "<column name or null>",
    "credit": "<column name or null>",
    "balance": "<column name or null>",
    "date": "<column name or null>",
    "description": "<column name or null>",
    "amount": "<column name or null>",
    "reference": "<column name or null>"
  }},
  "currency_detected": "<VND | USD | EUR | unknown>",
  "period_detected": "<detected accounting period or null>"
}}"""

SCHEMA_TYPES = {
    "TRIAL_BALANCE",
    "JOURNAL",
    "LEAD_SCHEDULE",
    "AGEING",
    "RECONCILIATION",
    "TRANSACTION_LOG",
    "OTHER",
}

SCHEMA_COLUMNS: dict[str, list[str]] = {
    "TRIAL_BALANCE": ["account_code", "account_name", "debit", "credit", "balance"],
    "JOURNAL": ["date", "journal_id", "debit_account", "credit_account", "amount", "description"],
    "LEAD_SCHEDULE": ["line_item", "prior_year", "current_year", "variance"],
    "AGEING": ["customer", "bucket_0_30", "bucket_31_60", "bucket_61_90", "bucket_90_plus", "total"],
    "RECONCILIATION": ["item", "book_balance", "bank_balance", "difference"],
}

COLUMN_SYNONYMS: dict[str, list[str]] = {
    "account_code": ["account", "acct", "code", "acct_code"],
    "account_name": ["name", "account_name"],
    "debit": ["debit", "dr"],
    "credit": ["credit", "cr"],
    "balance": ["balance", "ending_balance", "closing_balance"],
    "date": ["date", "posting_date", "transaction_date"],
    "journal_id": ["journal", "journal_id", "voucher", "entry"],
    "debit_account": ["debit_account", "dr_account", "debit_acct"],
    "credit_account": ["credit_account", "cr_account", "credit_acct"],
    "amount": ["amount", "value", "amt"],
    "description": ["description", "memo", "narration"],
    "line_item": ["line_item", "item", "account"],
    "prior_year": ["prior", "prev", "prior_year"],
    "current_year": ["current", "current_year"],
    "variance": ["variance", "delta"],
    "customer": ["customer", "client", "vendor"],
    "bucket_0_30": ["0-30", "0_30", "current"],
    "bucket_31_60": ["31-60", "31_60"],
    "bucket_61_90": ["61-90", "61_90"],
    "bucket_90_plus": ["90+", "over_90", "90_plus"],
    "total": ["total", "sum"],
    "item": ["item", "description"],
    "book_balance": ["book", "book_balance"],
    "bank_balance": ["bank", "bank_balance"],
    "difference": ["difference", "diff", "variance"],
}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _fuzzy_map_columns(columns: list[str], target_fields: list[str]) -> dict:
    mapping: dict[str, str] = {}
    normalized = {col: col.lower().replace(" ", "_") for col in columns}

    for field in target_fields:
        best_col = None
        best_score = 0.0
        candidates = COLUMN_SYNONYMS.get(field, [field])
        for col, norm in normalized.items():
            for candidate in candidates:
                score = _similarity(norm, candidate)
                if score > best_score:
                    best_score = score
                    best_col = col
        if best_col and best_score >= 0.65:
            mapping[field] = best_col
    return mapping


def _guess_schema_type(columns: list[str]) -> str:
    normalized = [col.lower().replace(" ", "_") for col in columns]
    scores: dict[str, int] = {}
    for schema_type, fields in SCHEMA_COLUMNS.items():
        score = 0
        for field in fields:
            synonyms = COLUMN_SYNONYMS.get(field, [field])
            if any(any(syn in col for syn in synonyms) for col in normalized):
                score += 1
        scores[schema_type] = score
    best = max(scores.items(), key=lambda item: item[1], default=("OTHER", 0))
    return best[0] if best[1] > 0 else "OTHER"


async def detect_table_schema(columns: list, sample_rows: list) -> dict:
    llm = get_llm_client("extraction")
    prompt = SCHEMA_DETECT_PROMPT.format(
        columns=columns[:20],
        sample=json.dumps(sample_rows[:3], default=str),
    )
    raw = await llm(prompt)
    try:
        parsed = json.loads(raw.strip())
        if isinstance(parsed, dict):
            schema_type = parsed.get("schema_type") or "OTHER"
            if schema_type not in SCHEMA_TYPES:
                schema_type = "OTHER"
            mapping = parsed.get("column_mapping") or {}
            if schema_type == "OTHER":
                schema_type = _guess_schema_type(columns)
            if schema_type in SCHEMA_COLUMNS and not mapping:
                mapping = _fuzzy_map_columns(columns, SCHEMA_COLUMNS[schema_type])
            parsed["schema_type"] = schema_type
            parsed["column_mapping"] = mapping
            return parsed
        return {"schema_type": _guess_schema_type(columns), "column_mapping": {}}
    except Exception:
        schema_type = _guess_schema_type(columns)
        mapping = _fuzzy_map_columns(columns, SCHEMA_COLUMNS.get(schema_type, []))
        return {"schema_type": schema_type, "column_mapping": mapping}


def normalize_table(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    mapping = schema.get("column_mapping", {})
    reverse_map = {value: key for key, value in mapping.items() if value}
    df_norm = df.rename(columns=reverse_map)
    schema_type = schema.get("schema_type") or "OTHER"
    expected = SCHEMA_COLUMNS.get(schema_type, [])
    for column in expected:
        if column not in df_norm.columns:
            df_norm[column] = None
    for col in ["debit", "credit", "balance", "amount"]:
        if col in df_norm.columns:
            df_norm[col] = pd.to_numeric(
                df_norm[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("(", "-", regex=False)
                .str.replace(")", "", regex=False)
                .str.replace(" ", "", regex=False),
                errors="coerce",
            )
    return df_norm
