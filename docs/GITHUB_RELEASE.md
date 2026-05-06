# GitHub Release Guide

This document explains how the AVE Audit Control Hub repository is prepared for open-source publishing on GitHub.

## Included in the repository
- Source code for backend and frontend
- Configuration templates and environment examples
- Sample audit documents for interim and fieldwork testing
- Product documentation in `docs/`
- End-to-end test script and sample data generation script

## Excluded from GitHub
The following items should not be committed or published:
- Local Python virtual environment: `.venv/`
- Runtime output directories: `outputs/`, `uploads/`
- Environment secrets: `.env`, `.env.*`, `frontend/.env.local`, `frontend/.env.*`
- Local database and generated storage: `*.db`, `*.sqlite`, `*.sqlite3`
- Logs and temporary files: `*.log`, `*.pyc`, `__pycache__/`
- Node build artifacts: `frontend/node_modules/`, `frontend/dist/`, `frontend/.vite/`

## What to keep
- `api/`, `services/`, `db/`, `config/`, `schemas/`
- `frontend/src/`, `frontend/package.json`, `frontend/vite.config.ts`
- `sample_audit_documents/` for demo and onboarding purposes
- `generate_real_documents_complete.py` and related generators
- `test_pipeline.py`, `test_data/`, and documentation files

## Recommended GitHub publish workflow
1. Initialize repository locally (if not already):
```bash
git init
```
2. Add files and commit:
```bash
git add .
git commit -m "Prepare AVE Audit Control Hub for GitHub release"
```
3. Create a GitHub repository and add remote:
```bash
git remote add origin https://github.com/<username>/<repository>.git
```
4. Push main branch:
```bash
git branch -M main
git push -u origin main
```

## Post-publish checklist
- Verify `README.md` renders correctly on GitHub.
- Confirm `.gitignore` is active and local artifacts are not tracked.
- Ensure `sample_audit_documents/` contains only representative samples, not temporary exports.
- Validate that the repository does not include `.env` or any secrets.

## Notes
- The repo is structured as a reusable audit assistant that can accept new document sets.
- The UI and backend are decoupled so the frontend can run with a live backend or mock data during development.
- If you need to add more sample documents, append them under `sample_audit_documents/` and keep generated outputs outside version control.
