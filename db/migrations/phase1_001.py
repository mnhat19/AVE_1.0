from sqlalchemy import inspect, text


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column_sqlite(engine, table_name: str, column_name: str, column_type: str) -> None:
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def apply(engine) -> None:
    """Apply phase-1 schema changes for SQLite without breaking existing data."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "audit_findings" in tables and not _column_exists(inspector, "audit_findings", "idempotency_key"):
        _add_column_sqlite(engine, "audit_findings", "idempotency_key", "TEXT")

    if "validation_reports" in tables:
        if not _column_exists(inspector, "validation_reports", "warnings"):
            _add_column_sqlite(engine, "validation_reports", "warnings", "TEXT")
        if not _column_exists(inspector, "validation_reports", "errors"):
            _add_column_sqlite(engine, "validation_reports", "errors", "TEXT")
