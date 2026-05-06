from pathlib import Path
import httpx

BASE_URL = "http://localhost:8000/api/v1"
ROOT = Path("sample_audit_documents")

files = []
for stage in ["INTERIM", "FIELDWORK"]:
    for path in sorted((ROOT / stage).glob("*")):
        if path.is_file():
            files.append((stage, path))

print("Uploading", len(files), "files")
with httpx.Client(timeout=httpx.Timeout(600.0, connect=60.0, read=600.0, write=600.0)) as client:
    r = client.post(f"{BASE_URL}/sessions")
    r.raise_for_status()
    session_id = r.json()["session_id"]
    print("session", session_id)
    multipart = [
        ("files", (path.name, path.read_bytes(), "application/octet-stream"))
        for _, path in files
    ]
    upload = client.post(f"{BASE_URL}/sessions/{session_id}/upload", files=multipart)
    print("upload status", upload.status_code)
    print(upload.json())
    print("Starting full audit run; this may take several minutes...")
    run = client.post(f"{BASE_URL}/sessions/{session_id}/run", data={"stage": "BOTH"})
    print("run status", run.status_code)
    print(run.json())
