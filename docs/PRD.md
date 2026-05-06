# PRD: AI Agent hỗ trợ Kiểm toán viên Kiểm chứng

**Phiên bản:** 1.0  
**Trạng thái:** Draft  
**Mục đích sử dụng:** Vibe coding với AI coding agents

---

## 1. Tổng quan sản phẩm

### 1.1 Mô tả

Hệ thống AI Agent đa tác tử (multi-agent) hỗ trợ kiểm toán viên trong hai giai đoạn kiểm toán cốt lõi: **Kiểm toán sơ bộ (Interim Audit)** và **Kiểm toán cuối kỳ (Fieldwork)**. Sản phẩm tự động hóa quá trình kiểm chứng thông tin, tối ưu độ chính xác và tiết kiệm thời gian xử lý hồ sơ kiểm toán.

### 1.2 Giá trị cốt lõi

- **Cơ chế validation tốt nhất thị trường**: Kết hợp logic kiểm toán nghiệp vụ với kỹ thuật lập trình tiên tiến.
- **Kiến trúc đa tác tử**: Các agent chuyên biệt hoạt động song song và phối hợp để xử lý nhiều loại tài liệu và thực hiện nhiều loại kiểm chứng đồng thời.
- **Quy trình kiểm chứng hỗn hợp**: Pha trộn giữa phân tích ngữ nghĩa tài liệu, đối chiếu dữ liệu có cấu trúc, và nhận dạng bất thường thống kê.

### 1.3 Vị trí can thiệp trong quy trình kiểm toán

```
Chấp nhận & duy trì KH  →  Lập kế hoạch  →  [INTERIM AUDIT]  →  [FIELDWORK]  →  Tổng hợp sai sót  →  Phát hành báo cáo
                                                      ↑                  ↑
                                               Can thiệp (a)      Can thiệp (b)
```

Sản phẩm **không** can thiệp vào: Chấp nhận và duy trì khách hàng, Lập kế hoạch kiểm toán, Tổng hợp sai sót & điều chỉnh, Kết thúc kiểm toán & phát hành báo cáo.

---

## 2. Kiến trúc hệ thống

### 2.1 Mô hình đa tác tử (Multi-Agent Architecture)

```
┌─────────────────────────────────────────────────────┐
│                  ORCHESTRATOR AGENT                 │
│   (Điều phối, lập kế hoạch, phân công, feedback)    │
└──────────┬──────────────┬──────────────┬────────────┘
           │              │              │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼───────────┐
    │  DOC AGENT  │ │ DATA AGENT │ │  AUDIT AGENT   │
    │  (Xử lý &   │ │ (Phân tích │ │ (Logic kiểm    │
    │  trích xuất │ │ dữ liệu có │ │  toán, rủi ro, │
    │  tài liệu)  │ │ cấu trúc)  │ │  validation)   │
    └─────────────┘ └────────────┘ └────────────────┘
           │              │              │
    ┌──────▼──────────────▼──────────────▼────────────┐
    │              SHARED MEMORY / WORKING STORE       │
    │   (Issue log, Risk register, Evidence links,     │
    │    Versioned notes, Audit state, Changelog)      │
    └─────────────────────────────────────────────────┘
```

### 2.2 Vai trò của từng Agent

| Agent | Trách nhiệm chính | Đầu vào | Đầu ra |
|---|---|---|---|
| **Orchestrator Agent** | Lập kế hoạch, phân công task, theo dõi trạng thái, điều phối feedback loop | Mục tiêu kiểm toán, trạng thái hệ thống | Task assignments, execution plan, consolidated report |
| **Doc Agent** | Đọc, trích xuất, chuẩn hóa tài liệu đa định dạng | Word, PDF, ảnh/scan, EML | Structured data, extracted text, metadata |
| **Data Agent** | Phân tích dữ liệu có cấu trúc, đối chiếu số liệu, phát hiện bất thường | Excel, CSV, XLSX, TXT (ERP exports) | Anomaly flags, reconciliation results, statistical findings |
| **Audit Agent** | Áp dụng logic kiểm toán, đánh giá rủi ro, tạo phát hiện | Structured data từ Doc/Data Agent | Risk matrix, issue log entries, audit findings |

### 2.3 Nguyên tắc thiết kế Agent

1. **Goal-driven**: Mỗi agent hoạt động hướng đến mục tiêu kiểm toán cụ thể, không phản hồi thụ động. Ưu tiên hành động có giá trị và tác động thực tế.
2. **Planning**: Orchestrator phân tích trạng thái hiện tại, chia nhỏ mục tiêu thành task con, tối ưu lộ trình xử lý theo dữ liệu nhận được.
3. **Autonomy**: Các agent tự điều chỉnh kế hoạch khi phát sinh rủi ro mới hoặc dữ liệu thay đổi. Tự quyết định thứ tự ưu tiên xử lý.
4. **Feedback loop**: Hệ thống ghi nhận phản hồi từ kiểm toán viên, so sánh kết quả với đánh giá chuyên gia, cập nhật knowledge base cho lần chạy sau.

---

## 3. Luồng xử lý tổng thể

```
[INPUT] → (1) Tiếp nhận & Xác thực
              → (2) Lập kế hoạch & Phân tích mục tiêu
                  → (3) Xử lý & Chuẩn hóa tài liệu
                      → (4) Interim Audit
                          → (5) Fieldwork
                              → (6) Tổng hợp & Validation chéo
                                  → (7) Sinh đầu ra & Bàn giao
                                      → (8) Feedback Loop → [UPDATE KNOWLEDGE BASE]
```

---

## 4. Chi tiết từng bước xử lý

### Bước 1 — Tiếp nhận & Xác thực đầu vào

**Nguyên tắc áp dụng:** Planning

**Xử lý:**
1. Nhận file từ kiểm toán viên qua interface (upload hoặc kết nối hệ thống).
2. Phân loại định dạng file: `PDF`, `DOCX`, `XLSX`, `CSV`, `TXT`, `JPG/PNG` (scan), `EML`, `PST`.
3. Xác thực tính đầy đủ của bộ tài liệu theo checklist bắt buộc cho từng giai đoạn.
4. Gắn nhãn giai đoạn kiểm toán: `INTERIM` hoặc `FIELDWORK`.
5. Phát cảnh báo nếu thiếu tài liệu bắt buộc, yêu cầu bổ sung trước khi tiếp tục.

**Entities:**
- `DocumentBundle`: tập hợp tài liệu đầu vào cho một phiên kiểm toán.
- `FileRecord`: metadata của từng file (tên, định dạng, giai đoạn, trạng thái xác thực).
- `ValidationReport`: kết quả xác thực tính đầy đủ của bundle.

---

### Bước 2 — Lập kế hoạch & Phân tích mục tiêu

**Nguyên tắc áp dụng:** Goal-driven, Planning

**Xử lý:**
1. Xác định phạm vi kiểm toán và mục tiêu cụ thể từ thông tin đầu vào.
2. Phân tích trạng thái hiện tại của bộ hồ sơ (độ đầy đủ, loại rủi ro tiềm năng).
3. Chia nhỏ mục tiêu thành danh sách `AuditTask` cụ thể.
4. Xây dựng `ExecutionPlan`: lộ trình xử lý tối ưu theo khoản mục và mức độ rủi ro ưu tiên.
5. Phân công task cho các agent chuyên biệt (Doc Agent, Data Agent, Audit Agent).

**Entities:**
- `AuditScope`: phạm vi và mục tiêu kiểm toán.
- `AuditTask`: một đơn vị công việc cụ thể (có loại, ưu tiên, agent phụ trách).
- `ExecutionPlan`: danh sách task có thứ tự và phụ thuộc.

---

### Bước 3 — Xử lý & Chuẩn hóa tài liệu

**Nguyên tắc áp dụng:** Planning

**Agent thực hiện:** Doc Agent, Data Agent

**Xử lý:**
1. **Doc Agent** trích xuất nội dung từ từng loại file:
   - `PDF/DOCX` → text + cấu trúc section.
   - `Ảnh/scan` → OCR → text.
   - `EML/PST` → metadata + nội dung email.
2. **Data Agent** đọc và chuẩn hóa dữ liệu có cấu trúc:
   - `XLSX/CSV/TXT` → normalized tabular data.
   - Ánh xạ cột theo schema chuẩn (trial balance schema, journal schema, v.v.).
3. Nhận diện quy trình nội bộ từ SOP, policy, walkthrough notes.
4. Liên kết dữ liệu kế toán với chứng từ gốc tương ứng.
5. Lưu trạng thái xử lý vào Working Store.

**Entities:**
- `ExtractedDocument`: nội dung đã trích xuất, có tham chiếu về `FileRecord` gốc.
- `NormalizedTable`: bảng dữ liệu đã chuẩn hóa với schema xác định.
- `InternalProcessMap`: mô tả quy trình nội bộ trích từ SOP/policy.

---

### Bước 4 — Kiểm toán sơ bộ (Interim Audit)

**Nguyên tắc áp dụng:** Autonomy

**Agent thực hiện:** Audit Agent (chính), Data Agent (hỗ trợ)

#### 4.1 Đầu vào

| Loại file | Nội dung |
|---|---|
| `Word/PDF` | Mô tả quy trình, lưu đồ, tường thuật KSNB, policy, SOP, walkthrough notes |
| `Excel` | Bảng hiểu biết quy trình, ma trận rủi ro–kiểm soát, test of controls, issue log, sampling plan, checklist |
| `CSV/TXT/XLSX` (ERP export) | Dữ liệu giao dịch giữa kỳ, dữ liệu kế toán trong kỳ, ước tính kế toán |
| `Ảnh/scan` | Sơ đồ, biên bản, chứng từ nội bộ đã ký, email xác nhận quan trọng |

#### 4.2 Quy trình xử lý

1. **Test of controls tự động**: chạy kiểm tra kiểm soát trên dữ liệu giao dịch giữa kỳ.
2. **Xây dựng ma trận rủi ro–kiểm soát**: liên kết rủi ro → kiểm soát → test result.
3. **Phát hiện bất thường**: gắn cờ rủi ro trong dữ liệu kế toán/ERP.
4. **Tự điều chỉnh danh sách ưu tiên** khi phát sinh rủi ro mới trong quá trình chạy.
5. **Sinh đầu ra sơ bộ**: issue log + risk register + memo tường thuật.

#### 4.3 Đầu ra

| Loại file | Nội dung |
|---|---|
| `Excel` (issue log) | Mã phát hiện, mô tả vấn đề, mức độ, người phụ trách, trạng thái xử lý |
| `Word` (memo) | Tường thuật phát hiện, nguyên nhân sơ bộ, tác động dự kiến, đề xuất bước tiếp theo |
| `PDF/scan` (bằng chứng) | Ảnh chụp, trích xuất hệ thống, email, biên bản làm việc làm nền cho phát hiện |
| `Excel/Word` (risk register) | Mã rủi ro, mô tả, xác suất, ảnh hưởng, điểm rủi ro, kiểm soát liên quan, chủ sở hữu |
| `Excel` (risk–control matrix) | Liên kết rủi ro với test kiểm soát |
| Versioned notes / changelog | Lịch sử cập nhật sau khi có thông tin mới từ khách hàng hoặc thủ tục kiểm toán |

---

### Bước 5 — Kiểm toán cuối kỳ (Fieldwork)

**Nguyên tắc áp dụng:** Autonomy, Planning

**Agent thực hiện:** Audit Agent (chính), Data Agent (chính), Doc Agent (hỗ trợ)

#### 5.1 Đầu vào

| Loại file | Nội dung |
|---|---|
| `Excel` | Lead schedule, trial balance, roll-forward, reconciliation, ageing, tie-out, test sheet, adjustment schedule |
| `PDF/scan` | Biên bản kiểm kê, xác nhận công nợ, hợp đồng, sao kê, chứng từ khóa sổ, báo cáo quản trị cuối kỳ |
| `CSV/XLSX/TXT` (ERP export) | Sổ cái, nhật ký chung, subledger, report cuối kỳ |
| Bằng chứng số hóa | Ảnh kiểm kê, file đính kèm email, file sign-off, tài liệu đối chiếu do khách hàng ký |

#### 5.2 Quy trình xử lý

1. **Đối chiếu số dư cuối kỳ** với trial balance, roll-forward, reconciliation.
2. **Phân tích ageing và lead schedule** để phát hiện sai lệch trọng yếu.
3. **Xác thực chứng từ số hóa** bằng cơ chế đa tác tử (cross-validate giữa Doc Agent và Audit Agent).
4. **Liên kết bằng chứng kiểm toán** với từng phát hiện và khoản mục tương ứng.
5. **Tự bổ sung bước kiểm tra** khi phát hiện sai lệch bất thường ngoài kế hoạch ban đầu.

#### 5.3 Đầu ra

| Loại file | Nội dung |
|---|---|
| `PDF` | Hợp đồng, hóa đơn, sao kê, biên bản, xác nhận ngân hàng, thư giải trình |
| `Ảnh/scan` | Biên bản kiểm kê, chứng từ ký tay, ảnh hiện trường |
| `Excel/CSV/XLSX` | Sổ cái, nhật ký, bảng phân tích, dữ liệu trích xuất từ ERP/kế toán |
| `Email/EML/PST` | Thư xác nhận, trao đổi với khách hàng, phản hồi bên thứ ba |

---

### Bước 6 — Tổng hợp & Validation chéo

**Nguyên tắc áp dụng:** Goal-driven, Autonomy

**Agent thực hiện:** Orchestrator Agent (điều phối), Audit Agent (thực hiện)

**Xử lý:**
1. Tổng hợp toàn bộ phát hiện từ cả hai giai đoạn (Interim + Fieldwork).
2. **Validation chéo** bằng chứng giữa nhiều nguồn (cross-source evidence matching).
3. Phân loại sai sót theo mức độ trọng yếu.
4. Kiểm tra tính nhất quán giữa các giấy tờ làm việc.
5. Gắn cờ `MANUAL_REVIEW_REQUIRED` cho các điểm mâu thuẫn cần kiểm toán viên xem xét thủ công.

**Entities:**
- `ConsolidatedFinding`: phát hiện tổng hợp từ cả hai giai đoạn, có confidence score.
- `EvidenceLink`: liên kết giữa finding và bằng chứng hỗ trợ.
- `MaterialityClassification`: phân loại mức độ trọng yếu của sai sót.

---

### Bước 7 — Sinh đầu ra & Bàn giao

**Xử lý:**
1. Sinh giấy tờ làm việc hoàn chỉnh: Excel checklist, Word memo, PDF bằng chứng.
2. Xuất danh sách sai sót đã phân loại theo mức độ trọng yếu.
3. Cập nhật versioned notes và changelog.
4. Trình bày kết quả cho kiểm toán viên kèm **confidence score** của từng phát hiện.

**Đầu ra cuối cùng:**

| Loại | Nội dung |
|---|---|
| Excel checklist | Toàn bộ issue log với trạng thái xử lý |
| Word memo | Tường thuật tổng hợp phát hiện |
| PDF bằng chứng | Bằng chứng đính kèm cho từng phát hiện |
| Risk register | Bản cập nhật cuối với điểm rủi ro và kiểm soát |
| Versioned notes | Changelog đầy đủ từ đầu đến cuối phiên |

---

### Bước 8 — Feedback Loop & Cập nhật hệ thống

**Nguyên tắc áp dụng:** Feedback loop

**Xử lý:**
1. Ghi nhận phản hồi và điều chỉnh của kiểm toán viên (accept/reject/modify findings).
2. So sánh kết quả agent với đánh giá chuyên gia để đo độ lệch.
3. Đánh giá độ chính xác theo từng loại phát hiện (accuracy per finding category).
4. Cập nhật trọng số ưu tiên và chiến lược xử lý cho lần chạy tiếp theo.
5. Lưu pattern phát hiện mới vào knowledge base của hệ thống.

**Entities:**
- `AuditorFeedback`: phản hồi của kiểm toán viên cho từng finding.
- `AccuracyMetric`: độ chính xác theo loại phát hiện.
- `KnowledgeBaseEntry`: pattern mới được học từ phiên hiện tại.

---

## 5. Logic nghiệp vụ cốt lõi

Đây là danh sách đầy đủ các business rules hệ thống phải tuân thủ:

1. Xác thực và phân loại tài liệu đầu vào theo loại file và giai đoạn kiểm toán.
2. Trích xuất và chuẩn hóa dữ liệu từ nhiều định dạng: Word, PDF, Excel, CSV, ảnh/scan, EML.
3. Nhận diện và phân tích quy trình nội bộ từ SOP, policy, walkthrough notes.
4. Xây dựng và cập nhật ma trận rủi ro–kiểm soát dựa trên dữ liệu đầu vào.
5. Thực hiện test of controls tự động trên dữ liệu giao dịch giữa kỳ.
6. Phát hiện bất thường và gắn cờ rủi ro trong dữ liệu kế toán/ERP.
7. Tạo và cập nhật issue log với mã phát hiện, mức độ, người phụ trách và trạng thái.
8. Sinh báo cáo tường thuật phát hiện sơ bộ kèm nguyên nhân và tác động dự kiến.
9. Quản lý versioned notes và changelog khi có thông tin cập nhật từ khách hàng.
10. Đối chiếu số dư cuối kỳ với trial balance, roll-forward và reconciliation.
11. Phân tích ageing và lead schedule để phát hiện sai lệch trọng yếu.
12. Xác thực chứng từ số hóa (biên bản kiểm kê, thư xác nhận, hợp đồng, sao kê) bằng kỹ thuật đa tác tử.
13. Liên kết bằng chứng kiểm toán với từng phát hiện và khoản mục tương ứng.
14. Tổng hợp danh sách sai sót và phân loại theo mức độ trọng yếu.
15. Sinh giấy tờ làm việc hoàn chỉnh cho giai đoạn cuối kỳ.
16. Điều phối luồng công việc giữa các tác tử chuyên biệt (logic kiểm toán, xử lý tài liệu, phân tích dữ liệu).
17. Theo dõi trạng thái xử lý từng vấn đề và nhắc nhở bước tiếp theo cho kiểm toán viên.
18. Kiểm soát chất lượng đầu ra bằng cơ chế validation chéo giữa nhiều nguồn bằng chứng.

---

## 6. Data Model (Entities)

```
DocumentBundle
  ├── id: string
  ├── session_id: string
  ├── stage: enum [INTERIM, FIELDWORK]
  └── files: FileRecord[]

FileRecord
  ├── id: string
  ├── filename: string
  ├── format: enum [PDF, DOCX, XLSX, CSV, TXT, IMAGE, EML, PST]
  ├── stage: enum [INTERIM, FIELDWORK]
  └── validation_status: enum [PENDING, VALID, INVALID, MISSING]

ExtractedDocument
  ├── id: string
  ├── source_file_id: string (→ FileRecord)
  ├── content_type: enum [PROCESS_DESC, TRANSACTION_DATA, CONFIRMATION, CONTRACT, ...]
  └── content: object (structured text or table)

NormalizedTable
  ├── id: string
  ├── schema_type: enum [TRIAL_BALANCE, JOURNAL, LEAD_SCHEDULE, AGEING, RECONCILIATION, ...]
  ├── source_file_id: string
  └── rows: object[]

AuditTask
  ├── id: string
  ├── type: enum [TEST_OF_CONTROLS, RECONCILIATION, ANOMALY_DETECTION, EVIDENCE_VALIDATION, ...]
  ├── priority: integer
  ├── assigned_agent: enum [DOC_AGENT, DATA_AGENT, AUDIT_AGENT]
  ├── status: enum [PENDING, IN_PROGRESS, COMPLETED, BLOCKED]
  └── dependencies: AuditTask[]

RiskEntry
  ├── id: string (mã rủi ro)
  ├── description: string
  ├── probability: float
  ├── impact: float
  ├── risk_score: float
  ├── related_controls: ControlEntry[]
  └── owner: string (chủ sở hữu rủi ro)

ControlEntry
  ├── id: string
  ├── description: string
  ├── test_result: enum [EFFECTIVE, DEFICIENT, NOT_TESTED]
  └── linked_risks: RiskEntry[]

AuditFinding
  ├── id: string (mã phát hiện)
  ├── stage: enum [INTERIM, FIELDWORK]
  ├── description: string
  ├── root_cause: string
  ├── expected_impact: string
  ├── severity: enum [LOW, MEDIUM, HIGH, CRITICAL]
  ├── assignee: string
  ├── status: enum [OPEN, IN_PROGRESS, RESOLVED, ESCALATED]
  ├── evidence_links: EvidenceLink[]
  └── confidence_score: float

EvidenceLink
  ├── id: string
  ├── finding_id: string (→ AuditFinding)
  ├── source_file_id: string (→ FileRecord)
  └── reference: string (page, sheet, row, etc.)

ConsolidatedFinding
  ├── id: string
  ├── interim_finding_id: string (→ AuditFinding, nullable)
  ├── fieldwork_finding_id: string (→ AuditFinding, nullable)
  ├── materiality: enum [IMMATERIAL, MATERIAL, HIGHLY_MATERIAL]
  ├── review_flag: boolean (MANUAL_REVIEW_REQUIRED)
  └── confidence_score: float

VersionedNote
  ├── id: string
  ├── session_id: string
  ├── timestamp: datetime
  ├── author: enum [SYSTEM, AUDITOR]
  ├── change_description: string
  └── previous_state_ref: string

AuditorFeedback
  ├── id: string
  ├── finding_id: string (→ AuditFinding)
  ├── action: enum [ACCEPT, REJECT, MODIFY]
  ├── comment: string
  └── corrected_value: object (nullable)
```

---

## 7. Luồng dữ liệu (Data Flow)

```
[Upload files]
      │
      ▼
[Step 1: Validation]
  FileRecord[] → DocumentBundle
      │
      ▼
[Step 2: Planning]
  DocumentBundle → AuditScope → ExecutionPlan → AuditTask[]
      │
      ▼
[Step 3: Extraction & Normalization]
  FileRecord → ExtractedDocument / NormalizedTable
      │
      ├──────────────────────────────────┐
      ▼                                  ▼
[Step 4: Interim Audit]        [Step 5: Fieldwork]
  NormalizedTable                NormalizedTable
  + ExtractedDocument            + ExtractedDocument
      │                                  │
      ▼                                  ▼
  AuditFinding[] (INTERIM)      AuditFinding[] (FIELDWORK)
  RiskEntry[]                   EvidenceLink[]
  ControlEntry[]
      │                                  │
      └─────────────┬────────────────────┘
                    ▼
          [Step 6: Consolidation]
          ConsolidatedFinding[]
          MaterialityClassification
                    │
                    ▼
          [Step 7: Output Generation]
          Excel / Word / PDF outputs
          VersionedNote (changelog)
                    │
                    ▼
          [Step 8: Feedback Loop]
          AuditorFeedback → AccuracyMetric → KnowledgeBaseEntry
```

---

## 8. Định dạng file hỗ trợ

### 8.1 Đầu vào

| Định dạng | Loại | Giai đoạn |
|---|---|---|
| `.docx`, `.doc` | Quy trình, SOP, policy, walkthrough notes | INTERIM |
| `.pdf` | Mô tả quy trình, chứng từ, biên bản, hợp đồng, sao kê | INTERIM, FIELDWORK |
| `.xlsx`, `.xls` | Ma trận rủi ro, trial balance, lead schedule, ageing, reconciliation | INTERIM, FIELDWORK |
| `.csv`, `.txt` | ERP export, sổ cái, nhật ký giao dịch | INTERIM, FIELDWORK |
| `.jpg`, `.png`, `.tiff` (scan) | Chứng từ ký tay, biên bản, sơ đồ, email scan | INTERIM, FIELDWORK |
| `.eml`, `.pst` | Thư xác nhận, trao đổi với khách hàng | FIELDWORK |

### 8.2 Đầu ra

| Định dạng | Nội dung | Giai đoạn |
|---|---|---|
| `.xlsx` | Issue log, risk register, ma trận rủi ro–kiểm soát, checklist | INTERIM, FIELDWORK |
| `.docx` | Memo tường thuật phát hiện, risk register dạng văn bản | INTERIM |
| `.pdf` | Bằng chứng kèm theo, giấy tờ làm việc hoàn chỉnh | INTERIM, FIELDWORK |
| `.xlsx/.csv` | Bảng phân tích tổng hợp, dữ liệu đối chiếu | FIELDWORK |
| Versioned `.md` / `.txt` | Changelog, versioned notes | INTERIM, FIELDWORK |

---

## 9. Yêu cầu phi chức năng

| Yêu cầu | Mô tả |
|---|---|
| **Độ chính xác** | Cơ chế validation chéo đa nguồn phải đảm bảo không bỏ sót phát hiện trọng yếu |
| **Khả năng mở rộng** | Kiến trúc agent phải cho phép thêm agent mới (ví dụ: Tax Agent, Consolidation Agent) mà không cần refactor |
| **Truy vết** | Mọi finding phải có EvidenceLink trỏ về file và vị trí nguồn gốc cụ thể |
| **Versioning** | Mọi thay đổi trạng thái phải được ghi vào VersionedNote với timestamp |
| **Confidence scoring** | Mỗi finding phải có confidence score để kiểm toán viên ưu tiên review |
| **Idempotency** | Chạy lại pipeline với cùng đầu vào không sinh ra duplicate findings |

---

## 10. Phạm vi ngoài sản phẩm (Out of Scope)

- Giai đoạn Chấp nhận và duy trì khách hàng.
- Giai đoạn Lập kế hoạch kiểm toán.
- Giai đoạn Tổng hợp sai sót và điều chỉnh (sau fieldwork).
- Giai đoạn Kết thúc kiểm toán và phát hành báo cáo kiểm toán chính thức.
- Ký số và xác thực pháp lý báo cáo.
- Tích hợp trực tiếp với phần mềm kế toán khách hàng (ERP integration) — hiện chỉ xử lý file export.
