from sqlalchemy import inspect, text


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column_sqlite(engine, table_name: str, column_name: str, column_type: str) -> None:
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def apply(engine) -> None:
    """Apply phase-3 schema changes for SQLite without breaking existing data."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "extracted_documents" in tables and not _column_exists(
        inspector, "extracted_documents", "internal_process_map_id"
    ):
        _add_column_sqlite(engine, "extracted_documents", "internal_process_map_id", "TEXT")
