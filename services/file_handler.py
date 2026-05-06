from pathlib import Path
import os
import shutil

from config.settings import settings
from db.database import SessionLocal
from db.models import DocumentBundle, FileRecord, ValidationReport, VersionedNote

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

INTERIM_REQUIRED = {
    "sop_policy": ["sop", "policy", "procedure"],
    "walkthrough_notes": ["walkthrough", "tobc", "control"],
    "risk_matrix": ["risk_matrix", "rcm", "risk_control"],
}

FIELDWORK_REQUIRED = {
    "trial_balance": ["trial_balance", "trialbalance"],
    "lead_schedule": ["lead_schedule", "lead-schedule"],
    "ageing": ["ageing", "aging"],
    "reconciliation": ["reconciliation", "recon", "roll_forward", "rollforward"],
    "confirmation": ["confirmation", "confirm", "bank", "inventory"],
}


def _has_keyword(filenames: list[str], keywords: list[str]) -> bool:
    return any(keyword in name for name in filenames for keyword in keywords)


def _missing_items_for_stage(filenames: list[str], stage: str) -> list[dict]:
    if stage == "INTERIM":
        required_map = INTERIM_REQUIRED
    elif stage == "FIELDWORK":
        required_map = FIELDWORK_REQUIRED
    else:
        return []

    missing = []
    for item, keywords in required_map.items():
        if not _has_keyword(filenames, keywords):
            missing.append({"item": item, "stage": stage, "keywords": keywords})
    return missing


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
    db = SessionLocal()
    try:
        bundle = db.query(DocumentBundle).filter_by(id=bundle_id).first()
        if not bundle:
            return {"bundle_id": bundle_id, "missing_items": [], "is_complete": True}

        records = (
            db.query(FileRecord)
            .filter_by(bundle_id=bundle_id)
            .filter(FileRecord.validation_status != "MISSING")
            .all()
        )
        filenames = [record.filename.lower() for record in records if record.filename]

        if bundle.stage == "BOTH":
            missing_items = _missing_items_for_stage(filenames, "INTERIM")
            missing_items.extend(_missing_items_for_stage(filenames, "FIELDWORK"))
        else:
            missing_items = _missing_items_for_stage(filenames, bundle.stage)

        db.query(FileRecord).filter_by(bundle_id=bundle_id, validation_status="MISSING").delete(
            synchronize_session=False
        )

        for item in missing_items:
            placeholder = FileRecord(
                bundle_id=bundle_id,
                filename=f"__MISSING__{item['stage'].lower()}__{item['item']}",
                format="MISSING",
                stage=item["stage"],
                validation_status="MISSING",
                file_path=None,
            )
            db.add(placeholder)

        db.query(ValidationReport).filter_by(bundle_id=bundle_id).delete(synchronize_session=False)
        report = ValidationReport(
            bundle_id=bundle_id,
            stage=bundle.stage,
            missing_items=missing_items,
            is_complete=len(missing_items) == 0,
        )
        db.add(report)

        if missing_items:
            change_description = f"Validation incomplete: {len(missing_items)} items missing"
        else:
            change_description = "Validation complete: all required items present"
        note = VersionedNote(
            session_id=bundle.session_id,
            author="SYSTEM",
            change_description=change_description,
        )
        db.add(note)
        db.commit()
        return {
            "bundle_id": bundle_id,
            "stage": bundle.stage,
            "missing_items": missing_items,
            "is_complete": len(missing_items) == 0,
        }
    finally:
        db.close()


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
