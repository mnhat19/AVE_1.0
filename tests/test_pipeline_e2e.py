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
from db.models import Base
from services import feedback_processor


def _setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(database, "SessionLocal", SessionLocal)
    monkeypatch.setattr(orchestrator, "SessionLocal", SessionLocal)
    monkeypatch.setattr(doc_agent, "SessionLocal", SessionLocal)
    monkeypatch.setattr(feedback_processor, "SessionLocal", SessionLocal)

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
        if "Audit memo" in prompt:
            return "1. Audit objective\n2. Summary\n3. Key findings\n4. Root cause\n5. Next steps"
        return "{}"

    return fake_llm


def _seed_llm(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr(doc_agent, "get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr(data_agent, "get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr(audit_agent, "get_llm_client", _fake_get_llm_client)
    monkeypatch.setattr(output_generator, "get_llm_client", _fake_get_llm_client)


def test_pipeline_outputs_generated(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    _seed_llm(monkeypatch)

    root = Path(__file__).resolve().parents[1]
    data_dir = root / "test_data"

    files = [
        ("F1", "journal_entries.csv", "CSV"),
        ("F2", "trial_balance.xlsx", "XLSX"),
        ("F3", "sop_procurement.docx", "DOCX"),
        ("F4", "walkthrough_notes.pdf", "PDF"),
    ]

    file_records = []
    for file_id, name, fmt in files:
        path = data_dir / name
        assert path.exists()
        file_records.append(
            {
                "id": file_id,
                "filename": name,
                "format": fmt,
                "file_path": str(path),
                "stage": "INTERIM",
            }
        )

    state = asyncio.run(orchestrator.run_audit_pipeline("S1", "INTERIM", file_records))
    output_paths = state.get("output_paths", {})

    expected_keys = {
        "issue_log",
        "memo",
        "risk_register",
        "evidence_pdf",
        "versioned_notes",
    }
    assert expected_keys.issubset(output_paths.keys())

    for key in expected_keys:
        path = Path(output_paths[key])
        assert path.exists()
        path.unlink()
