# MVP_TODO.md — AI Audit Agent Tool

> **Mục tiêu MVP**: Một công cụ CLI/API chạy được end-to-end luồng kiểm toán thực:
> Upload files → Phân loại → Trích xuất → Chạy logic kiểm toán → Sinh issue log + memo
>
> **Triết lý**: Backend-first, code được ngay, không over-engineer. LLM xử lý reasoning, rule-based xử lý số.

---

## Tech Stack Tối Ưu

```
Backend:       Python 3.11+
Agent Graph:   LangGraph (orchestration state machine)
API Server:    FastAPI + Uvicorn
File Parse:    pdfplumber, python-docx, openpyxl, pandas, pytesseract
LLM APIs:      Groq (primary — miễn phí, nhanh) / Mistral (fallback)
Local LLM:     Ollama (offline/internal)
DB:            SQLite (MVP) → PostgreSQL (production)
Output Gen:    openpyxl (Excel), python-docx (Word), reportlab (PDF)
Queue:         asyncio + background tasks (FastAPI) — không cần Celery ở MVP
Config:        python-dotenv + pydantic-settings
```

### Lý do chọn Groq làm primary
- Free tier: 30 req/min, đủ cho MVP
- Llama-3.3-70b-versatile: tốt cho reasoning + extraction
- Latency ~200ms — nhanh nhất trong các free provider

### Model Mapping theo Task

| Task | Groq Model | Ollama Fallback | Lý do |
|---|---|---|---|
| Document parsing / extraction | `llama-3.1-8b-instant` | `llama3.1:8b` | Nhanh, đủ cho structured extraction |
| Audit reasoning / risk analysis | `llama-3.3-70b-versatile` | `llama3.1:70b` hoặc `mistral` | Cần deep reasoning |
| Anomaly detection prompt | `llama-3.1-8b-instant` | `llama3.1:8b` | Pattern matching đơn giản |
| Memo / narrative generation | `llama-3.3-70b-versatile` | `mistral:7b` | Cần output chất lượng văn bản |

---

## Cài đặt Ollama (Local Fallback)

```bash
# Cài Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.1:8b        # extraction tasks
ollama pull llama3.3:70b       # reasoning (cần GPU ≥24GB) — hoặc dùng mistral nếu không đủ VRAM
ollama pull mistral             # memo generation fallback

# Start server (mặc định port 11434)
ollama serve
```

### Cấu hình LLM trong code

```python
# config/llm.py
import os
from groq import Groq
import httpx

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # "groq" | "mistral" | "ollama"

def get_llm_client(task_type: str = "reasoning"):
    """
    task_type: "extraction" | "reasoning" | "generation"
    Returns callable: async def call(prompt: str) -> str
    """
    if LLM_PROVIDER == "groq":
        model_map = {
            "extraction": "llama-3.1-8b-instant",
            "reasoning":  "llama-3.3-70b-versatile",
            "generation": "llama-3.3-70b-versatile",
        }
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        model = model_map.get(task_type, "llama-3.1-8b-instant")

        async def call(prompt: str, system: str = "") -> str:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system or "You are an expert auditor."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048
            )
            return resp.choices[0].message.content

        return call

    elif LLM_PROVIDER == "ollama":
        model_map = {
            "extraction": "llama3.1:8b",
            "reasoning":  "mistral",
            "generation": "mistral",
        }
        model = model_map.get(task_type, "llama3.1:8b")
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

        async def call(prompt: str, system: str = "") -> str:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{ollama_url}/api/generate", json={
                    "model": model,
                    "prompt": f"{system}\n\n{prompt}" if system else prompt,
                    "stream": False
                })
                return resp.json()["response"]

        return call

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
```

---

## Phase 0 — Foundation (ngày 1)

### 0.1 Khởi tạo project

```
audit-tool/
├── main.py                  # FastAPI app entry
├── config/
│   ├── settings.py          # pydantic-settings config
│   └── llm.py               # LLM client factory (code trên)
├── db/
│   ├── database.py          # SQLite init + session
│   └── models.py            # SQLAlchemy ORM models
├── agents/
│   ├── orchestrator.py      # LangGraph state machine
│   ├── doc_agent.py         # Extraction logic
│   ├── data_agent.py        # Tabular analysis
│   └── audit_agent.py       # Audit rules + LLM reasoning
├── services/
│   ├── file_handler.py      # Upload + classify
│   ├── extractor.py         # Per-format extractors
│   ├── normalizer.py        # Schema mapping
│   └── output_generator.py  # Excel/Word/PDF output
├── api/
│   └── routes.py            # FastAPI endpoints
├── schemas/                 # Pydantic models (request/response)
├── prompts/                 # Prompt templates (.txt hoặc .py)
├── uploads/                 # Temp file storage
├── outputs/                 # Generated output files
├── .env.example
└── requirements.txt
```

**requirements.txt:**
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-dotenv==1.0.0
pydantic-settings==2.3.0
sqlalchemy==2.0.30
langgraph==0.2.0
langchain-core==0.3.0
groq==0.11.0
httpx==0.27.0
pdfplumber==0.11.0
python-docx==1.1.2
openpyxl==3.1.5
pandas==2.2.2
pytesseract==0.3.13
Pillow==10.4.0
extract-msg==0.49.0        # EML parsing
reportlab==4.2.2
python-multipart==0.0.9    # FastAPI file upload
aiofiles==23.2.1
```

### 0.2 Database Schema (SQLite MVP)

**Tạo file `db/models.py`** — implement đúng các entities trong PRD:

```python
# db/models.py
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, Enum, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum, uuid
from datetime import datetime

Base = declarative_base()

def gen_id(): return str(uuid.uuid4())[:8]

class StageEnum(str, enum.Enum):
    INTERIM = "INTERIM"
    FIELDWORK = "FIELDWORK"

class FormatEnum(str, enum.Enum):
    PDF = "PDF"; DOCX = "DOCX"; XLSX = "XLSX"
    CSV = "CSV"; TXT = "TXT"; IMAGE = "IMAGE"; EML = "EML"

class DocumentBundle(Base):
    __tablename__ = "document_bundles"
    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, nullable=False)
    stage = Column(String)  # INTERIM | FIELDWORK | BOTH
    created_at = Column(DateTime, default=datetime.utcnow)
    files = relationship("FileRecord", back_populates="bundle")

class FileRecord(Base):
    __tablename__ = "file_records"
    id = Column(String, primary_key=True, default=gen_id)
    bundle_id = Column(String, ForeignKey("document_bundles.id"))
    filename = Column(String)
    format = Column(String)
    stage = Column(String)
    validation_status = Column(String, default="PENDING")  # PENDING|VALID|INVALID
    file_path = Column(String)
    bundle = relationship("DocumentBundle", back_populates="files")

class AuditFinding(Base):
    __tablename__ = "audit_findings"
    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String)
    stage = Column(String)
    description = Column(String)
    root_cause = Column(String)
    expected_impact = Column(String)
    severity = Column(String, default="MEDIUM")  # LOW|MEDIUM|HIGH|CRITICAL
    assignee = Column(String)
    status = Column(String, default="OPEN")
    confidence_score = Column(Float, default=0.0)
    source_file_id = Column(String)
    source_reference = Column(String)  # sheet name, page, row
    created_at = Column(DateTime, default=datetime.utcnow)

class RiskEntry(Base):
    __tablename__ = "risk_entries"
    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String)
    description = Column(String)
    probability = Column(Float, default=0.5)
    impact = Column(Float, default=0.5)
    risk_score = Column(Float)  # probability * impact * 10
    owner = Column(String)
    related_controls = Column(JSON)  # list of control descriptions

class VersionedNote(Base):
    __tablename__ = "versioned_notes"
    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    author = Column(String, default="SYSTEM")
    change_description = Column(String)

class AuditorFeedback(Base):
    __tablename__ = "auditor_feedback"
    id = Column(String, primary_key=True, default=gen_id)
    finding_id = Column(String, ForeignKey("audit_findings.id"))
    action = Column(String)  # ACCEPT|REJECT|MODIFY
    comment = Column(String)
    corrected_value = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**`db/database.py`:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./audit_mvp.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## Phase 1 — File Ingestion & Classification (ngày 1–2)

### Task 1.1: File Upload + Classification Service

**Input:** File binary (multipart upload)
**Xử lý:** Detect format → classify stage → validate
**Output:** `FileRecord` saved to DB, `DocumentBundle` created/updated

```python
# services/file_handler.py
import os, shutil, mimetypes
from pathlib import Path
from db.models import FileRecord, DocumentBundle
from db.database import SessionLocal

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

FORMAT_MAP = {
    ".pdf": "PDF", ".docx": "DOCX", ".doc": "DOCX",
    ".xlsx": "XLSX", ".xls": "XLSX", ".csv": "CSV",
    ".txt": "TXT", ".eml": "EML", ".pst": "EML",
    ".jpg": "IMAGE", ".jpeg": "IMAGE", ".png": "IMAGE", ".tiff": "IMAGE"
}

# Heuristic stage classification từ tên file
INTERIM_KEYWORDS = ["sox", "walkthrough", "control", "interim", "risk_matrix", "sop", "policy", "tobc"]
FIELDWORK_KEYWORDS = ["trial_balance", "lead_schedule", "ageing", "reconciliation", "roll_forward",
                       "confirmation", "inventory", "fieldwork", "journal", "ledger"]

def classify_stage(filename: str) -> str:
    name = filename.lower()
    is_interim = any(kw in name for kw in INTERIM_KEYWORDS)
    is_field = any(kw in name for kw in FIELDWORK_KEYWORDS)
    if is_interim and not is_field: return "INTERIM"
    if is_field and not is_interim: return "FIELDWORK"
    return "BOTH"  # ambiguous → xử lý cả hai giai đoạn

async def save_and_classify(file, session_id: str, bundle_id: str = None) -> FileRecord:
    ext = Path(file.filename).suffix.lower()
    fmt = FORMAT_MAP.get(ext, "TXT")
    stage = classify_stage(file.filename)

    dest = UPLOAD_DIR / session_id
    dest.mkdir(parents=True, exist_ok=True)
    file_path = dest / file.filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    db = SessionLocal()
    try:
        if not bundle_id:
            bundle = DocumentBundle(session_id=session_id, stage=stage)
            db.add(bundle)
            db.flush()
            bundle_id = bundle.id
        
        record = FileRecord(
            bundle_id=bundle_id,
            filename=file.filename,
            format=fmt,
            stage=stage,
            validation_status="VALID",
            file_path=str(file_path)
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()
```

### Task 1.2: API Endpoint — Upload

```python
# api/routes.py (phần upload)
from fastapi import APIRouter, UploadFile, File, Form
from services.file_handler import save_and_classify
import uuid

router = APIRouter()

@router.post("/sessions/{session_id}/upload")
async def upload_files(
    session_id: str,
    files: list[UploadFile] = File(...),
    bundle_id: str = Form(None)
):
    """
    Upload 1 hoặc nhiều files vào một session kiểm toán.
    Trả về danh sách FileRecord đã phân loại.
    """
    results = []
    for f in files:
        record = await save_and_classify(f, session_id, bundle_id)
        results.append({
            "file_id": record.id,
            "filename": record.filename,
            "format": record.format,
            "stage": record.stage,
            "status": record.validation_status
        })
    return {"session_id": session_id, "files": results}
```

---

## Phase 2 — Extraction & Normalization Pipeline (ngày 2–3)

### Task 2.1: Per-format Extractors

**Đầu vào:** `file_path`, `format`
**Đầu ra:** `dict` có dạng `{"type": "text"|"table", "content": ..., "metadata": ...}`

```python
# services/extractor.py
import pdfplumber, pandas as pd
from docx import Document
from pathlib import Path
import pytesseract
from PIL import Image
import extract_msg

def extract_pdf(path: str) -> dict:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
            # Extract tables nếu có
    return {"type": "text", "content": "\n".join(text_parts), "pages": len(pdf.pages)}

def extract_docx(path: str) -> dict:
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    tables = []
    for table in doc.tables:
        rows = [[cell.text for cell in row.cells] for row in table.rows]
        tables.append(rows)
    return {"type": "text", "content": "\n".join(paragraphs), "tables": tables}

def extract_excel(path: str) -> dict:
    xl = pd.ExcelFile(path)
    sheets = {}
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        sheets[sheet] = df.to_dict(orient="records")
    return {"type": "table", "content": sheets, "sheet_names": xl.sheet_names}

def extract_csv(path: str) -> dict:
    df = pd.read_csv(path, encoding="utf-8-sig")
    return {"type": "table", "content": df.to_dict(orient="records"), "columns": list(df.columns)}

def extract_image(path: str) -> dict:
    img = Image.open(path)
    text = pytesseract.image_to_string(img, lang="vie+eng")
    return {"type": "text", "content": text}

def extract_eml(path: str) -> dict:
    msg = extract_msg.Message(path)
    return {
        "type": "text",
        "content": msg.body or "",
        "metadata": {"sender": msg.sender, "date": str(msg.date), "subject": msg.subject}
    }

EXTRACTORS = {
    "PDF": extract_pdf, "DOCX": extract_docx, "XLSX": extract_excel,
    "CSV": extract_csv, "TXT": lambda p: {"type": "text", "content": open(p).read()},
    "IMAGE": extract_image, "EML": extract_eml
}

def extract(file_record) -> dict:
    fn = EXTRACTORS.get(file_record.format)
    if not fn:
        return {"type": "text", "content": "", "error": "unsupported format"}
    return fn(file_record.file_path)
```

### Task 2.2: LLM-powered Schema Normalization (Doc Agent)

**Đầu vào:** Extracted raw content (text)
**Xử lý:** LLM phân tích content → identify document type → extract structured fields
**Đầu ra:** `{"doc_type": ..., "key_fields": {...}, "process_description": ...}`

```python
# agents/doc_agent.py
from config.llm import get_llm_client
import json

CLASSIFY_PROMPT = """You are an audit document classifier. Analyze the document excerpt below and return JSON only.

Document content:
{content}

Return this JSON structure:
{{
  "doc_type": "<one of: PROCESS_DESC | SOP | RISK_MATRIX | WALKTHROUGH | TRIAL_BALANCE | JOURNAL | LEAD_SCHEDULE | AGEING | RECONCILIATION | CONFIRMATION | CONTRACT | BANK_STATEMENT | INVENTORY | EMAIL | OTHER>",
  "audit_stage": "<INTERIM | FIELDWORK | BOTH>",
  "key_entities": ["list of key account names, amounts, dates mentioned"],
  "summary": "<2-3 sentence summary of what this document contains>",
  "internal_controls_mentioned": ["list any internal controls or SOPs described"],
  "confidence": <0.0 to 1.0>
}}
Return ONLY valid JSON, no markdown, no explanation."""

EXTRACT_PROCESS_PROMPT = """You are an audit assistant. Extract internal control information from this document.

Content:
{content}

Return JSON:
{{
  "process_name": "<name of the business process>",
  "control_objectives": ["list of control objectives"],
  "key_controls": [
    {{"control_id": "C-001", "description": "<control description>", "type": "<PREVENTIVE|DETECTIVE|CORRECTIVE>", "frequency": "<DAILY|MONTHLY|ANNUAL|AD_HOC>"}}
  ],
  "risk_indicators": ["list of risks mentioned"]
}}"""

async def classify_document(content: str) -> dict:
    llm = get_llm_client("extraction")
    truncated = content[:3000]  # Giới hạn để tránh token overflow
    prompt = CLASSIFY_PROMPT.format(content=truncated)
    raw = await llm(prompt)
    try:
        return json.loads(raw.strip())
    except:
        return {"doc_type": "OTHER", "confidence": 0.0, "error": "parse_failed", "raw": raw}

async def extract_process_info(content: str) -> dict:
    llm = get_llm_client("extraction")
    raw = await llm(EXTRACT_PROCESS_PROMPT.format(content=content[:4000]))
    try:
        return json.loads(raw.strip())
    except:
        return {"process_name": "Unknown", "key_controls": [], "risk_indicators": []}
```

### Task 2.3: Tabular Data Normalization (Data Agent)

**Đầu vào:** Excel/CSV content (dict of rows)
**Xử lý:** LLM + rule-based nhận diện schema → map columns
**Đầu ra:** `NormalizedTable` với schema rõ ràng

```python
# agents/data_agent.py
from config.llm import get_llm_client
import pandas as pd, json

SCHEMA_DETECT_PROMPT = """You are an accounting data analyst. Examine these column headers and sample rows.

Columns: {columns}
Sample rows (first 3): {sample}

Identify the schema type and column mapping. Return JSON:
{{
  "schema_type": "<TRIAL_BALANCE | JOURNAL | LEAD_SCHEDULE | AGEING | RECONCILIATION | TRANSACTION_LOG | OTHER>",
  "column_mapping": {{
    "account_code": "<column name or null>",
    "account_name": "<column name or null>",
    "debit": "<column name or null>",
    "credit": "<column name or null>",
    "balance": "<column name or null>",
    "date": "<column name or null>",
    "description": "<column name or null>",
    "amount": "<column name or null>",
    "reference": "<column name or null>"
  }},
  "currency_detected": "<VND | USD | EUR | unknown>",
  "period_detected": "<detected accounting period or null>"
}}"""

async def detect_table_schema(columns: list, sample_rows: list) -> dict:
    llm = get_llm_client("extraction")
    prompt = SCHEMA_DETECT_PROMPT.format(
        columns=columns[:20],
        sample=json.dumps(sample_rows[:3], ensure_ascii=False, default=str)
    )
    raw = await llm(prompt)
    try:
        return json.loads(raw.strip())
    except:
        return {"schema_type": "OTHER", "column_mapping": {}}

def normalize_table(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """
    Rename columns theo column_mapping để tạo chuẩn hóa.
    Giữ nguyên dữ liệu gốc, chỉ thêm cột chuẩn hóa.
    """
    mapping = schema.get("column_mapping", {})
    reverse_map = {v: k for k, v in mapping.items() if v}
    df_norm = df.rename(columns=reverse_map)
    # Chuẩn hóa số: remove commas, convert to float
    for col in ["debit", "credit", "balance", "amount"]:
        if col in df_norm.columns:
            df_norm[col] = pd.to_numeric(
                df_norm[col].astype(str).str.replace(",", "").str.replace("(", "-").str.replace(")", ""),
                errors="coerce"
            )
    return df_norm
```

---

## Phase 3 — Core Audit Logic (ngày 3–5)

### Task 3.1: Anomaly Detection Rules (Data Agent — rule-based)

**Đầu vào:** `NormalizedTable` dạng `JOURNAL` hoặc `TRIAL_BALANCE`
**Xử lý:** Statistical rules → flag anomalies
**Đầu ra:** List `AnomalyFlag`

```python
# agents/audit_agent.py (phần anomaly detection)
import pandas as pd
import numpy as np
from typing import List, Dict

def detect_journal_anomalies(df: pd.DataFrame) -> List[Dict]:
    """
    Rule-based anomaly detection trên journal entries.
    PRD yêu cầu: gắn cờ rủi ro trong dữ liệu kế toán/ERP (Bước 4.2 #3)
    """
    flags = []

    # Rule 1: Round numbers (multiples of 1M VND / 1000 USD)
    if "amount" in df.columns:
        round_amounts = df[df["amount"] % 1_000_000 == 0]
        if not round_amounts.empty:
            flags.append({
                "rule": "ROUND_AMOUNT",
                "severity": "LOW",
                "count": len(round_amounts),
                "description": f"{len(round_amounts)} journal entries with round amounts (multiples of 1M)",
                "rows": round_amounts.index.tolist()[:10]
            })

    # Rule 2: Weekend entries
    if "date" in df.columns:
        df["_date"] = pd.to_datetime(df["date"], errors="coerce")
        weekend = df[df["_date"].dt.dayofweek >= 5]
        if not weekend.empty:
            flags.append({
                "rule": "WEEKEND_ENTRY",
                "severity": "MEDIUM",
                "count": len(weekend),
                "description": f"{len(weekend)} journal entries posted on weekends",
                "rows": weekend.index.tolist()[:10]
            })

    # Rule 3: Large amount outliers (>3 standard deviations)
    if "amount" in df.columns and len(df) > 10:
        mean, std = df["amount"].mean(), df["amount"].std()
        outliers = df[abs(df["amount"] - mean) > 3 * std]
        if not outliers.empty:
            flags.append({
                "rule": "LARGE_AMOUNT_OUTLIER",
                "severity": "HIGH",
                "count": len(outliers),
                "description": f"{len(outliers)} entries with amounts >3σ from mean ({mean:,.0f})",
                "rows": outliers.index.tolist()[:10]
            })

    # Rule 4: Unbalanced journals (debit ≠ credit)
    if "debit" in df.columns and "credit" in df.columns:
        df_ref = df.groupby("reference")[["debit", "credit"]].sum() if "reference" in df.columns else None
        if df_ref is not None:
            unbalanced = df_ref[abs(df_ref["debit"] - df_ref["credit"]) > 1]  # tolerance 1 unit
            if not unbalanced.empty:
                flags.append({
                    "rule": "UNBALANCED_JOURNAL",
                    "severity": "CRITICAL",
                    "count": len(unbalanced),
                    "description": f"{len(unbalanced)} journal references where debit ≠ credit",
                    "rows": unbalanced.index.tolist()[:10]
                })

    return flags


def detect_trial_balance_anomalies(df: pd.DataFrame) -> List[Dict]:
    """Kiểm tra trial balance: tổng debit = tổng credit, check negative balances."""
    flags = []

    if "debit" in df.columns and "credit" in df.columns:
        total_debit = df["debit"].sum()
        total_credit = df["credit"].sum()
        diff = abs(total_debit - total_credit)
        if diff > 1:
            flags.append({
                "rule": "TB_OUT_OF_BALANCE",
                "severity": "CRITICAL",
                "count": 1,
                "description": f"Trial balance out of balance by {diff:,.2f}",
                "rows": []
            })

    if "balance" in df.columns:
        neg_asset = df[(df.get("account_code", "").astype(str).str.startswith("1")) & (df["balance"] < 0)]
        if not neg_asset.empty:
            flags.append({
                "rule": "NEGATIVE_ASSET_BALANCE",
                "severity": "HIGH",
                "count": len(neg_asset),
                "description": f"{len(neg_asset)} asset accounts with negative balances",
                "rows": neg_asset.index.tolist()[:10]
            })

    return flags
```

### Task 3.2: LLM Audit Reasoning (Audit Agent)

**Đầu vào:** Anomaly flags + Document summaries + (optional) Risk matrix text
**Xử lý:** LLM phân tích context → generate findings
**Đầu ra:** List `AuditFinding` candidates

```python
# agents/audit_agent.py (phần LLM reasoning)

AUDIT_REASONING_PROMPT = """You are a senior auditor performing {stage} audit procedures.

CONTEXT:
- Audit Stage: {stage}
- Documents analyzed: {doc_summaries}
- Anomalies detected by automated rules: {anomaly_flags}
- Internal controls identified: {controls_identified}

Based on the above, identify audit findings. For each finding provide:
1. Clear description of the issue
2. Root cause analysis
3. Potential impact on financial statements
4. Severity (LOW/MEDIUM/HIGH/CRITICAL)
5. Confidence score (0.0-1.0) based on evidence strength

Return JSON array:
[
  {{
    "description": "<specific finding description>",
    "root_cause": "<identified root cause>",
    "expected_impact": "<impact on financial statements>",
    "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "confidence_score": <0.0-1.0>,
    "related_anomaly_rules": ["list of anomaly rules that triggered this finding"],
    "recommended_action": "<next audit step recommended>"
  }}
]

Return ONLY valid JSON array. Be specific and actionable, not generic."""

async def generate_audit_findings(
    stage: str,
    doc_summaries: list,
    anomaly_flags: list,
    controls_identified: list
) -> list:
    llm = get_llm_client("reasoning")
    prompt = AUDIT_REASONING_PROMPT.format(
        stage=stage,
        doc_summaries=json.dumps(doc_summaries[:5], ensure_ascii=False),
        anomaly_flags=json.dumps(anomaly_flags, ensure_ascii=False),
        controls_identified=json.dumps(controls_identified[:10], ensure_ascii=False)
    )
    raw = await llm(prompt)
    try:
        findings = json.loads(raw.strip())
        return findings if isinstance(findings, list) else []
    except:
        # Fallback: parse partial
        return []
```

### Task 3.3: Risk Matrix Builder

**Đầu vào:** List of findings + controls
**Xử lý:** Map risk → control → severity
**Đầu ra:** `RiskEntry[]` saved to DB

```python
# agents/audit_agent.py (risk matrix)

RISK_SCORE_MAP = {"LOW": 2, "MEDIUM": 5, "HIGH": 8, "CRITICAL": 10}

def build_risk_register(findings: list, session_id: str) -> list:
    """
    Chuyển đổi findings thành RiskEntry records.
    risk_score = probability * impact * 10 (đơn giản hóa: dùng severity map)
    """
    risks = []
    for i, finding in enumerate(findings):
        severity = finding.get("severity", "MEDIUM")
        score = RISK_SCORE_MAP.get(severity, 5)
        risks.append({
            "id": f"RISK-{session_id[:4]}-{i+1:03d}",
            "session_id": session_id,
            "description": finding.get("description", ""),
            "probability": 0.7 if severity in ["HIGH", "CRITICAL"] else 0.4,
            "impact": score / 10,
            "risk_score": score,
            "owner": "Audit Team",
            "related_controls": finding.get("related_anomaly_rules", [])
        })
    return risks
```

---

## Phase 4 — Orchestrator (LangGraph State Machine) (ngày 4–5)

### Task 4.1: Define Graph State

```python
# agents/orchestrator.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Annotated
import operator

class AuditState(TypedDict):
    session_id: str
    stage: str                          # INTERIM | FIELDWORK | BOTH
    file_records: List[dict]
    extracted_docs: List[dict]          # output of doc_agent
    normalized_tables: List[dict]       # output of data_agent
    anomaly_flags: List[dict]           # output of rule-based checks
    audit_findings: List[dict]          # output of audit_agent LLM
    risk_entries: List[dict]
    versioned_notes: Annotated[List[str], operator.add]  # accumulate notes
    errors: List[str]
    output_paths: dict                  # {"issue_log": ..., "memo": ..., "risk_register": ...}
```

### Task 4.2: Define Nodes (rule-based agents, mock-safe)

```python
# agents/orchestrator.py (nodes)
from agents.doc_agent import classify_document, extract_process_info
from agents.data_agent import detect_table_schema, normalize_table
from agents.audit_agent import (detect_journal_anomalies, detect_trial_balance_anomalies,
                                 generate_audit_findings, build_risk_register)
from services.extractor import extract
from services.output_generator import generate_issue_log, generate_memo

async def node_extract_documents(state: AuditState) -> AuditState:
    """Doc Agent: extract + classify all files."""
    extracted = []
    for fr in state["file_records"]:
        raw = extract(fr)
        if raw.get("type") == "text" and raw.get("content"):
            classification = await classify_document(raw["content"])
            extracted.append({
                "file_id": fr["id"],
                "filename": fr["filename"],
                "format": fr["format"],
                "raw": raw,
                "classification": classification
            })
        else:
            extracted.append({"file_id": fr["id"], "filename": fr["filename"],
                               "format": fr["format"], "raw": raw, "classification": {}})
    return {**state, "extracted_docs": extracted,
            "versioned_notes": [f"Extracted {len(extracted)} documents"]}

async def node_normalize_tables(state: AuditState) -> AuditState:
    """Data Agent: normalize tabular data."""
    import pandas as pd
    normalized = []
    for doc in state["extracted_docs"]:
        if doc["raw"].get("type") == "table":
            for sheet_name, rows in doc["raw"]["content"].items():
                if not rows: continue
                df = pd.DataFrame(rows)
                schema = await detect_table_schema(list(df.columns), rows[:3])
                df_norm = normalize_table(df, schema)
                normalized.append({
                    "file_id": doc["file_id"],
                    "sheet_name": sheet_name,
                    "schema": schema,
                    "dataframe": df_norm,
                    "rows_count": len(df_norm)
                })
    return {**state, "normalized_tables": normalized,
            "versioned_notes": [f"Normalized {len(normalized)} tables"]}

async def node_detect_anomalies(state: AuditState) -> AuditState:
    """Rule-based anomaly detection."""
    all_flags = []
    for table in state["normalized_tables"]:
        df = table["dataframe"]
        schema_type = table["schema"].get("schema_type", "OTHER")
        if schema_type == "JOURNAL":
            flags = detect_journal_anomalies(df)
        elif schema_type == "TRIAL_BALANCE":
            flags = detect_trial_balance_anomalies(df)
        else:
            flags = []
        for f in flags:
            f["source_file_id"] = table["file_id"]
            f["source_sheet"] = table["sheet_name"]
        all_flags.extend(flags)
    return {**state, "anomaly_flags": all_flags,
            "versioned_notes": [f"Detected {len(all_flags)} anomaly flags"]}

async def node_audit_reasoning(state: AuditState) -> AuditState:
    """Audit Agent: LLM reasoning → findings."""
    doc_summaries = [
        {"filename": d["filename"], "summary": d["classification"].get("summary", "")}
        for d in state["extracted_docs"] if d.get("classification")
    ]
    controls = []
    for d in state["extracted_docs"]:
        c = d.get("classification", {}).get("internal_controls_mentioned", [])
        controls.extend(c)

    findings_raw = await generate_audit_findings(
        stage=state["stage"],
        doc_summaries=doc_summaries,
        anomaly_flags=state["anomaly_flags"],
        controls_identified=controls
    )
    risk_entries = build_risk_register(findings_raw, state["session_id"])
    return {**state, "audit_findings": findings_raw, "risk_entries": risk_entries,
            "versioned_notes": [f"Generated {len(findings_raw)} audit findings"]}

async def node_generate_outputs(state: AuditState) -> AuditState:
    """Generate Excel issue log + Word memo."""
    issue_log_path = await generate_issue_log(state)
    memo_path = await generate_memo(state)
    return {**state, "output_paths": {"issue_log": issue_log_path, "memo": memo_path},
            "versioned_notes": ["Output files generated"]}
```

### Task 4.3: Build & Compile the Graph

```python
# agents/orchestrator.py (graph assembly)

def build_audit_graph():
    graph = StateGraph(AuditState)

    graph.add_node("extract_documents", node_extract_documents)
    graph.add_node("normalize_tables", node_normalize_tables)
    graph.add_node("detect_anomalies", node_detect_anomalies)
    graph.add_node("audit_reasoning", node_audit_reasoning)
    graph.add_node("generate_outputs", node_generate_outputs)

    graph.set_entry_point("extract_documents")
    graph.add_edge("extract_documents", "normalize_tables")
    graph.add_edge("normalize_tables", "detect_anomalies")
    graph.add_edge("detect_anomalies", "audit_reasoning")
    graph.add_edge("audit_reasoning", "generate_outputs")
    graph.add_edge("generate_outputs", END)

    return graph.compile()

# Singleton
AUDIT_GRAPH = build_audit_graph()

async def run_audit_pipeline(session_id: str, stage: str, file_records: list) -> dict:
    initial_state: AuditState = {
        "session_id": session_id,
        "stage": stage,
        "file_records": file_records,
        "extracted_docs": [],
        "normalized_tables": [],
        "anomaly_flags": [],
        "audit_findings": [],
        "risk_entries": [],
        "versioned_notes": [],
        "errors": [],
        "output_paths": {}
    }
    final_state = await AUDIT_GRAPH.ainvoke(initial_state)
    return final_state
```

---

## Phase 5 — Output Generation (ngày 5–6)

### Task 5.1: Excel Issue Log Generator

**Output format chuẩn** theo PRD (Section 4.3):
Mã phát hiện | Mô tả | Mức độ | Người phụ trách | Trạng thái xử lý | Confidence

```python
# services/output_generator.py
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from pathlib import Path
import uuid

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

SEVERITY_COLORS = {
    "CRITICAL": "FF0000", "HIGH": "FF6600",
    "MEDIUM": "FFCC00", "LOW": "99CC00"
}

async def generate_issue_log(state: dict) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Issue Log"

    # Header
    headers = ["Finding ID", "Stage", "Description", "Root Cause",
               "Expected Impact", "Severity", "Assignee", "Status", "Confidence Score", "Source"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E79")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    ws.row_dimensions[1].height = 30

    # Data rows
    session_id = state["session_id"]
    for i, finding in enumerate(state["audit_findings"], 1):
        row_num = i + 1
        finding_id = f"FND-{session_id[:4].upper()}-{i:03d}"
        severity = finding.get("severity", "MEDIUM")

        row_data = [
            finding_id,
            state["stage"],
            finding.get("description", ""),
            finding.get("root_cause", ""),
            finding.get("expected_impact", ""),
            severity,
            "Audit Team",
            "OPEN",
            f"{finding.get('confidence_score', 0.0):.0%}",
            ", ".join(finding.get("related_anomaly_rules", []))
        ]
        for col, val in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col, value=val)

        # Color severity cell
        sev_cell = ws.cell(row=row_num, column=6)
        sev_cell.fill = PatternFill("solid", fgColor=SEVERITY_COLORS.get(severity, "CCCCCC"))
        sev_cell.font = Font(bold=True)

    # Column widths
    col_widths = [15, 10, 60, 50, 50, 12, 15, 12, 15, 30]
    for col, w in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = w

    # Risk Register sheet
    ws2 = wb.create_sheet("Risk Register")
    risk_headers = ["Risk ID", "Description", "Probability", "Impact", "Risk Score", "Owner", "Controls"]
    for col, h in enumerate(risk_headers, 1):
        ws2.cell(row=1, column=col, value=h).font = Font(bold=True)

    for i, risk in enumerate(state["risk_entries"], 2):
        ws2.cell(row=i, column=1, value=risk.get("id", f"RISK-{i}"))
        ws2.cell(row=i, column=2, value=risk.get("description", ""))
        ws2.cell(row=i, column=3, value=risk.get("probability", 0))
        ws2.cell(row=i, column=4, value=risk.get("impact", 0))
        ws2.cell(row=i, column=5, value=risk.get("risk_score", 0))
        ws2.cell(row=i, column=6, value=risk.get("owner", ""))
        ws2.cell(row=i, column=7, value=str(risk.get("related_controls", [])))

    path = OUTPUT_DIR / f"issue_log_{session_id}.xlsx"
    wb.save(path)
    return str(path)
```

### Task 5.2: Word Memo Generator

```python
# services/output_generator.py (tiếp theo)
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from config.llm import get_llm_client
import json

MEMO_GENERATION_PROMPT = """You are a senior auditor writing an audit memo. Based on the findings below, write a professional audit memo in Vietnamese.

Session: {session_id}
Stage: {stage}
Findings: {findings_json}
Anomaly Summary: {anomaly_summary}

Structure:
1. Mục tiêu kiểm toán
2. Tóm tắt thủ tục thực hiện
3. Phát hiện chính (mô tả chi tiết từng phát hiện theo mức độ ưu tiên)
4. Nguyên nhân & Tác động dự kiến
5. Đề xuất bước tiếp theo

Write in formal Vietnamese audit language. Be specific, reference actual finding IDs (FND-xxx)."""

async def generate_memo(state: dict) -> str:
    llm = get_llm_client("generation")
    anomaly_summary = f"{len(state['anomaly_flags'])} anomalies flagged: " + \
                      ", ".join(set(f["rule"] for f in state["anomaly_flags"]))
    
    prompt = MEMO_GENERATION_PROMPT.format(
        session_id=state["session_id"],
        stage=state["stage"],
        findings_json=json.dumps(state["audit_findings"][:10], ensure_ascii=False),
        anomaly_summary=anomaly_summary
    )
    memo_text = await llm(prompt)

    doc = Document()
    doc.add_heading(f"AUDIT MEMO — {state['stage']}", 0)
    doc.add_paragraph(f"Session ID: {state['session_id']}")
    doc.add_paragraph(f"Giai đoạn: {state['stage']}")
    doc.add_paragraph("")

    # Parse memo sections
    for line in memo_text.split("\n"):
        line = line.strip()
        if not line: continue
        if line.startswith(("1.", "2.", "3.", "4.", "5.")):
            doc.add_heading(line, level=1)
        else:
            doc.add_paragraph(line)

    path = OUTPUT_DIR / f"audit_memo_{state['session_id']}.docx"
    doc.save(path)
    return str(path)
```

---

## Phase 6 — FastAPI Endpoints & Main App (ngày 6)

### Task 6.1: Main API Routes

```python
# api/routes.py (complete)
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import DocumentBundle, FileRecord, AuditFinding, AuditorFeedback
from agents.orchestrator import run_audit_pipeline
from services.file_handler import save_and_classify
import uuid, asyncio

router = APIRouter(prefix="/api/v1")

# --- Session Management ---
@router.post("/sessions")
def create_session(db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())[:8]
    return {"session_id": session_id, "status": "created"}

# --- File Upload ---
@router.post("/sessions/{session_id}/upload")
async def upload_files(
    session_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    results = []
    for f in files:
        record = await save_and_classify(f, session_id)
        results.append({"file_id": record.id, "filename": record.filename,
                        "format": record.format, "stage": record.stage})
    return {"session_id": session_id, "uploaded": len(results), "files": results}

# --- Run Pipeline ---
@router.post("/sessions/{session_id}/run")
async def run_audit(
    session_id: str,
    stage: str = Form("BOTH"),
    db: Session = Depends(get_db)
):
    """Trigger the full audit pipeline for a session."""
    # Load file records
    files = db.query(FileRecord).filter(FileRecord.bundle.has(session_id=session_id)).all()
    if not files:
        raise HTTPException(404, "No files found for this session")

    file_records = [{"id": f.id, "filename": f.filename, "format": f.format,
                     "file_path": f.file_path, "stage": f.stage} for f in files]

    try:
        result = await run_audit_pipeline(session_id, stage, file_records)
    except Exception as e:
        raise HTTPException(500, f"Pipeline error: {str(e)}")

    # Save findings to DB
    for finding_data in result["audit_findings"]:
        finding = AuditFinding(
            session_id=session_id,
            stage=stage,
            description=finding_data.get("description", ""),
            root_cause=finding_data.get("root_cause", ""),
            expected_impact=finding_data.get("expected_impact", ""),
            severity=finding_data.get("severity", "MEDIUM"),
            confidence_score=finding_data.get("confidence_score", 0.0),
            status="OPEN"
        )
        db.add(finding)
    db.commit()

    return {
        "session_id": session_id,
        "stage": stage,
        "findings_count": len(result["audit_findings"]),
        "anomalies_count": len(result["anomaly_flags"]),
        "output_paths": result["output_paths"],
        "changelog": result["versioned_notes"]
    }

# --- Get Findings ---
@router.get("/sessions/{session_id}/findings")
def get_findings(session_id: str, db: Session = Depends(get_db)):
    findings = db.query(AuditFinding).filter_by(session_id=session_id).all()
    return [{"id": f.id, "stage": f.stage, "description": f.description,
             "severity": f.severity, "status": f.status,
             "confidence_score": f.confidence_score} for f in findings]

# --- Download Output ---
@router.get("/sessions/{session_id}/download/{file_type}")
def download_output(session_id: str, file_type: str):
    """file_type: issue_log | memo | risk_register"""
    from pathlib import Path
    file_map = {
        "issue_log": f"outputs/issue_log_{session_id}.xlsx",
        "memo": f"outputs/audit_memo_{session_id}.docx"
    }
    path = file_map.get(file_type)
    if not path or not Path(path).exists():
        raise HTTPException(404, "Output file not found. Run the pipeline first.")
    return FileResponse(path, filename=Path(path).name)

# --- Auditor Feedback ---
@router.post("/findings/{finding_id}/feedback")
def submit_feedback(
    finding_id: str,
    action: str = Form(...),  # ACCEPT | REJECT | MODIFY
    comment: str = Form(""),
    db: Session = Depends(get_db)
):
    finding = db.query(AuditFinding).filter_by(id=finding_id).first()
    if not finding:
        raise HTTPException(404, "Finding not found")
    
    feedback = AuditorFeedback(
        finding_id=finding_id,
        action=action,
        comment=comment
    )
    db.add(feedback)

    # Update finding status based on feedback
    if action == "ACCEPT":
        finding.status = "RESOLVED"
    elif action == "REJECT":
        finding.status = "RESOLVED"
    elif action == "MODIFY":
        finding.status = "IN_PROGRESS"

    db.commit()
    return {"status": "feedback_recorded", "finding_id": finding_id, "action": action}
```

### Task 6.2: Main App Entry Point

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from api.routes import router
import os

app = FastAPI(
    title="AI Audit Tool — MVP",
    description="End-to-end audit automation: upload → extract → analyze → output",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(router)

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok", "llm_provider": os.getenv("LLM_PROVIDER", "groq")}
```

### Task 6.3: .env Configuration

```bash
# .env
LLM_PROVIDER=groq              # groq | mistral | ollama
GROQ_API_KEY=gsk_xxxx          # Get free at console.groq.com
MISTRAL_API_KEY=xxxx           # Fallback
OLLAMA_URL=http://localhost:11434
DATABASE_URL=sqlite:///./audit_mvp.db
MAX_FILE_SIZE_MB=50
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
```

---

## Phase 7 — Test & Validation (ngày 7)

### Task 7.1: Integration Test Script

```python
# test_pipeline.py — chạy ngay để validate end-to-end
import asyncio, httpx

BASE = "http://localhost:8000/api/v1"

async def test_full_flow():
    async with httpx.AsyncClient(timeout=120) as client:
        # 1. Create session
        r = await client.post(f"{BASE}/sessions")
        session_id = r.json()["session_id"]
        print(f"Session: {session_id}")

        # 2. Upload test files
        with open("test_data/journal_entries.csv", "rb") as f:
            r = await client.post(
                f"{BASE}/sessions/{session_id}/upload",
                files={"files": ("journal_entries.csv", f, "text/csv")}
            )
        print(f"Upload: {r.json()}")

        # 3. Run pipeline
        r = await client.post(
            f"{BASE}/sessions/{session_id}/run",
            data={"stage": "INTERIM"}
        )
        result = r.json()
        print(f"Findings: {result['findings_count']}")
        print(f"Anomalies: {result['anomalies_count']}")
        print(f"Outputs: {result['output_paths']}")

        # 4. Download issue log
        r = await client.get(f"{BASE}/sessions/{session_id}/download/issue_log")
        with open(f"test_output_issue_log.xlsx", "wb") as f:
            f.write(r.content)
        print("Issue log downloaded ✓")

asyncio.run(test_full_flow())
```

### Task 7.2: Test Data để Validate

Tạo thư mục `test_data/` với các file mẫu tối thiểu:
- `journal_entries.csv` — 100 rows, có cột: date, reference, debit, credit, description, amount
- `trial_balance.xlsx` — sheet "TB" với cột: account_code, account_name, debit, credit, balance
- `sop_procurement.docx` — text mô tả quy trình mua hàng đơn giản
- `walkthrough_notes.pdf` — text mô tả test of controls

---

## Frontend Bridge — Prompt cho Google Stitch

> **Mục đích**: Sau khi backend MVP hoàn tất, dùng prompt này trên Google Stitch để tạo FE tương thích.

---

### API Contract Summary (giao cho Stitch)

```
BASE URL: http://localhost:8000/api/v1

POST   /sessions                              → {session_id}
POST   /sessions/{id}/upload                  → {files: [{file_id, filename, format, stage}]}
POST   /sessions/{id}/run  (form: stage)      → {findings_count, anomalies_count, output_paths, changelog}
GET    /sessions/{id}/findings                → [{id, stage, description, severity, status, confidence_score}]
GET    /sessions/{id}/download/{type}         → file binary (issue_log | memo | risk_register)
POST   /findings/{id}/feedback  (form: action, comment) → {status}
```

---

### Google Stitch Prompt

```
Build a minimal, professional web UI for an AI Audit Tool. The tool already has a working backend API. 
The UI should be a single-page application acting as an interface to that backend — NOT a standalone system.

BASE API URL: http://localhost:8000/api/v1

SCREENS REQUIRED (keep it simple, 4 screens total):

--- SCREEN 1: New Audit Session ---
- Button: "Tạo phiên kiểm toán mới" → POST /sessions → store session_id
- Display returned session_id prominently
- File upload area: drag & drop or click to upload multiple files
  → POST /sessions/{id}/upload with multipart files
  → Show upload result: filename, format, detected stage (INTERIM/FIELDWORK/BOTH) as badges
- Dropdown to select audit stage: INTERIM | FIELDWORK | BOTH
- Button: "Chạy phân tích" → POST /sessions/{id}/run (form: stage)
  → Show loading spinner with message: "Đang phân tích tài liệu..."
  → On success: show summary card with findings_count, anomalies_count

--- SCREEN 2: Findings Dashboard ---
- Triggered after run completes
- Load GET /sessions/{id}/findings
- Table with columns: Finding ID | Stage | Description | Severity | Confidence | Status | Actions
- Severity column: color-coded badges (CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=green)
- Confidence column: progress bar (0-100%)
- Actions column: "Chấp nhận" (ACCEPT) | "Từ chối" (REJECT) | "Chỉnh sửa" (MODIFY) buttons
  → POST /findings/{id}/feedback with action + optional comment
  → Update row status inline without page reload
- Filter bar: filter by severity, stage, status

--- SCREEN 3: Download Outputs ---
- Two download buttons:
  → "Tải Issue Log (Excel)" → GET /sessions/{id}/download/issue_log → trigger browser download
  → "Tải Audit Memo (Word)" → GET /sessions/{id}/download/memo → trigger browser download
- → "Tải Risk Register (Excel)" → GET /sessions/{id}/download/risk_register → trigger browser download
- Show changelog (versioned_notes array from run response) as a timeline list

--- SCREEN 4: Session History ---
- Simple list of past session IDs stored in localStorage
- Click any session to load its findings

DESIGN REQUIREMENTS:
- Framework: React + Tailwind CSS (or plain HTML/CSS if React not available)
- Color scheme: Professional navy blue (#1F4E79) header, white content, subtle gray borders
- Font: Inter or system-ui
- NO complex state management — use simple useState and fetch()
- All API calls include error handling with user-friendly Vietnamese error messages
- Mobile-responsive but desktop-first
- NO authentication in MVP — session_id is the only identity

IMPORTANT CONSTRAINTS:
- This is a TOOL, not a platform. Keep UI minimal and functional.
- Do not add features not listed above.
- Do not create backend code — only the frontend that calls the API above.
- Labels and messages in Vietnamese.
```

---

## Thứ tự Triển khai (Khuyến nghị)

| Ngày | Việc cần làm | Output có thể chạy ngay |
|---|---|---|
| **1** | Phase 0 (structure + DB) + Phase 1 (upload API) | `POST /sessions`, `POST /upload` hoạt động |
| **2** | Phase 2 (extractor.py + doc_agent.py classify) | Có thể extract text từ PDF/Excel thực |
| **3** | Phase 2 (data_agent normalize) + Phase 3 (anomaly rules) | Phát hiện được bất thường số học |
| **4** | Phase 3 (LLM reasoning) + Phase 4 (LangGraph wiring) | Pipeline chạy qua LLM Groq |
| **5** | Phase 4 (complete graph) + Phase 5 (Excel output) | Có file issue_log.xlsx download được |
| **6** | Phase 5 (memo) + Phase 6 (all endpoints) | End-to-end API hoàn chỉnh |
| **7** | Phase 7 (test) + debug | Validated với dữ liệu thật |
| **8+** | Dùng Stitch prompt → build FE | Tool hoàn chỉnh với UI |

---

## Checklist trước khi bắt đầu code

```bash
# Verify prerequisites
python --version          # >= 3.11
pip --version
tesseract --version       # sudo apt install tesseract-ocr tesseract-ocr-vie

# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Get free API key
# → https://console.groq.com (free, no credit card)
# → Copy key to .env as GROQ_API_KEY

# Start server
uvicorn main:app --reload --port 8000

# Test health
curl http://localhost:8000/health
```

---

*MVP_TODO.md — generated from PRD v1.0 | Backend-first | Vibe coding ready*
