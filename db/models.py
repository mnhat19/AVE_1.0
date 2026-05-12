from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def gen_id() -> str:
    return str(uuid.uuid4())[:8]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditSession(Base):
    __tablename__ = "audit_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    last_active_at = Column(DateTime(timezone=True), default=utcnow)


class DocumentBundle(Base):
    __tablename__ = "document_bundles"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, nullable=False)
    stage = Column(String)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class FileRecord(Base):
    __tablename__ = "file_records"

    id = Column(String, primary_key=True, default=gen_id)
    bundle_id = Column(String, ForeignKey("document_bundles.id"))
    filename = Column(String)
    format = Column(String)
    stage = Column(String)
    validation_status = Column(String, default="PENDING")
    file_path = Column(String)


class AuditFinding(Base):
    __tablename__ = "audit_findings"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String)
    stage = Column(String)
    description = Column(String)
    root_cause = Column(String)
    expected_impact = Column(String)
    severity = Column(String, default="MEDIUM")
    assignee = Column(String)
    status = Column(String, default="OPEN")
    confidence_score = Column(Float, default=0.0)
    source_file_id = Column(String)
    source_reference = Column(String)
    idempotency_key = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class RiskEntry(Base):
    __tablename__ = "risk_entries"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String)
    description = Column(String)
    probability = Column(Float, default=0.5)
    impact = Column(Float, default=0.5)
    risk_score = Column(Float)
    owner = Column(String)
    related_controls = Column(JSON)


class VersionedNote(Base):
    __tablename__ = "versioned_notes"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String)
    timestamp = Column(DateTime(timezone=True), default=utcnow)
    author = Column(String, default="SYSTEM")
    change_description = Column(String)


class AuditorFeedback(Base):
    __tablename__ = "auditor_feedback"

    id = Column(String, primary_key=True, default=gen_id)
    finding_id = Column(String, ForeignKey("audit_findings.id"))
    action = Column(String)
    comment = Column(String)
    corrected_value = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class ValidationReport(Base):
    __tablename__ = "validation_reports"

    id = Column(String, primary_key=True, default=gen_id)
    bundle_id = Column(String, ForeignKey("document_bundles.id"))
    stage = Column(String)
    missing_items = Column(JSON)
    warnings = Column(JSON)
    errors = Column(JSON)
    is_complete = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AuditScope(Base):
    __tablename__ = "audit_scopes"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, nullable=False)
    objectives = Column(JSON)
    stage = Column(String)
    risk_profile = Column(String)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class ExecutionPlan(Base):
    __tablename__ = "execution_plans"

    id = Column(String, primary_key=True, default=gen_id)
    audit_scope_id = Column(String, ForeignKey("audit_scopes.id"))
    tasks = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow)


class InternalProcessMap(Base):
    __tablename__ = "internal_process_maps"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, nullable=False)
    source_file_id = Column(String, ForeignKey("file_records.id"))
    process_name = Column(String)
    process_steps = Column(JSON)
    controls_identified = Column(JSON)
    extracted_at = Column(DateTime(timezone=True), default=utcnow)


class AccuracyMetric(Base):
    __tablename__ = "accuracy_metrics"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, nullable=False)
    finding_category = Column(String)
    total_findings = Column(Integer, default=0)
    accepted = Column(Integer, default=0)
    rejected = Column(Integer, default=0)
    modified = Column(Integer, default=0)
    accuracy_rate = Column(Float, default=0.0)
    calculated_at = Column(DateTime(timezone=True), default=utcnow)


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base_entries"

    id = Column(String, primary_key=True, default=gen_id)
    pattern_type = Column(String)
    description = Column(String)
    source_session_id = Column(String)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    applicable_stages = Column(JSON)


class EvidenceLink(Base):
    __tablename__ = "evidence_links"

    id = Column(String, primary_key=True, default=gen_id)
    finding_id = Column(String, ForeignKey("audit_findings.id"))
    source_file_id = Column(String)
    reference = Column(String)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class ConsolidatedFinding(Base):
    __tablename__ = "consolidated_findings"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String)
    interim_finding_id = Column(String, ForeignKey("audit_findings.id"))
    fieldwork_finding_id = Column(String, ForeignKey("audit_findings.id"))
    materiality = Column(String)
    review_flag = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class ExtractedDocument(Base):
    __tablename__ = "extracted_documents"

    id = Column(String, primary_key=True, default=gen_id)
    source_file_id = Column(String, ForeignKey("file_records.id"))
    internal_process_map_id = Column(String, ForeignKey("internal_process_maps.id"))
    content_type = Column(String)
    content = Column(JSON)
    extraction_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class NormalizedTable(Base):
    __tablename__ = "normalized_tables"

    id = Column(String, primary_key=True, default=gen_id)
    source_file_id = Column(String, ForeignKey("file_records.id"))
    schema_type = Column(String)
    sheet_name = Column(String)
    source_page = Column(Integer)
    rows = Column(JSON)
    schema = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utcnow)
