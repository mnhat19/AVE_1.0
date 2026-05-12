from __future__ import annotations


def format_reference(location: dict) -> str:
    """Format a human-readable reference string from location metadata."""
    parts: list[str] = []
    sheet = location.get("sheet")
    rows = location.get("rows")
    if sheet:
        row = location.get("row")
        row_label = None
        if rows:
            if isinstance(rows, list) and len(rows) > 1:
                row_label = f"Rows {rows[0]}-{rows[-1]}"
            elif isinstance(rows, list) and len(rows) == 1:
                row_label = f"Row {rows[0]}"
        elif row is not None:
            row_label = f"Row {row}"

        if row_label:
            parts.append(f"{sheet}!{row_label}")
        else:
            parts.append(str(sheet))
    else:
        row = location.get("row")
        if rows:
            if isinstance(rows, list) and len(rows) > 1:
                parts.append(f"Rows {rows[0]}-{rows[-1]}")
            elif isinstance(rows, list) and len(rows) == 1:
                parts.append(f"Row {rows[0]}")
        elif row is not None:
            parts.append(f"Row {row}")
    page = location.get("page")
    if page is not None:
        parts.append(f"Page {page}")
    if not parts:
        return "Unknown"
    return " | ".join(parts)


def create_evidence_link(finding_id: str | None, source_file_id: str | None, location: dict) -> dict:
    """Build a serializable evidence link payload."""
    return {
        "finding_id": finding_id,
        "source_file_id": source_file_id,
        "reference": format_reference(location),
    }
