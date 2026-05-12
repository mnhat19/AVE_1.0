from pathlib import Path
import os
import shutil

from config.settings import settings
from db.database import SessionLocal
from db.models import DocumentBundle, FileRecord
from services.validator import validate_bundle as _validate_bundle

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FORMAT_MAP = {
    ".pdf": "PDF",
    ".docx": "DOCX",
    ".doc": "DOCX",
    ".xlsx": "XLSX",
    ".xls": "XLSX",
    ".csv": "CSV",
    ".txt": "TXT",
    ".eml": "EML",
    ".pst": "PST",
    ".jpg": "IMAGE",
    ".jpeg": "IMAGE",
    ".png": "IMAGE",
    ".tiff": "IMAGE",
}

INTERIM_KEYWORDS = [
    "sox",
    "walkthrough",
    "control",
    "interim",
    "risk_matrix",
    "sop",
    "policy",
    "tobc",
]
FIELDWORK_KEYWORDS = [
    "trial_balance",
    "lead_schedule",
    "ageing",
    "reconciliation",
    "roll_forward",
    "confirmation",
    "inventory",
    "fieldwork",
    "journal",
    "ledger",
]


def classify_stage(filename: str) -> str:
    name = filename.lower()
    is_interim = any(keyword in name for keyword in INTERIM_KEYWORDS)
    is_fieldwork = any(keyword in name for keyword in FIELDWORK_KEYWORDS)
    if is_interim and not is_fieldwork:
        return "INTERIM"
    if is_fieldwork and not is_interim:
        return "FIELDWORK"
    return "BOTH"


def validate_bundle(bundle_id: str) -> dict:
    return _validate_bundle(bundle_id)


async def save_and_classify(file, session_id: str, bundle_id: str | None = None) -> FileRecord:
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > max_bytes:
        raise ValueError(f"size_limit:{file_size}")

    safe_name = Path(file.filename).name
    ext = Path(safe_name).suffix.lower()
    fmt = FORMAT_MAP.get(ext, "TXT")
    stage = classify_stage(safe_name)

    dest_dir = UPLOAD_DIR / session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_path = dest_dir / safe_name

    with open(file_path, "wb") as handle:
        shutil.copyfileobj(file.file, handle)

    db = SessionLocal()
    try:
        if not bundle_id:
            bundle = DocumentBundle(session_id=session_id, stage=stage)
            db.add(bundle)
            db.flush()
            bundle_id = bundle.id
        else:
            bundle = db.query(DocumentBundle).filter_by(id=bundle_id).first()
            if bundle and bundle.stage != stage and bundle.stage != "BOTH":
                bundle.stage = "BOTH"

        record = FileRecord(
            bundle_id=bundle_id,
            filename=safe_name,
            format=fmt,
            stage=stage,
            validation_status="VALID",
            file_path=str(file_path),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()
