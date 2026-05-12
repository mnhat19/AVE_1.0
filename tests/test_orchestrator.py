import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agents.orchestrator import generate_execution_plan, node_extract_documents
from db.models import Base, InternalProcessMap
from services.task_dispatcher import dispatch_tasks


def _make_scope(stage: str) -> dict:
    return {
        "session_id": "S1",
        "stage": stage,
        "objectives": [],
        "risk_profile": "MEDIUM",
    }


def test_execution_plan_interim_tasks():
    plan = generate_execution_plan(_make_scope("INTERIM"), [{"format": "XLSX"}])
    task_types = {task["task_type"] for task in plan["tasks"]}

    assert "TEST_OF_CONTROLS" in task_types
    assert "RISK_MATRIX" in task_types
    assert "RECONCILIATION" not in task_types


def test_execution_plan_fieldwork_tasks():
    plan = generate_execution_plan(_make_scope("FIELDWORK"), [{"format": "XLSX"}])
    task_types = {task["task_type"] for task in plan["tasks"]}

    assert "RECONCILIATION" in task_types
    assert "AGEING_ANALYSIS" in task_types
    assert "TEST_OF_CONTROLS" not in task_types


def test_dispatch_tasks_marks_dispatched():
    plan = generate_execution_plan(_make_scope("INTERIM"), [{"format": "XLSX"}])
    dispatch_map = dispatch_tasks(plan["tasks"])

    assert "DOC_AGENT" in dispatch_map
    assert all(task["status"] == "DISPATCHED" for task in plan["tasks"])


@pytest.mark.anyio
async def test_internal_process_map_created(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    import agents.doc_agent as doc_agent

    monkeypatch.setattr(doc_agent, "SessionLocal", SessionLocal)

    async def fake_classify(_content: str) -> dict:
        return {"doc_type": "SOP"}

    async def fake_process_info(_content: str) -> dict:
        return {
            "process_name": "Procurement",
            "control_objectives": ["Approval required"],
            "key_controls": [{"control_id": "C-001", "description": "Manager approval"}],
        }

    import agents.orchestrator as orchestrator

    monkeypatch.setattr(orchestrator, "classify_document", fake_classify)
    monkeypatch.setattr(orchestrator, "extract_process_info", fake_process_info)

    file_path = tmp_path / "sop.txt"
    file_path.write_text("SOP content", encoding="utf-8")

    state = {
        "session_id": "S1",
        "stage": "INTERIM",
        "file_records": [
            {
                "id": "F1",
                "filename": "sop.txt",
                "format": "TXT",
                "file_path": str(file_path),
            }
        ],
        "audit_tasks": [],
        "execution_plan": {},
        "extracted_docs": [],
        "normalized_tables": [],
        "anomaly_flags": [],
        "audit_findings": [],
        "risk_entries": [],
        "consolidated_findings": [],
        "versioned_notes": [],
        "errors": [],
        "output_paths": {},
    }

    await node_extract_documents(state)

    db = SessionLocal()
    try:
        record = db.query(InternalProcessMap).filter_by(session_id="S1").first()
        assert record is not None
        assert record.process_name == "Procurement"
    finally:
        db.close()
