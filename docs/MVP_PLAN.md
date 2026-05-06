# Ke hoach hoan thien MVP

## 1. Tom tat tinh trang hien tai
- Da co FastAPI app, route sessions/upload/run/download/feedback.
- Co pipeline LangGraph: plan -> extract -> normalize -> detect anomalies -> reasoning -> output.
- Co LLM providers: groq, ollama, mistral.
- Co issue log, risk register, memo output.
- Co bo test data va test end-to-end.

## 2. Checklist yeu cau MVP_TODO con thieu
- [x] Bo sung trich xuat bang tu PDF (pdfplumber table extraction) va gan metadata (page, table index).
- [x] Tich hop extract_process_info vao pipeline va dua control info vao audit reasoning.
- [x] Bo sung services/normalizer.py (hoac tach normalize_table ra module rieng) de khop cau truc MVP_TODO.
- [x] Cap nhat health endpoint de tra ve LLM provider theo mo ta MVP_TODO.
- [x] Mo rong test_pipeline: tai xuong memo va kiem tra output paths day du.

## 3. Ke hoach trien khai (tu hien tai -> MVP hoan chinh)

### Pha 1: Hoan thien trich xuat + chuan hoa
- [x] Them PDF table extraction trong extractor.
- [x] Tao services/normalizer.py (wrapper goi data_agent.normalize_table).
- [x] Cap nhat orchestrator de luu thong tin sheet/page vao anomaly flags (de tao evidence link ro rang).
- [ ] Kiem thu bang test_data tu dong.

### Pha 2: Bo sung thong tin quy trinh/noi bo
- [x] Goi extract_process_info cho tai lieu SOP/policy/walkthrough.
- [x] Hop nhat internal controls vao input LLM reasoning.
- [x] Luu control summary vao versioned_notes hoac output.

### Pha 3: Hoan thien API va test
- [x] Health endpoint tra ve llm_provider.
- [x] Cap nhat test_pipeline: download memo va risk register.
- [x] Cap nhat README neu can.

### Pha 4: Traceability co ban (sau MVP)
- [x] Luu ExtractedDocument vao DB de truy vet.
- [x] Luu NormalizedTable vao DB de truy vet.

## 4. Backlog theo PRD (ngoai MVP, uu tien sau)
- Risk-control matrix va ControlEntry.
- Cross-source validation va evidence linking theo page/sheet/row.
- Idempotency (chay lai pipeline khong sinh duplicate findings).
- Feedback loop: accuracy metrics + knowledge base.
