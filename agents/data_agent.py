import json

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
            return parsed
        return {"schema_type": "OTHER", "column_mapping": {}}
    except Exception:
        return {"schema_type": "OTHER", "column_mapping": {}}


def normalize_table(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    mapping = schema.get("column_mapping", {})
    reverse_map = {value: key for key, value in mapping.items() if value}
    df_norm = df.rename(columns=reverse_map)
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
