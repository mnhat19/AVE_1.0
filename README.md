# AVE Audit Control Hub

AVE_1.2 is a ready-to-use AI audit support platform for evidence intake, document extraction, risk analysis, and deliverable generation.
It combines a FastAPI backend, a React + Vite frontend, realistic sample data generation, and an extensible audit workflow that can support almost any document collection.

## Why this repository is GitHub-ready
- Includes complete backend and frontend source code.
- Contains detailed documentation and sample audit datasets.
- Excludes local development artifacts and generated outputs using `.gitignore`.
- Designed for reuse with any audit evidence collection and document type.

## What is included
- `api/` — FastAPI route definitions and session orchestration.
- `services/` — document extractor, normalizer, file handler, output generator.
- `db/` — SQLite models and persistence glue.
- `frontend/` — React + Vite audit dashboard UI.
- `sample_audit_documents/` — realistic interim and fieldwork document examples.
- `generate_real_documents_complete.py` — sample dataset generation.
- `test_pipeline.py` — end-to-end CLI regression test.
- `docs/` — product requirements, test scenarios, and release note guidance.

## Requirements
- Python 3.11+
- Node.js 18+ and npm
- Optional: Tesseract OCR for scanned images
- Optional: `pypff` for PST parsing if you use `.pst` evidence files

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration
Copy the environment template and set your provider keys:
```bash
copy .env.example .env
```

Required environment variables:
- `LLM_PROVIDER=groq|mistral|ollama`
- `GROQ_API_KEY` when using `groq`
- `MISTRAL_API_KEY` when using `mistral`

Recommended optional settings:
- `OLLAMA_URL` for local LLM fallback
- `MAX_FILE_SIZE_MB` to limit upload payloads
- `UPLOAD_DIR`, `OUTPUT_DIR` for local storage

## Run the backend
```bash
uvicorn main:app --reload --port 8000
```

Verify the backend:
```bash
curl http://localhost:8000/api/v1/ping
```

## Run the frontend
Open a new terminal and run:
```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`.

## Full workflow
1. Start backend and frontend.
2. In the UI, create a new session.
3. Upload document files from `sample_audit_documents/INTERIM` and `sample_audit_documents/FIELDWORK`.
4. Choose stage `INTERIM`, `FIELDWORK`, or `BOTH`.
5. Run the audit pipeline.
6. Review findings and download generated reports.

## Generate realistic sample documents
Use the sample generator to build a full dataset:
```bash
python generate_real_documents_complete.py
```

## Supported audit evidence formats
- PDF, DOCX, TXT, CSV, XLSX, EML, PNG, JPG
- Custom scanned images via OCR (if Tesseract is installed)

## CLI regression test
```bash
python test_pipeline.py
```

This test expects the API to be running and valid LLM credentials.

## API summary
Base URL: `http://localhost:8000/api/v1`

```
POST   /sessions
POST   /sessions/{session_id}/upload
POST   /sessions/{session_id}/run  (form: stage)
GET    /sessions/{session_id}/findings
GET    /sessions/{session_id}/download/{type}
POST   /findings/{id}/feedback  (form: action, comment)
```

## Clean GitHub-ready rules
The repository intentionally excludes:
- `.venv/`, `outputs/`, `uploads/`
- `.env`, `.env.*`, `frontend/.env.local`, `frontend/.env.*`
- `*.log`, `*.db`, `*.sqlite`, `*.pyc`
- `node_modules/`, `frontend/node_modules/`, `frontend/dist/`, `frontend/.vite/`

## Publish to GitHub
If this project is not yet initialized as a repository, run:
```bash
git init
git add .
git commit -m "Initial GitHub-ready release for AVE Audit Control Hub"
```
Then create a repository on GitHub and add the remote:
```bash
git remote add origin https://github.com/<username>/<repository>.git
git branch -M main
git push -u origin main
```

## Notes
- Use `sample_audit_documents/edge_cases/` to validate error handling.
- Generated outputs are stored under `OUTPUT_DIR` and are not tracked.
- The project is designed for flexible audit support and can be adapted to new evidence types.
