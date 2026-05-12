from __future__ import annotations

import hashlib

from db.models import AuditFinding


def compute_idempotency_key(source_file_id: str | None, rule_id: str | None, location_ref: str | None) -> str:
    """Compute a stable hash to prevent duplicate findings for the same evidence location."""
    safe_source = source_file_id or ""
    safe_rule = rule_id or ""
    safe_location = location_ref or ""
    raw = f"{safe_source}:{safe_rule}:{safe_location}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_finding_safe(
    db,
    finding_data: dict,
    session_id: str,
    stage: str,
) -> tuple[AuditFinding, bool]:
    """Insert a finding if its idempotency key is new; return (finding, created)."""
    source_file_id = finding_data.get("source_file_id")
    rule_id = finding_data.get("rule_id")
    location_ref = finding_data.get("location_ref") or finding_data.get("source_reference")
    idempotency_key = compute_idempotency_key(source_file_id, rule_id, location_ref)

    existing = db.query(AuditFinding).filter_by(idempotency_key=idempotency_key).first()
    if existing:
        return existing, False

    finding = AuditFinding(
        session_id=session_id,
        stage=stage,
        description=finding_data.get("description", ""),
        root_cause=finding_data.get("root_cause", ""),
        expected_impact=finding_data.get("expected_impact", ""),
        severity=finding_data.get("severity", "MEDIUM"),
        assignee="Audit Team",
        status="OPEN",
        confidence_score=finding_data.get("confidence_score", 0.0),
        source_file_id=source_file_id,
        source_reference=finding_data.get("source_reference"),
        idempotency_key=idempotency_key,
    )
    db.add(finding)
    db.flush()
    return finding, True
