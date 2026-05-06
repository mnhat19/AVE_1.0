import asyncio
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000/api/v1"
TEST_DATA_DIR = Path("test_data")


async def test_full_flow():
    async with httpx.AsyncClient(timeout=120) as client:
        session_resp = await client.post(f"{BASE_URL}/sessions")
        session_resp.raise_for_status()
        session_id = session_resp.json()["session_id"]
        print(f"Session: {session_id}")

        files = []
        for name in [
            "journal_entries.csv",
            "trial_balance.xlsx",
            "sop_procurement.docx",
            "walkthrough_notes.pdf",
        ]:
            path = TEST_DATA_DIR / name
            if path.exists():
                files.append(("files", (name, path.read_bytes())))

        if not files:
            raise RuntimeError("No test_data files found. Run test_data/generate_test_data.py first.")

        upload_resp = await client.post(
            f"{BASE_URL}/sessions/{session_id}/upload",
            files=files,
        )
        upload_resp.raise_for_status()
        upload_payload = upload_resp.json()
        print(f"Upload: {upload_payload}")
        validation = upload_payload.get("validation")
        if validation:
            missing_items = validation.get("missing_items", [])
            print(f"Validation missing items: {len(missing_items)}")
            if missing_items:
                print(f"Missing detail: {missing_items}")

        run_resp = await client.post(
            f"{BASE_URL}/sessions/{session_id}/run",
            data={"stage": "INTERIM"},
        )
        run_resp.raise_for_status()
        result = run_resp.json()
        print(f"Findings: {result['findings_count']}")
        print(f"Anomalies: {result['anomalies_count']}")
        print(f"Consolidated: {result.get('consolidated_count', 0)}")
        print(f"Outputs: {result['output_paths']}")
        print(f"Tasks planned: {len(result.get('audit_tasks', []))}")
        if not result.get("output_paths"):
            raise RuntimeError("No output paths returned from pipeline")
        if not result["output_paths"].get("memo"):
            raise RuntimeError("Missing memo output path")
        if not result["output_paths"].get("risk_register"):
            raise RuntimeError("Missing risk register output path")

        issue_log_resp = await client.get(
            f"{BASE_URL}/sessions/{session_id}/download/issue_log"
        )
        issue_log_resp.raise_for_status()
        Path("test_output_issue_log.xlsx").write_bytes(issue_log_resp.content)
        print("Issue log downloaded")

        risk_resp = await client.get(
            f"{BASE_URL}/sessions/{session_id}/download/risk_register"
        )
        risk_resp.raise_for_status()
        Path("test_output_risk_register.xlsx").write_bytes(risk_resp.content)
        print("Risk register downloaded")

        memo_resp = await client.get(
            f"{BASE_URL}/sessions/{session_id}/download/memo"
        )
        memo_resp.raise_for_status()
        Path("test_output_memo.docx").write_bytes(memo_resp.content)
        print("Memo downloaded")


if __name__ == "__main__":
    asyncio.run(test_full_flow())
