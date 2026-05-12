from __future__ import annotations

from db.database import SessionLocal
from db.models import DocumentBundle, FileRecord, ValidationReport, VersionedNote

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


def _records_for_stage(records: list[FileRecord], stage: str) -> list[FileRecord]:
    return [
        record
        for record in records
        if record.stage in {stage, "BOTH"}
    ]


def _formats_for_stage(records: list[FileRecord], stage: str) -> set[str]:
    return {
        record.format
        for record in _records_for_stage(records, stage)
        if record.format
    }


def _build_error(stage: str, rule_id: str, message: str, expected_formats: list[str]) -> dict:
    return {
        "stage": stage,
        "rule_id": rule_id,
        "message": message,
        "expected_formats": expected_formats,
    }


def _required_format_errors(records: list[FileRecord], stage: str) -> list[dict]:
    formats = _formats_for_stage(records, stage)
    errors: list[dict] = []

    if stage == "INTERIM":
        if not formats.intersection({"DOCX", "PDF"}):
            errors.append(
                _build_error(
                    stage,
                    "INTERIM_DOC_REQUIRED",
                    "Require at least one SOP/policy document in DOCX or PDF.",
                    ["DOCX", "PDF"],
                )
            )
        if not formats.intersection({"XLSX", "CSV"}):
            errors.append(
                _build_error(
                    stage,
                    "INTERIM_DATA_REQUIRED",
                    "Require at least one risk matrix or ERP data file in XLSX or CSV.",
                    ["XLSX", "CSV"],
                )
            )
    elif stage == "FIELDWORK":
        if "XLSX" not in formats:
            errors.append(
                _build_error(
                    stage,
                    "FIELDWORK_XLSX_REQUIRED",
                    "Require at least one trial balance or lead schedule in XLSX.",
                    ["XLSX"],
                )
            )
        if not formats.intersection({"PDF", "IMAGE"}):
            errors.append(
                _build_error(
                    stage,
                    "FIELDWORK_EVIDENCE_REQUIRED",
                    "Require at least one evidence file in PDF or image format.",
                    ["PDF", "IMAGE"],
                )
            )

    return errors


def validate_bundle(bundle_id: str) -> dict:
    db = SessionLocal()
    try:
        bundle = db.query(DocumentBundle).filter_by(id=bundle_id).first()
        if not bundle:
            return {
                "bundle_id": bundle_id,
                "missing_items": [],
                "warnings": [],
                "errors": [],
                "is_complete": True,
            }

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
            errors = _required_format_errors(records, "INTERIM")
            errors.extend(_required_format_errors(records, "FIELDWORK"))
        else:
            missing_items = _missing_items_for_stage(filenames, bundle.stage)
            errors = _required_format_errors(records, bundle.stage)

        warnings = [
            {
                "stage": item["stage"],
                "rule_id": "KEYWORD_MISSING",
                "item": item["item"],
                "keywords": item["keywords"],
            }
            for item in missing_items
        ]

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
            warnings=warnings,
            errors=errors,
            is_complete=len(errors) == 0,
        )
        db.add(report)

        if errors:
            change_description = f"Validation blocked: {len(errors)} required rules failed"
        elif missing_items:
            change_description = f"Validation warnings: {len(missing_items)} items missing"
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
            "warnings": warnings,
            "errors": errors,
            "is_complete": len(errors) == 0,
        }
    finally:
        db.close()
