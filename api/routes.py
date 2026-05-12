from datetime import datetime, timezone
import json
import logging
import traceback
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from agents.orchestrator import run_audit_pipeline
from config.settings import settings
from db.database import get_db
from db.models import (
    AuditSession,
    AuditFinding,
    AuditorFeedback,
    AuditScope,
    AccuracyMetric,
    ConsolidatedFinding,
    DocumentBundle,
    EvidenceLink,
    ExecutionPlan,
    ExtractedDocument,
    FileRecord,
    KnowledgeBaseEntry,
    NormalizedTable,
    RiskEntry,
    VersionedNote,
)
from services.file_handler import save_and_classify, validate_bundle
from services.finding_writer import create_finding_safe
from services.feedback_processor import process_feedback

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)


def _touch_session(db: Session, session_id: str, create_if_missing: bool) -> AuditSession:
    session = db.query(AuditSession).filter_by(id=session_id).first()
    if session:
        session.last_active_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
        return session

    existing_bundle = db.query(DocumentBundle).filter_by(session_id=session_id).first()
    if existing_bundle:
        session = AuditSession(id=session_id, status="ACTIVE")
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    if create_if_missing:
        session = AuditSession(id=session_id, status="ACTIVE")
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    raise HTTPException(404, "Session not found")


def _validation_errors_for_stage(validation: dict | None, stage: str) -> list[dict]:
    if not validation:
        return []
    errors = validation.get("errors") or []
    if stage == "BOTH":
        return errors
    return [error for error in errors if error.get("stage") == stage]


@router.get("/ping")
def ping():
    return {"status": "ok"}


@router.post("/sessions")
def create_session(db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())[:8]
    session = AuditSession(id=session_id, status="ACTIVE")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "status": "created"}


@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = _touch_session(db, session_id, create_if_missing=False)
    bundles_count = db.query(DocumentBundle).filter_by(session_id=session_id).count()
    files_count = (
        db.query(FileRecord)
        .join(DocumentBundle, FileRecord.bundle_id == DocumentBundle.id)
        .filter(DocumentBundle.session_id == session_id)
        .filter(FileRecord.file_path.isnot(None))
        .count()
    )
    return {
        "session_id": session.id,
        "status": session.status,
        "created_at": session.created_at,
        "last_active_at": session.last_active_at,
        "bundles_count": bundles_count,
        "files_count": files_count,
    }


@router.get("/sessions/{session_id}/files")
def list_session_files(session_id: str, db: Session = Depends(get_db)):
    _touch_session(db, session_id, create_if_missing=False)
    bundles = db.query(DocumentBundle).filter_by(session_id=session_id).all()
    if not bundles:
        return {"session_id": session_id, "files": []}

    bundle_ids = [bundle.id for bundle in bundles]
    records = (
        db.query(FileRecord)
        .filter(FileRecord.bundle_id.in_(bundle_ids))
        .filter(FileRecord.file_path.isnot(None))
        .order_by(FileRecord.filename)
        .all()
    )
    files = [
        {
            "file_id": record.id,
            "filename": record.filename,
            "format": record.format,
            "stage": record.stage,
            "status": record.validation_status,
        }
        for record in records
    ]
    return {"session_id": session_id, "files": files}


@router.post("/sessions/{session_id}/upload")
async def upload_files(
    session_id: str,
    files: list[UploadFile] = File(...),
    bundle_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    _touch_session(db, session_id, create_if_missing=True)
    results = []
    active_bundle_id = bundle_id
    for uploaded in files:
        try:
            record = await save_and_classify(uploaded, session_id, active_bundle_id)
        except ValueError as exc:
            if str(exc).startswith("size_limit"):
                raise HTTPException(413, "File too large")
            raise HTTPException(400, str(exc))
        if active_bundle_id is None:
            active_bundle_id = record.bundle_id
        results.append(
            {
                "file_id": record.id,
                "filename": record.filename,
                "format": record.format,
                "stage": record.stage,
                "status": record.validation_status,
            }
        )
    validation = validate_bundle(active_bundle_id) if active_bundle_id else None
    return {"session_id": session_id, "files": results, "validation": validation}


@router.post("/sessions/{session_id}/run")
async def run_audit(
    session_id: str,
    stage: str = Form("BOTH"),
    db: Session = Depends(get_db),
):
    bundles = db.query(DocumentBundle).filter_by(session_id=session_id).all()
    if not bundles:
        raise HTTPException(404, "No files found for this session")

    bundle_ids = [bundle.id for bundle in bundles]
    files = (
        db.query(FileRecord)
        .filter(FileRecord.bundle_id.in_(bundle_ids))
        .filter(FileRecord.validation_status != "MISSING")
        .filter(FileRecord.file_path.isnot(None))
        .all()
    )
    if not files:
        raise HTTPException(404, "No files found for this session")

    file_records = [
        {
            "id": record.id,
            "filename": record.filename,
            "format": record.format,
            "file_path": record.file_path,
            "stage": record.stage,
        }
        for record in files
    ]

    validation_errors: list[dict] = []
    for bundle in bundles:
        validation = validate_bundle(bundle.id)
        validation_errors.extend(_validation_errors_for_stage(validation, stage))
    if validation_errors:
        raise HTTPException(400, {"message": "Validation failed", "errors": validation_errors})

    try:
        result = await run_audit_pipeline(session_id, stage, file_records)
    except Exception as exc:
        logger.exception("Pipeline error for session %s", session_id)
        detail = {
            "message": "Pipeline error",
            "error": str(exc),
            "trace": traceback.format_exc(),
        }
        raise HTTPException(500, detail)

    file_ids = [record.id for record in files]
    if file_ids:
        db.query(ExtractedDocument).filter(ExtractedDocument.source_file_id.in_(file_ids)).delete(
            synchronize_session=False
        )
        db.query(NormalizedTable).filter(NormalizedTable.source_file_id.in_(file_ids)).delete(
            synchronize_session=False
        )

    for i, doc in enumerate(result.get("extracted_docs", []) or []):
        try:
            raw = doc.get("raw") or {}
            if isinstance(raw, dict):
                raw_type = raw.get("type")
            else:
                raw_type = None
            content: dict = {}
            if raw_type == "text" and isinstance(raw, dict):
                text = raw.get("content") or ""
                content = {"text": text[:10000]}
            elif raw_type == "table" and isinstance(raw, dict):
                table_content = raw.get("content") or {}
                if isinstance(table_content, list):
                    content = {"sheets": [f"Sheet_{j}" for j in range(len(table_content))]}
                elif isinstance(table_content, dict):
                    content = {"sheets": list(table_content.keys())}
                else:
                    content = {"sheets": []}
            elif isinstance(raw, list):
                content = {"items": len(raw)}

            table_meta = []
            if isinstance(raw, dict):
                for table_info in raw.get("tables") or []:
                    if not isinstance(table_info, dict):
                        continue
                    table_meta.append(
                        {
                            "page": table_info.get("page"),
                            "index": table_info.get("index"),
                            "rows": len(table_info.get("rows") or []),
                        }
                    )

            classification = doc.get("classification") or {}
            if not isinstance(classification, dict):
                classification = {}
            process_info = doc.get("process_info") or {}
            if not isinstance(process_info, dict):
                process_info = {}

            metadata = {
                "classification": classification,
                "process_info": process_info,
                "type": raw_type,
                "pages": raw.get("pages") if isinstance(raw, dict) else None,
                "tables": table_meta,
            }
            content_type = classification.get("doc_type") or raw_type or "UNKNOWN"
            db.add(
                ExtractedDocument(
                    source_file_id=doc.get("file_id"),
                    internal_process_map_id=doc.get("process_map_id"),
                    content_type=content_type,
                    content=content,
                    extraction_metadata=metadata,
                )
            )
        except Exception as e:
            raise HTTPException(500, f"Error processing extracted doc: {e}")

    with open("debug.log", "a") as f:
        f.write(f"[run_audit] Processing {len(result.get('normalized_tables', []) or [])} normalized tables\n")
        f.flush()

    for table in result.get("normalized_tables", []) or []:
        rows = []
        # Table data is now stored as dict with "data" and "columns" keys
        if "data" in table:
            rows = table.get("data", [])
        elif "dataframe" in table:
            df = table.get("dataframe")
            if df is not None and hasattr(df, "to_dict"):
                try:
                    rows = df.where(df.notna(), None).to_dict(orient="records")
                except Exception:
                    rows = df.to_dict(orient="records")
        
        if len(rows) > 500:
            rows = rows[:500]

        schema = table.get("schema") or {}
        db.add(
            NormalizedTable(
                source_file_id=table.get("file_id"),
                schema_type=schema.get("schema_type"),
                sheet_name=table.get("sheet_name"),
                source_page=table.get("source_page"),
                rows=rows,
                schema=schema,
            )
        )

    index_to_id: dict[int, str] = {}
    for idx, finding_data in enumerate(result.get("audit_findings", []), 1):
        finding, created = create_finding_safe(db, finding_data, session_id, stage)
        index_to_id[idx] = finding.id

        if created:
            for link in finding_data.get("evidence_links", []) or []:
                if not link.get("source_file_id") and not link.get("reference"):
                    continue
                db.add(
                    EvidenceLink(
                        finding_id=finding.id,
                        source_file_id=link.get("source_file_id"),
                        reference=link.get("reference"),
                    )
                )

    for consolidated in result.get("consolidated_findings", []) or []:
        interim_index = consolidated.get("interim_finding_index")
        fieldwork_index = consolidated.get("fieldwork_finding_index")
        interim_id = index_to_id.get(interim_index)
        fieldwork_id = index_to_id.get(fieldwork_index)
        db.add(
            ConsolidatedFinding(
                session_id=session_id,
                interim_finding_id=interim_id,
                fieldwork_finding_id=fieldwork_id,
                materiality=consolidated.get("materiality"),
                review_flag=bool(consolidated.get("review_flag")),
                confidence_score=consolidated.get("confidence_score", 0.0),
            )
        )

    for risk in result.get("risk_entries", []) or []:
        db.add(
            RiskEntry(
                id=risk.get("id"),
                session_id=session_id,
                description=risk.get("description", ""),
                probability=risk.get("probability", 0.0),
                impact=risk.get("impact", 0.0),
                risk_score=risk.get("risk_score", 0.0),
                owner=risk.get("owner", ""),
                related_controls=risk.get("related_controls", []),
            )
        )

    for note in result.get("versioned_notes", []) or []:
        db.add(
            VersionedNote(
                session_id=session_id,
                author="SYSTEM",
                change_description=str(note),
            )
        )

    db.commit()

    return {
        "session_id": session_id,
        "stage": stage,
        "findings_count": len(result.get("audit_findings", [])),
        "anomalies_count": len(result.get("anomaly_flags", [])),
        "control_tests_count": len(result.get("control_test_results", [])),
        "consolidated_count": len(result.get("consolidated_findings", [])),
        "output_paths": result.get("output_paths", {}),
        "changelog": result.get("versioned_notes", []),
        "audit_tasks": result.get("audit_tasks", []),
        "execution_plan": result.get("execution_plan", {}),
        "risk_control_matrix": result.get("risk_control_matrix", []),
    }


@router.get("/sessions/{session_id}/findings")
def get_findings(session_id: str, db: Session = Depends(get_db)):
    findings = db.query(AuditFinding).filter_by(session_id=session_id).all()
    finding_ids = [finding.id for finding in findings]

    links = []
    if finding_ids:
        links = db.query(EvidenceLink).filter(EvidenceLink.finding_id.in_(finding_ids)).all()
    link_map: dict[str, list[dict]] = {}
    for link in links:
        link_map.setdefault(link.finding_id, []).append(
            {
                "id": link.id,
                "source_file_id": link.source_file_id,
                "reference": link.reference,
            }
        )

    consolidated = db.query(ConsolidatedFinding).filter_by(session_id=session_id).all()
    consolidated_map: dict[str, dict] = {}
    for item in consolidated:
        if item.interim_finding_id:
            consolidated_map[item.interim_finding_id] = item
        if item.fieldwork_finding_id:
            consolidated_map[item.fieldwork_finding_id] = item
    return [
        {
            "id": finding.id,
            "stage": finding.stage,
            "description": finding.description,
            "severity": finding.severity,
            "status": finding.status,
            "confidence_score": finding.confidence_score,
            "evidence_links": link_map.get(finding.id, []),
            "materiality": consolidated_map.get(finding.id).materiality
            if consolidated_map.get(finding.id)
            else None,
            "review_flag": consolidated_map.get(finding.id).review_flag
            if consolidated_map.get(finding.id)
            else False,
        }
        for finding in findings
    ]


@router.get("/findings/{finding_id}/evidence-links")
def get_evidence_links(finding_id: str, db: Session = Depends(get_db)):
    links = db.query(EvidenceLink).filter_by(finding_id=finding_id).all()
    return [
        {
            "id": link.id,
            "finding_id": link.finding_id,
            "source_file_id": link.source_file_id,
            "reference": link.reference,
        }
        for link in links
    ]


@router.get("/sessions/{session_id}/execution-plan")
def get_execution_plan(session_id: str, db: Session = Depends(get_db)):
    scope = (
        db.query(AuditScope)
        .filter_by(session_id=session_id)
        .order_by(AuditScope.created_at.desc())
        .first()
    )
    if not scope:
        raise HTTPException(404, "Execution plan not found")

    plan = (
        db.query(ExecutionPlan)
        .filter_by(audit_scope_id=scope.id)
        .order_by(ExecutionPlan.created_at.desc())
        .first()
    )
    if not plan:
        return {"session_id": session_id, "execution_plan": None}

    return {
        "session_id": session_id,
        "audit_scope": {
            "id": scope.id,
            "stage": scope.stage,
            "objectives": scope.objectives,
            "risk_profile": scope.risk_profile,
            "created_at": scope.created_at,
        },
        "execution_plan": plan.tasks,
    }


@router.get("/sessions/{session_id}/consolidated-findings")
def get_consolidated_findings(session_id: str, db: Session = Depends(get_db)):
    consolidated = db.query(ConsolidatedFinding).filter_by(session_id=session_id).all()
    return [
        {
            "id": finding.id,
            "interim_finding_id": finding.interim_finding_id,
            "fieldwork_finding_id": finding.fieldwork_finding_id,
            "materiality": finding.materiality,
            "review_flag": finding.review_flag,
            "confidence_score": finding.confidence_score,
        }
        for finding in consolidated
    ]


@router.get("/sessions/{session_id}/download/{file_type}")
def download_output(session_id: str, file_type: str):
    base_dir = Path(settings.output_dir)
    file_map = {
        "issue_log": base_dir / f"issue_log_{session_id}.xlsx",
        "memo": base_dir / f"audit_memo_{session_id}.docx",
        "risk_register": base_dir / f"risk_register_{session_id}.xlsx",
        "evidence_pdf": base_dir / f"evidence_{session_id}.pdf",
        "versioned_notes": base_dir / f"versioned_notes_{session_id}.md",
    }
    path = file_map.get(file_type)
    if not path:
        raise HTTPException(400, "Unknown output type")

    if not path.exists():
        raise HTTPException(404, "Output file not found. Run the pipeline first.")

    return FileResponse(path, filename=path.name)


@router.post("/findings/{finding_id}/feedback")
def submit_feedback(
    finding_id: str,
    action: str = Form(...),
    comment: str = Form(""),
    corrected_value: str | None = Form(None),
    db: Session = Depends(get_db),
):
    corrected_payload = None
    if corrected_value:
        try:
            corrected_payload = json.loads(corrected_value)
        except Exception:
            corrected_payload = {"value": corrected_value}

    try:
        feedback = process_feedback(finding_id, action, comment, corrected_payload)
    except ValueError as exc:
        raise HTTPException(404, str(exc))

    return {
        "status": "feedback_recorded",
        "finding_id": finding_id,
        "action": action,
        "feedback_id": feedback.id,
    }


@router.get("/accuracy-metrics")
def get_accuracy_metrics(db: Session = Depends(get_db)):
    metrics = db.query(AccuracyMetric).all()
    return [
        {
            "id": metric.id,
            "session_id": metric.session_id,
            "finding_category": metric.finding_category,
            "total_findings": metric.total_findings,
            "accepted": metric.accepted,
            "rejected": metric.rejected,
            "modified": metric.modified,
            "accuracy_rate": metric.accuracy_rate,
            "calculated_at": metric.calculated_at,
        }
        for metric in metrics
    ]


@router.get("/knowledge-base")
def get_knowledge_base(db: Session = Depends(get_db)):
    entries = db.query(KnowledgeBaseEntry).all()
    return [
        {
            "id": entry.id,
            "pattern_type": entry.pattern_type,
            "description": entry.description,
            "source_session_id": entry.source_session_id,
            "confidence": entry.confidence,
            "created_at": entry.created_at,
            "applicable_stages": entry.applicable_stages,
        }
        for entry in entries
    ]
