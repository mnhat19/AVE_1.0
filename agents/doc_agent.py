import json

from config.llm import get_llm_client

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
    truncated = content[:3000]
    prompt = CLASSIFY_PROMPT.format(content=truncated)
    raw = await llm(prompt)
    try:
        return json.loads(raw.strip())
    except Exception:
        return {"doc_type": "OTHER", "confidence": 0.0, "error": "parse_failed", "raw": raw}


async def extract_process_info(content: str) -> dict:
    llm = get_llm_client("extraction")
    raw = await llm(EXTRACT_PROCESS_PROMPT.format(content=content[:4000]))
    try:
        return json.loads(raw.strip())
    except Exception:
        return {"process_name": "Unknown", "key_controls": [], "risk_indicators": []}
