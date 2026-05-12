import pandas as pd
import pytest

from agents.data_agent import normalize_table


@pytest.mark.parametrize(
    "schema_type,columns,expected",
    [
        (
            "TRIAL_BALANCE",
            ["account_code", "debit", "credit", "balance"],
            ["account_code", "account_name", "debit", "credit", "balance"],
        ),
        (
            "JOURNAL",
            ["date", "journal_id", "amount"],
            ["date", "journal_id", "debit_account", "credit_account", "amount", "description"],
        ),
        (
            "LEAD_SCHEDULE",
            ["line_item", "current_year"],
            ["line_item", "prior_year", "current_year", "variance"],
        ),
        (
            "AGEING",
            ["customer", "total"],
            [
                "customer",
                "bucket_0_30",
                "bucket_31_60",
                "bucket_61_90",
                "bucket_90_plus",
                "total",
            ],
        ),
        (
            "RECONCILIATION",
            ["item", "book_balance"],
            ["item", "book_balance", "bank_balance", "difference"],
        ),
    ],
)
def test_schema_specific_columns(schema_type, columns, expected):
    df = pd.DataFrame([{col: 1 for col in columns}])
    schema = {"schema_type": schema_type, "column_mapping": {}}
    normalized = normalize_table(df, schema)

    for column in expected:
        assert column in normalized.columns
