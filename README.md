# AVE Audit Control Hub

A professional GitHub-ready release of the AVE audit support platform.
This repository includes the backend, frontend, curated sample evidence, and customer-ready documentation for real audit testing.

## Table of contents
- [Overview](#overview)
- [Included in this repository](#included-in-this-repository)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Run the backend](#run-the-backend)
- [Run the frontend](#run-the-frontend)
- [Testing](#testing)
- [Audit workflow](#audit-workflow)
- [Sample evidence included](#sample-evidence-included)
- [Customer test cases](#customer-test-cases)
- [API summary](#api-summary)
- [Repository hygiene](#repository-hygiene)
- [Publish checklist](#publish-checklist)

## Overview
AVE_1.2 is a complete AI audit assistant that supports evidence intake, multi-stage audit workflow, extraction, risk analysis, and report generation.
This release is curated for GitHub distribution: no sensitive environment files, no generator scripts, no build artifacts, and ready-to-use sample evidence.

## Included in this repository
- `api/` — FastAPI routes and session orchestration.
- `services/` — extractor, normalizer, file handler, output generator.
- `db/` — SQLite models and persistence.
- `frontend/` — React + Vite audit dashboard.
- `sample_audit_documents/` — curated sample audit evidence for customer testing.
- `test_data/` — representative regression test files.
- `docs/` — design, requirements, and release guidance.
- `sample_audit_documents/README.md` — how to use the sample evidence.
- `test_data/README.md` — how to use the regression test data.

## Requirements
- Python 3.11+
- Node.js 18+ and npm
- Optional: Tesseract OCR for scanned images
- Optional: `pypff` for PST handling

## Quick start
1. Create a virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Copy the example environment file and update it:
```bash
copy .env.example .env
```

Required values:
- `LLM_PROVIDER=groq|mistral|ollama`
- `GROQ_API_KEY` when using `groq`
- `MISTRAL_API_KEY` when using `mistral`

Recommended values:
- `OLLAMA_URL` for local LLM fallback
- `MAX_FILE_SIZE_MB` to limit upload sizes
- `UPLOAD_DIR`, `OUTPUT_DIR` for local storage paths

## Run the backend
```bash
uvicorn main:app --reload --port 8000
```

Verify the backend is healthy:
```bash
curl http://localhost:8000/api/v1/ping
```

## Run the frontend
```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`.

## Testing
Backend tests:
```bash
pytest tests/ -v --tb=short
```

Frontend checks:
```bash
cd frontend
npm run lint
npm run build
```

## Audit workflow
1. Start the backend and frontend.
2. In the UI, create a new audit session.
3. Upload evidence files from `sample_audit_documents/INTERIM` and `sample_audit_documents/FIELDWORK`.
4. Select stage `INTERIM`, `FIELDWORK`, or `BOTH`.
5. Run the audit pipeline.
6. Review findings, anomalies, and download generated reports.

## Sample evidence included
This repository includes a ready-to-use sample dataset:
- `sample_audit_documents/INTERIM/` — interim audit evidence and control documentation.
- `sample_audit_documents/FIELDWORK/` — fieldwork evidence, reconciliations, and supporting files.
- `sample_audit_documents/edge_cases/` — corrupted and malformed files for robustness testing.
- `test_data/` — compact sample files for regression validation.

## Customer test cases
The included samples support:
- Full audit run with real-case style evidence.
- Interim + fieldwork cross-stage validation.
- Error handling for malformed or missing files.
- Size-limit and unsupported file validation.
- Downloadable issue log, risk register, audit memo, evidence PDF, and versioned notes.

## API summary
Base URL: `http://localhost:8000/api/v1`

```
POST   /sessions
POST   /sessions/{session_id}/upload
POST   /sessions/{session_id}/run  (form: stage)
GET    /sessions/{session_id}/findings
GET    /sessions/{session_id}/execution-plan
GET    /sessions/{session_id}/consolidated-findings
GET    /findings/{id}/evidence-links
GET    /sessions/{session_id}/download/{type}
POST   /findings/{id}/feedback  (form: action, comment, corrected_value)
GET    /accuracy-metrics
GET    /knowledge-base
```

## Repository hygiene
This GitHub release intentionally excludes:
- `generate_*` scripts
- `Stitch_Prompt.md`
- Local environment files: `.env`, `.env.*`, `frontend/.env.local`
- Build artifacts: `.venv/`, `node_modules/`, `frontend/dist/`, `frontend/.vite/`
- Runtime outputs: `outputs/`, `uploads/`
- Logs and temporary files: `*.log`, `*.db`, `*.sqlite`, `*.pyc`

## Publish checklist
- Confirm `README.md` renders correctly.
- Confirm `sample_audit_documents/` contains realistic sample evidence.
- Confirm `test_data/` contains representative regression files.
- Confirm `.gitignore` blocks local artifacts and generator scripts.
- Confirm no draft prompt or generator file is tracked.
