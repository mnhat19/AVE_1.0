from __future__ import annotations

import asyncio
from threading import Thread
import json
from datetime import datetime, timezone

from config.llm import get_llm_client
from db.database import SessionLocal
from db.models import AccuracyMetric, AuditFinding, AuditorFeedback, KnowledgeBaseEntry, VersionedNote


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _category_from_finding(finding: AuditFinding) -> str:
    stage = (finding.stage or "").upper()
    if stage == "INTERIM":
        return "TEST_OF_CONTROLS"
    if stage == "FIELDWORK":
        return "FIELDWORK_CHECKS"
    return "GENERAL"


def calculate_accuracy_metric(db, session_id: str, category: str) -> AccuracyMetric:
    feedbacks = (
        db.query(AuditorFeedback)
        .join(AuditFinding, AuditorFeedback.finding_id == AuditFinding.id)
        .filter(AuditFinding.session_id == session_id)
        .filter(AuditFinding.stage.isnot(None))
        .all()
    )

    total = 0
    accepted = 0
    rejected = 0
    modified = 0

    for feedback in feedbacks:
        finding = db.query(AuditFinding).filter_by(id=feedback.finding_id).first()
        if not finding:
            continue
        if _category_from_finding(finding) != category:
            continue
        total += 1
        action = (feedback.action or "").upper()
        if action == "ACCEPT":
            accepted += 1
        elif action == "REJECT":
            rejected += 1
        elif action == "MODIFY":
            modified += 1

    accuracy_rate = accepted / total if total else 0.0

    metric = (
        db.query(AccuracyMetric)
        .filter_by(session_id=session_id, finding_category=category)
        .first()
    )
    if not metric:
        metric = AccuracyMetric(session_id=session_id, finding_category=category)
        db.add(metric)

    metric.total_findings = total
    metric.accepted = accepted
    metric.rejected = rejected
    metric.modified = modified
    metric.accuracy_rate = accuracy_rate
    metric.calculated_at = datetime.now(timezone.utc)

    return metric


def _run_llm(prompt: str) -> str:
    llm = get_llm_client("extraction")
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop and running_loop.is_running():
        result: dict[str, str] = {}

        def _runner():
            result["value"] = asyncio.run(llm(prompt))

        thread = Thread(target=_runner)
        thread.start()
        thread.join()
        return result.get("value", "")

    return asyncio.run(llm(prompt))


def extract_knowledge_pattern(feedback: AuditorFeedback, finding: AuditFinding) -> KnowledgeBaseEntry | None:
    prompt = (
        "Analyze the auditor feedback and finding to extract a reusable knowledge pattern.\n"
        f"Finding: {finding.description}\n"
        f"Feedback action: {feedback.action}\n"
        f"Comment: {feedback.comment}\n"
        f"Corrected value: {feedback.corrected_value}\n\n"
        "Return JSON:\n"
        "{\n"
        '  "pattern_type": "anomaly|control_failure|data_quality|other",\n'
        '  "description": "short reusable pattern",\n'
        '  "applicable_stages": ["INTERIM", "FIELDWORK"]\n'
        "}\n"
        "Return only valid JSON."
    )

    raw = ""
    try:
        raw = _run_llm(prompt)
    except Exception:
        raw = ""

    pattern_type = "other"
    description = ""
    stages = [finding.stage] if finding.stage else []

    try:
        parsed = json.loads(raw.strip()) if raw else {}
        if isinstance(parsed, dict):
            pattern_type = parsed.get("pattern_type") or pattern_type
            description = parsed.get("description") or description
            stages = parsed.get("applicable_stages") or stages
    except Exception:
        description = ""

    if not description:
        return None

    confidence = 1.0 if (feedback.action or "").upper() == "REJECT" else 0.7
    return KnowledgeBaseEntry(
        pattern_type=pattern_type,
        description=description,
        source_session_id=finding.session_id,
        confidence=_safe_float(confidence),
        applicable_stages=stages,
    )


def process_feedback(
    finding_id: str,
    action: str,
    comment: str,
    corrected_value: dict | None,
) -> AuditorFeedback:
    """Persist feedback, update accuracy metrics, and create knowledge entries."""
    db = SessionLocal()
    try:
        finding = db.query(AuditFinding).filter_by(id=finding_id).first()
        if not finding:
            raise ValueError("Finding not found")

        feedback = AuditorFeedback(
            finding_id=finding_id,
            action=action,
            comment=comment,
            corrected_value=corrected_value,
        )
        db.add(feedback)

        action_upper = (action or "").upper()
        if action_upper in {"ACCEPT", "REJECT"}:
            finding.status = "RESOLVED"
        elif action_upper == "MODIFY":
            finding.status = "IN_PROGRESS"

        category = _category_from_finding(finding)
        calculate_accuracy_metric(db, finding.session_id, category)

        if action_upper in {"REJECT", "MODIFY"}:
            entry = extract_knowledge_pattern(feedback, finding)
            if entry:
                db.add(entry)

        note = VersionedNote(
            session_id=finding.session_id,
            author="AUDITOR",
            change_description=f"Auditor {action_upper} finding {finding.id}: {comment}",
        )
        db.add(note)

        db.commit()
        db.refresh(feedback)
        return feedback
    finally:
        db.close()


def load_relevant_knowledge(session_stage: str) -> list[KnowledgeBaseEntry]:
    db = SessionLocal()
    try:
        entries = (
            db.query(KnowledgeBaseEntry)
            .order_by(KnowledgeBaseEntry.confidence.desc())
            .all()
        )
    finally:
        db.close()

    stage = (session_stage or "").upper()
    filtered = [
        entry
        for entry in entries
        if not entry.applicable_stages or stage in entry.applicable_stages
    ]
    return filtered[:50]
