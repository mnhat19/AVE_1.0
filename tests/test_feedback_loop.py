import asyncio
import json
from pathlib import Path

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.audit_agent as audit_agent
import agents.data_agent as data_agent
import agents.doc_agent as doc_agent
import agents.orchestrator as orchestrator
import services.output_generator as output_generator
from db import database
from db.models import Base, AuditFinding, KnowledgeBaseEntry
from services import feedback_processor


def _setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(feedback_processor, "SessionLocal", SessionLocal)
    monkeypatch.setattr(database, "SessionLocal", SessionLocal)
    monkeypatch.setattr(orchestrator, "SessionLocal", SessionLocal)
    monkeypatch.setattr(doc_agent, "SessionLocal", SessionLocal)
    return SessionLocal


def _fake_get_llm_client(_task_type: str = "reasoning"):
    async def fake_llm(prompt: str, system: str = "") -> str:
        if "Analyze the audit files" in prompt and "objectives" in prompt:
            return json.dumps({"objectives": ["Test objective"], "risk_profile": "LOW"})
        if "Identify the schema type" in prompt and "schema_type" in prompt:
            if "balance" in prompt.lower():
                schema_type = "TRIAL_BALANCE"
            else:
                schema_type = "JOURNAL"
            return json.dumps(
                {
                    "schema_type": schema_type,
                    "column_mapping": {},
                    "currency_detected": "VND",
                    "period_detected": None,
                }
            )
        if "Return this JSON structure" in prompt and "doc_type" in prompt:
            return json.dumps(
                {
                    "doc_type": "SOP",
                    "audit_stage": "INTERIM",
                    "key_entities": [],
                    "summary": "Test summary",
                    "internal_controls_mentioned": ["Approval"],
                    "confidence": 0.7,
                }
            )
        if "Extract internal control information" in prompt:
            return json.dumps(
                {
                    "process_name": "Procurement",
                    "control_objectives": ["Approval required"],
                    "key_controls": [
                        {
                            "control_id": "C-001",
                            "description": "Manager approval",
                            "type": "PREVENTIVE",
                            "frequency": "MONTHLY",
                        }
                    ],
                    "risk_indicators": [],
                }
            )
        if "Return JSON array" in prompt and "audit findings" in prompt:
            return json.dumps(
                [
                    {
                        "description": "Test finding",
                        "root_cause": "Test cause",
                        "expected_impact": "Test impact",
                        "severity": "LOW",
                        "confidence_score": 0.6,
                        "related_anomaly_rules": [],
                        "recommended_action": "Review",
                    }
                ]
            )
        if "Analyze the auditor feedback" in prompt and "pattern_type" in prompt:
            return json.dumps(
                {
                    "pattern_type": "control_failure",
                    "description": "Missing approval evidence",
                    "applicable_stages": ["INTERIM"],
                }
            )
        if "Audit memo" in prompt:
            return "1. Audit objective\n2. Summary\n3. Key findings\n4. Root cause\n5. Next steps"
        return "{}"

    return fake_llm


def _seed_llm(monkeypatch):
    monkeypatch.setattr(feedback_processor, "get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr(orchestrator, "get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr(doc_agent, "get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr(data_agent, "get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr(audit_agent, "get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr(output_generator, "get_llm_client", _fake_get_llm_client)


def test_feedback_creates_knowledge_entry(tmp_path, monkeypatch):
    SessionLocal = _setup_db(tmp_path, monkeypatch)
    _seed_llm(monkeypatch)
    db = SessionLocal()
    try:
        finding = AuditFinding(
            session_id="S1",
            stage="INTERIM",
            description="Policy missing approval",
            severity="HIGH",
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
    finally:
        db.close()

    feedback = feedback_processor.process_feedback(
        finding.id,
        "REJECT",
        "Need approval evidence",
        {"approval": "missing"},
    )

    db = SessionLocal()
    try:
        entries = db.query(feedback_processor.KnowledgeBaseEntry).all()
        assert feedback.id is not None
        assert len(entries) == 1
        assert entries[0].pattern_type == "control_failure"
    finally:
        db.close()


def test_feedback_improves_pipeline_priorities(tmp_path, monkeypatch):
    SessionLocal = _setup_db(tmp_path, monkeypatch)
    _seed_llm(monkeypatch)

    db = SessionLocal()
    try:
        finding = AuditFinding(
            session_id="S2",
            stage="INTERIM",
            description="Policy missing approval",
            severity="HIGH",
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
    finally:
        db.close()

    feedback_processor.process_feedback(
        finding.id,
        "REJECT",
        "Need approval evidence",
        {"approval": "missing"},
    )

    root = Path(__file__).resolve().parents[1]
    data_dir = root / "test_data"
    file_records = [
        {
            "id": "F1",
            "filename": "journal_entries.csv",
            "format": "CSV",
            "file_path": str(data_dir / "journal_entries.csv"),
            "stage": "INTERIM",
        },
        {
            "id": "F2",
            "filename": "trial_balance.xlsx",
            "format": "XLSX",
            "file_path": str(data_dir / "trial_balance.xlsx"),
            "stage": "INTERIM",
        },
        {
            "id": "F3",
            "filename": "sop_procurement.docx",
            "format": "DOCX",
            "file_path": str(data_dir / "sop_procurement.docx"),
            "stage": "INTERIM",
        },
    ]

    state = asyncio.run(orchestrator.run_audit_pipeline("S2", "INTERIM", file_records))

    db = SessionLocal()
    try:
        entries = db.query(KnowledgeBaseEntry).all()
        assert entries
    finally:
        db.close()

    assert state.get("knowledge_entries")
    task_priorities = {
        task.get("task_type"): task.get("priority")
        for task in state.get("execution_plan", {}).get("tasks", [])
    }
    assert task_priorities.get("TEST_OF_CONTROLS") == 1
    assert task_priorities.get("RISK_MATRIX") == 1

    for path in state.get("output_paths", {}).values():
        Path(path).unlink()
