from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, DocumentBundle, FileRecord
from services import validator


def _add_bundle(session, stage: str) -> DocumentBundle:
    bundle = DocumentBundle(session_id="S1", stage=stage)
    session.add(bundle)
    session.commit()
    session.refresh(bundle)
    return bundle


def _add_file(session, bundle_id: str, filename: str, fmt: str, stage: str) -> None:
    record = FileRecord(
        bundle_id=bundle_id,
        filename=filename,
        format=fmt,
        stage=stage,
        validation_status="VALID",
        file_path="/tmp/file",
    )
    session.add(record)
    session.commit()


def _setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(validator, "SessionLocal", SessionLocal)
    return SessionLocal


def test_interim_requires_data_file(tmp_path, monkeypatch):
    SessionLocal = _setup_db(tmp_path, monkeypatch)
    session = SessionLocal()
    try:
        bundle = _add_bundle(session, "INTERIM")
        _add_file(session, bundle.id, "sop_policy.docx", "DOCX", "INTERIM")

        result = validator.validate_bundle(bundle.id)
        rule_ids = {error.get("rule_id") for error in result.get("errors", [])}

        assert "INTERIM_DATA_REQUIRED" in rule_ids
        assert "INTERIM_DOC_REQUIRED" not in rule_ids
        assert result.get("is_complete") is False
    finally:
        session.close()


def test_fieldwork_requires_evidence_file(tmp_path, monkeypatch):
    SessionLocal = _setup_db(tmp_path, monkeypatch)
    session = SessionLocal()
    try:
        bundle = _add_bundle(session, "FIELDWORK")
        _add_file(session, bundle.id, "trial_balance.xlsx", "XLSX", "FIELDWORK")

        result = validator.validate_bundle(bundle.id)
        rule_ids = {error.get("rule_id") for error in result.get("errors", [])}

        assert "FIELDWORK_EVIDENCE_REQUIRED" in rule_ids
        assert result.get("is_complete") is False
    finally:
        session.close()
