# COMPLETE_PRODUCT.md — AVE: Lộ Trình MVP → Sản Phẩm Hoàn Chỉnh

> **Mục đích:** Tài liệu này là kế hoạch thực thi dành cho coding agent đọc và thực hiện tuần tự. Mỗi giai đoạn là một đơn vị công việc khép kín, tối ưu cho 1 lần chạy của agent mà không gây hết token.
>
> **Nguyên tắc đọc:** Agent đọc toàn bộ tài liệu này trước, sau đó thực hiện **từng giai đoạn một**. Sau mỗi giai đoạn, đánh dấu checklist tương ứng và commit code trước khi chuyển sang giai đoạn tiếp theo.

---

## Trạng Thái Xuất Phát (MVP Hiện Tại)

| Thành phần | Trạng thái |
|---|---|
| Luồng end-to-end cơ bản | ✅ Hoàn thành |
| Orchestrator / Doc / Data / Audit Agent (nền tảng) | ✅ Hoàn thành |
| DB entities cơ bản + API session/upload/findings | ✅ Hoàn thành |
| Validation keyword-based | ✅ Hoàn thành (cần nâng cấp) |
| UI upload → run → results → download | ✅ Hoàn thành |
| Validation chéo đa nguồn | ❌ Chưa có |
| AuditScope / ExecutionPlan / InternalProcessMap entities | ❌ Chưa có |
| Test of controls + Risk-control matrix nghiệp vụ | ❌ Chưa có |
| Idempotency chống duplicate findings | ❌ Chưa có |
| EvidenceLink traceability (page/sheet/row) | ❌ Chưa có |
| Feedback loop → AccuracyMetric → KnowledgeBaseEntry | ❌ Chưa có |
| Materiality classification + ConsolidatedFinding | ❌ Chưa có |

---

## Kiến Trúc Đích (Full Product)

```
[Upload files]
      │
      ▼
[Phase 1: Validation nâng cao]       ← Giai đoạn 1
  FileRecord[] → DocumentBundle → ValidationReport (business rules)
      │
      ▼
[Phase 2: Planning & Data Model]     ← Giai đoạn 2
  AuditScope → ExecutionPlan → AuditTask[] → InternalProcessMap
      │
      ▼
[Phase 3: Extraction nâng cao]       ← Giai đoạn 3
  ExtractedDocument (OCR, EML) + NormalizedTable (schema-aware)
      │
      ├─────────────────────────┐
      ▼                         ▼
[Phase 4: Interim Audit]       [Phase 5: Fieldwork]    ← Giai đoạn 4 & 5
  Test of controls              Roll-forward / Reconciliation
  Risk-control matrix           Evidence validation (cross-agent)
  Anomaly detection             Ageing / Lead schedule analysis
      │                         │
      └────────────┬────────────┘
                   ▼
      [Phase 6: Consolidation]       ← Giai đoạn 6
        ConsolidatedFinding + Materiality + MANUAL_REVIEW flag
                   │
                   ▼
      [Phase 7: Output & Traceability] ← Giai đoạn 7
        Excel / Word / PDF + EvidenceLink (page/sheet/row) + VersionedNote
                   │
                   ▼
      [Phase 8: Feedback Loop]       ← Giai đoạn 8
        AuditorFeedback → AccuracyMetric → KnowledgeBaseEntry
```

---

## Master Checklist Tiến Độ

> Agent đánh dấu `[x]` sau khi hoàn thành từng mục. Checklist này là nguồn sự thật duy nhất về tiến độ.

### Giai đoạn 1 — Nâng Cấp Validation & Data Model Nền Tảng
- [x] 1.1 Thêm entities mới vào DB: `AuditScope`, `ExecutionPlan`, `InternalProcessMap`, `AccuracyMetric`, `KnowledgeBaseEntry`
- [x] 1.2 Migrate DB (Alembic hoặc tương đương) không phá vỡ schema cũ
- [x] 1.3 Nâng cấp `ValidationReport`: thêm business rules theo từng `stage` (INTERIM / FIELDWORK)
- [x] 1.4 Thêm cross-field validation: file bắt buộc theo giai đoạn (ví dụ: INTERIM cần SOP + risk matrix)
- [x] 1.5 Thêm idempotency key cho `AuditFinding` (hash từ source_file_id + rule_id + location)
- [x] 1.6 Viết unit tests cho validation logic mới
- [x] 1.7 Cập nhật API routes để trả về `ValidationReport` đầy đủ

### Giai đoạn 2 — Planning Agent & ExecutionPlan
- [x] 2.1 Implement `AuditScope` builder trong Orchestrator: đọc DocumentBundle, xác định phạm vi
- [x] 2.2 Implement `ExecutionPlan` generator: chia nhỏ thành `AuditTask[]` có priority và dependencies
- [x] 2.3 Implement task dispatcher: phân công task cho đúng agent theo `assigned_agent` field
- [x] 2.4 Implement `InternalProcessMap` builder trong Doc Agent: trích xuất quy trình nội bộ từ SOP/policy
- [x] 2.5 Lưu `AuditScope` và `ExecutionPlan` vào Working Store (DB)
- [x] 2.6 Expose API endpoint: `GET /session/{id}/execution-plan`
- [x] 2.7 Viết integration test: upload SOP → tạo được InternalProcessMap

### Giai đoạn 3 — Nâng Cấp Extraction & Normalization
- [x] 3.1 Nâng cấp Doc Agent: hỗ trợ OCR cho ảnh/scan (JPG, PNG, TIFF) bằng thư viện phù hợp
- [x] 3.2 Nâng cấp Doc Agent: parse EML/PST (metadata + body + attachments)
- [x] 3.3 Nâng cấp Data Agent: schema-aware normalization (TRIAL_BALANCE, JOURNAL, LEAD_SCHEDULE, AGEING, RECONCILIATION)
- [x] 3.4 Implement column mapping: ánh xạ tên cột thực tế → schema chuẩn bằng LLM + fuzzy match
- [x] 3.5 Liên kết `ExtractedDocument` với `InternalProcessMap` khi nội dung là SOP/policy
- [x] 3.6 Lưu `NormalizedTable.schema_type` đúng enum theo PRD
- [x] 3.7 Viết unit tests cho từng schema normalizer

### Giai đoạn 4 — Interim Audit: Test of Controls & Risk-Control Matrix
- [x] 4.1 Implement `TestOfControls` runner trong Audit Agent: kiểm tra kiểm soát trên dữ liệu giao dịch giữa kỳ
- [x] 4.2 Implement business rules cho test of controls (ví dụ: segregation of duties, authorization limits)
- [x] 4.3 Implement `RiskControlMatrix` builder: liên kết `RiskEntry` → `ControlEntry` → test result
- [x] 4.4 Implement autonomy logic trong Orchestrator: khi phát sinh rủi ro mới → tự thêm task mới vào ExecutionPlan
- [x] 4.5 Nâng cấp anomaly detection: thay keyword-based bằng rule engine + statistical checks
- [x] 4.6 Sinh đầu ra Interim: issue log + risk register + risk-control matrix + memo (lưu DB)
- [x] 4.7 Áp dụng idempotency: trước khi ghi finding, kiểm tra hash trùng
- [x] 4.8 Viết integration test: upload ERP data → tạo được RiskControlMatrix

### Giai đoạn 5 — Fieldwork: Reconciliation, Evidence Validation & EvidenceLink
- [x] 5.1 Implement roll-forward / reconciliation engine: đối chiếu số dư cuối kỳ với trial balance
- [x] 5.2 Implement ageing analysis: phân tích ageing và lead schedule, phát hiện sai lệch trọng yếu
- [x] 5.3 Implement cross-agent evidence validation: Doc Agent + Audit Agent cùng xác thực chứng từ số hóa
- [x] 5.4 Implement `EvidenceLink` builder: gán link page/sheet/row cụ thể cho từng `AuditFinding`
- [x] 5.5 Implement `VersionedNote` writer: ghi changelog mỗi khi finding hoặc state thay đổi
- [x] 5.6 Implement autonomy: khi phát hiện sai lệch ngoài kế hoạch → tự bổ sung bước kiểm tra
- [x] 5.7 Expose API: `GET /finding/{id}/evidence-links` trả về links với reference đầy đủ
- [x] 5.8 Viết integration test: upload trial balance + reconciliation → tạo được EvidenceLink

### Giai đoạn 6 — Consolidation, Materiality & Cross-Validation
- [x] 6.1 Implement `ConsolidatedFinding` builder: tổng hợp findings từ Interim + Fieldwork
- [x] 6.2 Implement cross-source evidence matching: đối chiếu bằng chứng chéo giữa nhiều nguồn
- [x] 6.3 Implement `MaterialityClassification`: phân loại IMMATERIAL / MATERIAL / HIGHLY_MATERIAL
- [x] 6.4 Implement `MANUAL_REVIEW_REQUIRED` flag: gắn khi phát hiện mâu thuẫn giữa các nguồn
- [x] 6.5 Implement consistency check: kiểm tra tính nhất quán giữa các giấy tờ làm việc
- [x] 6.6 Implement `confidence_score` calculator cho `ConsolidatedFinding`
- [x] 6.7 Expose API: `GET /session/{id}/consolidated-findings`
- [x] 6.8 Viết unit tests cho materiality classifier và cross-validation logic

### Giai đoạn 7 — Output Hoàn Chỉnh, Traceability UI & Versioned Notes
- [x] 7.1 Nâng cấp output generator: Excel issue log có EvidenceLink reference (page/sheet/row)
- [x] 7.2 Nâng cấp output generator: Word memo tổng hợp có confidence score cho từng finding
- [x] 7.3 Nâng cấp output generator: Risk register cập nhật cuối với điểm rủi ro và kiểm soát
- [x] 7.4 Sinh PDF bằng chứng: đính kèm evidence cho từng finding
- [x] 7.5 Sinh Versioned notes / changelog dạng `.md` đầy đủ từ `VersionedNote` records
- [x] 7.6 Nâng cấp UI: hiển thị EvidenceLink (page/sheet/row) bên cạnh mỗi finding trong Results view
- [x] 7.7 Nâng cấp UI: hiển thị confidence score và MANUAL_REVIEW badge trên mỗi finding
- [x] 7.8 Nâng cấp UI: hiển thị materiality label (IMMATERIAL / MATERIAL / HIGHLY_MATERIAL)
- [x] 7.9 Viết E2E test: chạy pipeline đầy đủ → tải xuống tất cả output formats

### Giai đoạn 8 — Feedback Loop, AccuracyMetric & KnowledgeBase
- [x] 8.1 Nâng cấp feedback UI: auditor có thể ACCEPT / REJECT / MODIFY từng finding với comment
- [x] 8.2 Implement `AuditorFeedback` writer: lưu action + comment + corrected_value vào DB
- [x] 8.3 Implement `AccuracyMetric` calculator: đo độ lệch giữa agent output và expert judgment theo finding category
- [x] 8.4 Implement `KnowledgeBaseEntry` writer: trích xuất pattern mới từ feedback, lưu vào knowledge base
- [x] 8.5 Integrate KnowledgeBase vào Audit Agent: load entries liên quan khi khởi động pipeline mới
- [x] 8.6 Implement priority weight updater trong Orchestrator: điều chỉnh ưu tiên xử lý dựa trên AccuracyMetric
- [x] 8.7 Expose API: `GET /accuracy-metrics` và `GET /knowledge-base`
- [x] 8.8 Viết integration test: submit feedback → verify KnowledgeBaseEntry được tạo → chạy lại pipeline → verify kết quả cải thiện

---

## Chi Tiết Từng Giai Đoạn

---

### GIAI ĐOẠN 1 — Nâng Cấp Validation & Data Model Nền Tảng

**Phạm vi:** DB schema + validation logic. Không thay đổi agent logic.

**Mục tiêu:** Đặt nền tảng data model đầy đủ theo PRD trước khi build các tính năng nghiệp vụ. Nếu thiếu bước này, các giai đoạn sau sẽ không có chỗ lưu dữ liệu.

**Files cần tạo/sửa:**
```
db/models.py                    ← Thêm AuditScope, ExecutionPlan, InternalProcessMap,
                                   AccuracyMetric, KnowledgeBaseEntry
                                   Thêm idempotency_key vào AuditFinding
db/migrations/                  ← Tạo migration file mới
services/validator.py           ← Nâng cấp ValidationReport với business rules
api/routes.py                   ← Cập nhật endpoint trả về ValidationReport đầy đủ
tests/test_validation.py        ← Unit tests mới
```

**Business rules validation cần implement (theo PRD §4, Bước 1):**
- INTERIM stage bắt buộc: ít nhất 1 file `DOCX/PDF` (SOP/policy) + 1 file `XLSX/CSV` (risk matrix hoặc ERP data)
- FIELDWORK stage bắt buộc: ít nhất 1 file `XLSX` (trial balance hoặc lead schedule) + 1 file `PDF/scan` (chứng từ)
- Cảnh báo nếu thiếu: ghi vào `ValidationReport.warnings[]`, không block pipeline
- Lỗi nếu thiếu bắt buộc: ghi vào `ValidationReport.errors[]`, block pipeline

**Idempotency key (theo PRD §9):**
```python
# Trong AuditFinding
idempotency_key = sha256(f"{source_file_id}:{rule_id}:{location_ref}").hexdigest()
# Trước khi INSERT: SELECT existing WHERE idempotency_key = ? → skip nếu tồn tại
```

**Entities mới cần thêm vào `db/models.py`:**
```python
class AuditScope:
    id: str
    session_id: str
    objectives: list[str]          # mục tiêu kiểm toán cụ thể
    stage: enum [INTERIM, FIELDWORK]
    risk_profile: str              # nhận định rủi ro tổng thể

class ExecutionPlan:
    id: str
    audit_scope_id: str
    tasks: list[AuditTask]
    created_at: datetime
    updated_at: datetime           # cập nhật khi Orchestrator tự điều chỉnh

class InternalProcessMap:
    id: str
    session_id: str
    source_file_id: str
    process_name: str
    process_steps: list[str]
    controls_identified: list[str]
    extracted_at: datetime

class AccuracyMetric:
    id: str
    session_id: str
    finding_category: str
    total_findings: int
    accepted: int
    rejected: int
    modified: int
    accuracy_rate: float
    calculated_at: datetime

class KnowledgeBaseEntry:
    id: str
    pattern_type: str              # loại pattern (anomaly, control_failure, ...)
    description: str
    source_session_id: str
    confidence: float
    created_at: datetime
    applicable_stages: list[str]
```

**Không được làm trong giai đoạn này:** Không sửa agent logic, không thay đổi frontend.

---

### GIAI ĐOẠN 2 — Planning Agent & ExecutionPlan

**Phạm vi:** Orchestrator + Doc Agent. Dựa trên data model đã tạo ở Giai đoạn 1.

**Mục tiêu:** Orchestrator thực sự "lập kế hoạch" thay vì chỉ gọi agents tuần tự. Đây là nền tảng của nguyên tắc `Goal-driven` và `Planning` trong PRD.

**Files cần tạo/sửa:**
```
agents/orchestrator.py          ← Thêm AuditScope builder, ExecutionPlan generator, task dispatcher
agents/doc_agent.py             ← Thêm InternalProcessMap builder
services/task_dispatcher.py     ← Module mới: phân công AuditTask → đúng agent
api/routes.py                   ← Thêm GET /session/{id}/execution-plan
tests/test_orchestrator.py      ← Integration tests
```

**Logic AuditScope builder (trong Orchestrator):**
```python
def build_audit_scope(document_bundle) -> AuditScope:
    # 1. Đọc ValidationReport để biết stage và file types có sẵn
    # 2. Dùng LLM prompt để xác định objectives từ nội dung tài liệu
    # 3. Nhận định risk_profile ban đầu từ file types và metadata
    # 4. Lưu vào DB và trả về AuditScope
```

**Logic ExecutionPlan generator:**
```python
def generate_execution_plan(audit_scope) -> ExecutionPlan:
    tasks = []
    # Luôn có: EXTRACTION tasks cho mỗi file
    # Nếu INTERIM: thêm TEST_OF_CONTROLS, RISK_MATRIX tasks
    # Nếu FIELDWORK: thêm RECONCILIATION, AGEING_ANALYSIS, EVIDENCE_VALIDATION tasks
    # Luôn có: ANOMALY_DETECTION, CONSOLIDATION tasks
    # Gán priority (1=cao nhất) theo mức độ rủi ro
    # Gán dependencies (RECONCILIATION phụ thuộc EXTRACTION)
    return ExecutionPlan(tasks=sorted(tasks, key=lambda t: t.priority))
```

**Logic InternalProcessMap builder (trong Doc Agent):**
```python
def extract_internal_process(extracted_doc) -> InternalProcessMap | None:
    # Chỉ áp dụng nếu content_type là PROCESS_DESC
    # Dùng LLM để trích xuất: tên quy trình, các bước, kiểm soát nhận diện
    # Lưu vào DB với reference về source_file_id
```

**Autonomy hook (cần implement ngay từ bước này):**
```python
# Trong Orchestrator, sau mỗi task completed:
def on_task_completed(task, result):
    if result.has_unexpected_risk:
        new_tasks = generate_additional_tasks(result.new_risk)
        execution_plan.add_tasks(new_tasks)  # tự điều chỉnh kế hoạch
        save_versioned_note(f"Added {len(new_tasks)} tasks due to new risk: {result.new_risk}")
```

---

### GIAI ĐOẠN 3 — Nâng Cấp Extraction & Normalization

**Phạm vi:** Doc Agent + Data Agent. Không thay đổi audit logic.

**Mục tiêu:** Extraction đủ mạnh để xử lý toàn bộ file types trong PRD §8.1, normalization đủ thông minh để ánh xạ schema thực tế.

**Files cần tạo/sửa:**
```
agents/doc_agent.py             ← Thêm OCR handler, EML/PST parser
agents/data_agent.py            ← Nâng cấp schema detection
services/normalizer.py          ← Thêm normalizers cho TRIAL_BALANCE, JOURNAL,
                                   LEAD_SCHEDULE, AGEING, RECONCILIATION
services/ocr_service.py         ← Module mới: OCR wrapper
services/email_parser.py        ← Module mới: EML/PST parser
tests/test_normalizer.py        ← Unit tests từng schema
```

**OCR handler (Doc Agent):**
```python
# Sử dụng pytesseract hoặc easyocr (kiểm tra dependency đã có)
def extract_from_image(file_path) -> ExtractedDocument:
    text = ocr_service.extract(file_path)
    return ExtractedDocument(content_type=detect_content_type(text), content=text)
```

**EML/PST parser (Doc Agent):**
```python
def parse_email(file_path) -> ExtractedDocument:
    # Dùng email (stdlib) cho EML, extract-msg hoặc libpff cho PST
    # Trích xuất: from, to, date, subject, body, attachments metadata
    return ExtractedDocument(content_type="EMAIL_CONFIRMATION", content={...})
```

**Schema-aware normalization (Data Agent):**
```python
SCHEMA_SIGNATURES = {
    "TRIAL_BALANCE": ["account_code", "debit", "credit", "balance"],
    "JOURNAL":       ["date", "journal_id", "debit_account", "credit_account", "amount"],
    "LEAD_SCHEDULE": ["line_item", "prior_year", "current_year", "variance"],
    "AGEING":        ["customer", "0-30", "31-60", "61-90", "90+", "total"],
    "RECONCILIATION":["item", "book_balance", "bank_balance", "difference"],
}

def detect_schema(df: DataFrame) -> SchemaType:
    # Dùng LLM + fuzzy match để ánh xạ tên cột thực tế → schema chuẩn
    # Trả về SchemaType enum và column_mapping dict
```

**Không được làm trong giai đoạn này:** Không implement audit rules, không thay đổi output generator.

---

### GIAI ĐOẠN 4 — Interim Audit: Test of Controls & Risk-Control Matrix

**Phạm vi:** Audit Agent (Interim logic). Dựa trên data từ Giai đoạn 2 & 3.

**Mục tiêu:** Audit Agent thực sự chạy kiểm toán nghiệp vụ theo chuẩn Interim, không chỉ phát hiện keyword.

**Files cần tạo/sửa:**
```
agents/audit_agent.py           ← Thêm test_of_controls_runner, risk_control_matrix_builder
services/rule_engine.py         ← Module mới: business rules cho test of controls
services/anomaly_detector.py    ← Nâng cấp: statistical checks thay keyword-based
tests/test_interim_audit.py     ← Integration tests
```

**Test of controls rules (examples theo chuẩn kiểm toán):**
```python
CONTROL_RULES = [
    {
        "id": "TOC-001",
        "name": "Segregation of Duties",
        "description": "Người tạo và người duyệt giao dịch phải khác nhau",
        "check": lambda df: df[df["creator"] == df["approver"]],
        "severity": "HIGH"
    },
    {
        "id": "TOC-002",
        "name": "Authorization Limit",
        "description": "Giao dịch > ngưỡng phải có duyệt cấp trên",
        "check": lambda df: df[(df["amount"] > LIMIT) & (df["approval_level"] < REQUIRED_LEVEL)],
        "severity": "CRITICAL"
    },
    {
        "id": "TOC-003",
        "name": "Completeness — Sequential Numbering",
        "description": "Số chứng từ phải liên tục, không có gap",
        "check": lambda df: detect_gaps(df["voucher_number"]),
        "severity": "MEDIUM"
    },
    # ... thêm rules theo nghiệp vụ
]
```

**Risk-Control Matrix builder:**
```python
def build_risk_control_matrix(audit_scope, test_results) -> list[dict]:
    # Liên kết: RiskEntry → ControlEntry → TestResult
    # Dùng InternalProcessMap để nhận diện controls từ SOP
    # Gắn test_result: EFFECTIVE / DEFICIENT / NOT_TESTED
    # Lưu vào DB dưới dạng ControlEntry records
```

**Autonomy: tự điều chỉnh kế hoạch:**
```python
# Sau mỗi control test failure:
if test_result == "DEFICIENT" and risk.probability > HIGH_RISK_THRESHOLD:
    orchestrator.add_task(AuditTask(
        type="DEEP_DIVE_INVESTIGATION",
        priority=1,  # ưu tiên cao nhất
        description=f"Deep dive: {risk.description}"
    ))
```

**Idempotency (bắt buộc cho mọi finding được tạo):**
```python
def create_finding_safe(finding_data) -> AuditFinding:
    key = compute_idempotency_key(finding_data)
    existing = db.query(AuditFinding).filter_by(idempotency_key=key).first()
    if existing:
        return existing  # skip duplicate
    return db.create(AuditFinding(**finding_data, idempotency_key=key))
```

---

### GIAI ĐOẠN 5 — Fieldwork: Reconciliation, Evidence Validation & EvidenceLink

**Phạm vi:** Audit Agent (Fieldwork logic) + EvidenceLink system. Dựa trên Giai đoạn 3 & 4.

**Mục tiêu:** Fieldwork audit có khả năng đối chiếu số liệu cuối kỳ và gắn bằng chứng cụ thể cho từng finding.

**Files cần tạo/sửa:**
```
agents/audit_agent.py           ← Thêm fieldwork_runner, reconciliation_engine, ageing_analyzer
agents/doc_agent.py             ← Thêm cross-agent evidence validation helper
services/evidence_linker.py     ← Module mới: tạo EvidenceLink với page/sheet/row reference
services/reconciliation.py      ← Module mới: roll-forward, reconciliation logic
api/routes.py                   ← Thêm GET /finding/{id}/evidence-links
tests/test_fieldwork.py         ← Integration tests
```

**Reconciliation engine:**
```python
def reconcile_trial_balance(trial_balance: NormalizedTable, roll_forward: NormalizedTable):
    # So sánh closing balance của roll_forward với trial_balance
    # Phát hiện: unexplained differences > materiality threshold
    # Sinh AuditFinding với severity dựa trên difference amount
    # Gắn EvidenceLink trỏ về cả hai file nguồn
```

**Ageing analysis:**
```python
def analyze_ageing(ageing_table: NormalizedTable):
    # Phát hiện: overdue buckets > threshold (ví dụ: 90+ > 20% total)
    # So sánh với prior period nếu có
    # Sinh AuditFinding với reference đến sheet + row cụ thể
```

**EvidenceLink builder (quan trọng — theo PRD §9 Truy vết):**
```python
def create_evidence_link(finding_id, source_file, location) -> EvidenceLink:
    return EvidenceLink(
        finding_id=finding_id,
        source_file_id=source_file.id,
        reference=format_reference(source_file, location)
        # format_reference returns: "Sheet2!B15" hoặc "Page 3, Para 2" hoặc "Row 142"
    )
```

**Cross-agent evidence validation:**
```python
# Doc Agent extract chứng từ → Audit Agent verify số liệu khớp
def cross_validate_evidence(doc_agent_result, audit_finding):
    # Doc Agent: trích xuất số liệu từ PDF/scan chứng từ
    # Audit Agent: so sánh với số liệu trong NormalizedTable
    # Nếu mâu thuẫn: gắn MANUAL_REVIEW_REQUIRED = True
```

---

### GIAI ĐOẠN 6 — Consolidation, Materiality & Cross-Validation

**Phạm vi:** Orchestrator (consolidation) + Audit Agent (materiality). Dựa trên output của Giai đoạn 4 & 5.

**Mục tiêu:** Tổng hợp toàn bộ findings, phân loại theo materiality, gắn flag review thủ công khi cần.

**Files cần tạo/sửa:**
```
agents/orchestrator.py          ← Thêm consolidation_runner, cross_source_matcher
agents/audit_agent.py           ← Thêm materiality_classifier, consistency_checker
services/consolidator.py        ← Module mới: tổng hợp findings
api/routes.py                   ← Thêm GET /session/{id}/consolidated-findings
tests/test_consolidation.py     ← Unit + integration tests
```

**Consolidation logic:**
```python
def consolidate_findings(session_id) -> list[ConsolidatedFinding]:
    interim_findings = db.query(AuditFinding).filter_by(stage="INTERIM", session_id=session_id)
    fieldwork_findings = db.query(AuditFinding).filter_by(stage="FIELDWORK", session_id=session_id)

    consolidated = []
    for fw_finding in fieldwork_findings:
        # Tìm finding tương tự từ Interim (theo description similarity + source area)
        matching_interim = find_matching_interim(fw_finding, interim_findings)
        cf = ConsolidatedFinding(
            interim_finding_id=matching_interim.id if matching_interim else None,
            fieldwork_finding_id=fw_finding.id,
            materiality=classify_materiality(fw_finding),
            confidence_score=calculate_confidence(fw_finding, matching_interim)
        )
        consolidated.append(cf)
    return consolidated
```

**Materiality classifier:**
```python
MATERIALITY_RULES = {
    "HIGHLY_MATERIAL": lambda f: f.severity == "CRITICAL" or f.expected_impact_amount > HIGH_THRESHOLD,
    "MATERIAL":        lambda f: f.severity in ["HIGH", "MEDIUM"] or f.expected_impact_amount > MED_THRESHOLD,
    "IMMATERIAL":      lambda f: True  # default
}
```

**Cross-source evidence matching:**
```python
def match_evidence_across_sources(finding) -> bool:
    """Returns True nếu bằng chứng nhất quán, False nếu mâu thuẫn"""
    evidence_links = db.query(EvidenceLink).filter_by(finding_id=finding.id)
    values = [extract_value(link) for link in evidence_links]
    if has_contradiction(values):
        finding.review_flag = True  # MANUAL_REVIEW_REQUIRED
        save_versioned_note(f"Contradiction detected in evidence for {finding.id}")
        return False
    return True
```

---

### GIAI ĐOẠN 7 — Output Hoàn Chỉnh, Traceability UI & Versioned Notes

**Phạm vi:** Output generator + Frontend. Đây là giai đoạn duy nhất có thay đổi frontend lớn.

**Mục tiêu:** Output đủ chuẩn để bàn giao thực sự cho kiểm toán viên; UI hiển thị đầy đủ evidence và confidence.

**Files cần tạo/sửa:**
```
services/output_generator.py    ← Nâng cấp toàn bộ output formats
frontend/src/features/results/  ← Nâng cấp Results view
frontend/src/components/        ← Thêm EvidenceLinkBadge, ConfidenceScore, MaterialityTag
api/routes.py                   ← Endpoint download từng output type riêng biệt
tests/test_e2e.py               ← E2E test: pipeline đầy đủ → download all outputs
```

**Output formats cần nâng cấp:**

| Output | Nội dung bổ sung so với MVP |
|---|---|
| Excel issue log | Cột `evidence_reference` (page/sheet/row), `confidence_score`, `materiality`, `review_flag` |
| Word memo | Confidence score cho từng finding, section MANUAL_REVIEW_REQUIRED riêng |
| Risk register | Điểm rủi ro cuối + control test result + link đến ConsolidatedFinding |
| PDF bằng chứng | Bundle evidence files theo finding, có annotation page/row |
| Versioned notes `.md` | Full changelog từ `VersionedNote` records, có timestamp và author |

**Frontend changes (Results view):**
```tsx
// Thêm vào mỗi FindingCard:
<EvidenceLinkBadge links={finding.evidence_links} />
// Hiển thị: "Sheet2!B15 | Page 3" — clickable nếu có URL

<ConfidenceScore score={finding.confidence_score} />
// Hiển thị: progress bar 0-100%

<MaterialityTag level={finding.materiality} />
// Hiển thị: chip màu (đỏ=HIGHLY_MATERIAL, vàng=MATERIAL, xanh=IMMATERIAL)

{finding.review_flag && <ManualReviewBadge />}
// Hiển thị: ⚠️ MANUAL REVIEW REQUIRED
```

---

### GIAI ĐOẠN 8 — Feedback Loop, AccuracyMetric & KnowledgeBase

**Phạm vi:** Feedback system + Knowledge base integration. Giai đoạn cuối cùng.

**Mục tiêu:** Hệ thống học từ phản hồi của kiểm toán viên và cải thiện qua các lần chạy tiếp theo.

**Files cần tạo/sửa:**
```
agents/orchestrator.py          ← Tích hợp KnowledgeBase vào pipeline startup
agents/audit_agent.py           ← Load KnowledgeBaseEntry khi chạy rule engine
services/feedback_processor.py  ← Module mới: xử lý feedback → AccuracyMetric → KnowledgeBaseEntry
frontend/src/features/feedback/ ← Nâng cấp: ACCEPT/REJECT/MODIFY với comment + corrected_value
api/routes.py                   ← GET /accuracy-metrics, GET /knowledge-base
tests/test_feedback_loop.py     ← Integration test: feedback → knowledge base → pipeline improvement
```

**Feedback processor:**
```python
def process_feedback(feedback: AuditorFeedback):
    # 1. Lưu AuditorFeedback vào DB
    # 2. Cập nhật AccuracyMetric cho finding.category trong session
    # 3. Nếu action == REJECT hoặc MODIFY: extract pattern → KnowledgeBaseEntry
    # 4. Ghi VersionedNote: "Auditor rejected finding {id}: {comment}"

def extract_knowledge_pattern(feedback: AuditorFeedback) -> KnowledgeBaseEntry:
    # Dùng LLM để phân tích: tại sao finding bị reject/modify?
    # Trích xuất: pattern_type, description, applicable contexts
    # Gán confidence = 1.0 nếu REJECT, 0.7 nếu MODIFY
```

**KnowledgeBase integration vào pipeline:**
```python
# Trong Orchestrator, khi khởi động pipeline mới:
def load_relevant_knowledge(session) -> list[KnowledgeBaseEntry]:
    entries = db.query(KnowledgeBaseEntry).filter(
        KnowledgeBaseEntry.applicable_stages.contains(session.stage)
    ).order_by(KnowledgeBaseEntry.confidence.desc()).limit(50)
    return entries

# Trong Audit Agent, khi chạy rule:
def run_rule_with_knowledge(rule, data, knowledge_entries):
    # Inject knowledge như context vào LLM prompt
    # Adjust rule thresholds dựa trên historical accuracy
```

**AccuracyMetric calculator:**
```python
def calculate_accuracy(session_id, category) -> AccuracyMetric:
    feedbacks = db.query(AuditorFeedback).join(AuditFinding).filter(
        AuditFinding.session_id == session_id,
        AuditFinding.category == category
    )
    total = feedbacks.count()
    accepted = feedbacks.filter_by(action="ACCEPT").count()
    return AccuracyMetric(
        accuracy_rate=accepted / total if total > 0 else 0.0,
        # ...
    )
```

**Priority weight updater (Orchestrator autonomy):**
```python
# Dựa trên AccuracyMetric từ sessions trước:
# Nếu accuracy thấp cho TEST_OF_CONTROLS → tăng priority của MANUAL_REVIEW tasks
# Nếu accuracy cao cho ANOMALY_DETECTION → giảm priority, tăng tốc pipeline
```

---

## Quy Tắc Thực Thi Cho Coding Agent

### Trước khi bắt đầu mỗi giai đoạn:
1. Đọc lại phần "Chi tiết" của giai đoạn đó trong tài liệu này
2. Đọc file hiện tại sẽ bị sửa đổi để hiểu context
3. Kiểm tra checklist: các giai đoạn phụ thuộc đã `[x]` chưa

### Trong khi thực hiện:
- Giữ backward compatibility: không break API endpoints hiện có
- Mọi function mới phải có docstring giải thích nghiệp vụ
- Mọi finding creation phải đi qua `create_finding_safe()` để đảm bảo idempotency
- Dùng LLM (via existing LLM service) cho: schema detection, process extraction, knowledge pattern extraction
- Không dùng LLM cho: arithmetic checks, rule-based validation, DB operations

### Sau khi hoàn thành mỗi giai đoạn:
1. Đánh dấu `[x]` tất cả items trong checklist của giai đoạn đó
2. Chạy tests: `pytest tests/test_<giai_doan>.py -v`
3. Commit với message: `feat(phase-N): <mô tả ngắn>`
4. Kiểm tra không có regression: `pytest tests/ -v --tb=short`

### Xử lý lỗi:
- Nếu LLM output không parse được: log warning, dùng fallback rule-based
- Nếu file không đọc được: tạo `FileRecord` với `validation_status=INVALID`, tiếp tục pipeline
- Nếu DB migration fail: rollback, báo lỗi rõ ràng, không tiếp tục

---

## Phụ Lục: Mapping PRD → Giai Đoạn

| PRD Section | Giai đoạn thực hiện |
|---|---|
| §4 Bước 1 — Tiếp nhận & Xác thực | Giai đoạn 1 (nâng cấp) |
| §4 Bước 2 — Lập kế hoạch | Giai đoạn 2 |
| §4 Bước 3 — Xử lý & Chuẩn hóa | Giai đoạn 3 |
| §4 Bước 4 — Interim Audit | Giai đoạn 4 |
| §4 Bước 5 — Fieldwork | Giai đoạn 5 |
| §4 Bước 6 — Tổng hợp & Validation chéo | Giai đoạn 6 |
| §4 Bước 7 — Sinh đầu ra | Giai đoạn 7 |
| §4 Bước 8 — Feedback Loop | Giai đoạn 8 |
| §6 Data Model — entities mới | Giai đoạn 1 |
| §9 Idempotency | Giai đoạn 1 + 4 |
| §9 Truy vết (EvidenceLink) | Giai đoạn 5 + 7 |
| §9 Versioning (VersionedNote) | Giai đoạn 5 + 7 |
| §9 Confidence scoring | Giai đoạn 6 + 7 |
| §2.3 Autonomy | Giai đoạn 2 + 4 |
| §2.3 Feedback loop | Giai đoạn 8 |
