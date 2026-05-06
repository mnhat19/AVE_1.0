from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from agents.orchestrator import run_audit_pipeline
from config.settings import settings
from db.database import get_db
from db.models import (
    AuditFinding,
    AuditorFeedback,
    ConsolidatedFinding,
    DocumentBundle,
    EvidenceLink,
    ExtractedDocument,
    FileRecord,
    NormalizedTable,
    RiskEntry,
    VersionedNote,
)
from services.file_handler import save_and_classify, validate_bundle

router = APIRouter(prefix="/api/v1")


@router.get("/ping")
def ping():
    return {"status": "ok"}


@router.post("/sessions")
def create_session():
    session_id = str(uuid.uuid4())[:8]
    return {"session_id": session_id, "status": "created"}


@router.post("/sessions/{session_id}/upload")
async def upload_files(
    session_id: str,
    files: list[UploadFile] = File(...),
    bundle_id: str | None = Form(None),
):
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

    try:
        result = await run_audit_pipeline(session_id, stage, file_records)
    except Exception as exc:
        raise HTTPException(500, f"Pipeline error: {exc}")

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
                    content_type=content_type,
                    content=content,
                    metadata=metadata,
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
            source_reference=finding_data.get("source_reference"),
        )
        db.add(finding)
        db.flush()
        index_to_id[idx] = finding.id

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
        source_index = consolidated.get("source_finding_index")
        source_id = index_to_id.get(source_index)
        db.add(
            ConsolidatedFinding(
                session_id=session_id,
                interim_finding_id=source_id,
                fieldwork_finding_id=None,
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
        "consolidated_count": len(result.get("consolidated_findings", [])),
        "output_paths": result.get("output_paths", {}),
        "changelog": result.get("versioned_notes", []),
        "audit_tasks": result.get("audit_tasks", []),
        "execution_plan": result.get("execution_plan", {}),
    }


@router.get("/sessions/{session_id}/findings")
def get_findings(session_id: str, db: Session = Depends(get_db)):
    findings = db.query(AuditFinding).filter_by(session_id=session_id).all()
    return [
        {
            "id": finding.id,
            "stage": finding.stage,
            "description": finding.description,
            "severity": finding.severity,
            "status": finding.status,
            "confidence_score": finding.confidence_score,
        }
        for finding in findings
    ]


@router.get("/sessions/{session_id}/download/{file_type}")
def download_output(session_id: str, file_type: str):
    base_dir = Path(settings.output_dir)
    file_map = {
        "issue_log": base_dir / f"issue_log_{session_id}.xlsx",
        "memo": base_dir / f"audit_memo_{session_id}.docx",
        "risk_register": base_dir / f"risk_register_{session_id}.xlsx",
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
    db: Session = Depends(get_db),
):
    finding = db.query(AuditFinding).filter_by(id=finding_id).first()
    if not finding:
        raise HTTPException(404, "Finding not found")

    feedback = AuditorFeedback(
        finding_id=finding_id,
        action=action,
        comment=comment,
    )
    db.add(feedback)

    if action in {"ACCEPT", "REJECT"}:
        finding.status = "RESOLVED"
    elif action == "MODIFY":
        finding.status = "IN_PROGRESS"

    db.commit()
    return {"status": "feedback_recorded", "finding_id": finding_id, "action": action}
