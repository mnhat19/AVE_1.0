# AVE MVP: Use Cases

Bộ tài liệu này mô tả các tình huống thực tế (Use Cases) mà một kiểm toán viên (Auditor) sẽ sử dụng hệ thống AI Audit Tool (AVE) MVP. Dữ liệu thử nghiệm đã được cung cấp sẵn trong thư mục `test_data/`.

## Use Case 1: Kiểm toán giữa kỳ (Interim Audit) - Kiểm tra Quy trình & Kiểm soát nội bộ

**Mô tả:** 
Kiểm toán viên cần đọc hiểu các tài liệu mô tả quy trình (SOP) và ghi chú quá trình walk-through để tìm ra các rủi ro, lỗ hổng kiểm soát.

**Actor:** Kiểm toán viên (Auditor)
**Input Data:** 
- `sop_procurement.docx`: Quy trình mua hàng với ngưỡng phê duyệt rõ ràng.
- `policy_internal.docx`: Policy kiểm soát nội bộ.
- `walkthrough_notes.pdf`: Ghi chép walkthrough và kết luận quan sát.
- `risk_matrix.xlsx`: Ma trận rủi ro - kiểm soát.
- `test_of_controls.xlsx`: Kết quả test kiểm soát.
- `control_questionnaire.xlsx`: Bảng hỏi kiểm soát.
- `email_confirmation.eml`: Email xác nhận walkthrough.

**Luồng thực thi:**
1. Auditor truy cập vào giao diện AVE.
2. Tạo mới một Session.
3. Kéo thả 2 file `sop_procurement.docx` và `walkthrough_notes.pdf` vào vùng Upload.
4. Chọn tải lên (Upload Bundle) và chờ hệ thống phân tích, trích xuất dữ liệu.
5. Tại màn hình Execution, Auditor chọn Stage là **INTERIM**.
6. Nhấn "Run Audit" để kích hoạt AI Agent phân tích quy trình mua hàng, đối chiếu rủi ro.
7. Chuyển sang màn hình Results, Auditor xem danh sách các Findings (điểm yếu kiểm soát, rủi ro) do AI phát hiện.
8. Auditor xem xét, gửi Feedback (Accept/Reject/Modify) cho từng finding.
9. Tải xuống `Risk Register` (Excel) để lưu hồ sơ kiểm toán.

---

## Use Case 2: Kiểm toán cuối kỳ (Fieldwork Audit) - Phân tích Dữ liệu Kế toán

**Mô tả:**
Kiểm toán viên cần rà soát sổ nhật ký chung (Journal Entries) và bảng cân đối phát sinh (Trial Balance) để tìm các bút toán bất thường, sai lệch số liệu.

**Actor:** Kiểm toán viên (Auditor)
**Input Data:**
- `journal_entries.csv`: Sổ nhật ký chung.
- `gl_export.csv`: Trích xuất sổ cái.
- `trial_balance.xlsx`: Bảng cân đối phát sinh cuối kỳ.
- `lead_schedule.xlsx`: Lead schedule theo tài khoản.
- `ageing.csv`: Bảng phân tích tuổi nợ.
- `reconciliation.xlsx`: Bảng đối chiếu.
- `bank_statement.pdf`: Sao kê ngân hàng.
- `inventory_count.png`: Ảnh kiểm kê tồn kho.
- `confirmation_letter.eml`: Thư xác nhận ngân hàng.

**Luồng thực thi:**
1. Auditor tiếp tục dùng Session hiện tại hoặc tạo mới.
2. Tải lên `journal_entries.csv` và `trial_balance.xlsx`.
3. Tại màn hình Execution, chọn Stage là **FIELDWORK**.
4. Nhấn "Run Audit". Các Rule-based engine và Data Agent sẽ quét các bút toán (như làm tròn số, giao dịch cuối tuần, mất cân đối).
5. AI tổng hợp các "Anomalies" thành Findings.
6. Auditor vào màn hình Results, lọc các Findings có mức độ (Severity) là "HIGH" hoặc "CRITICAL".
7. Auditor tải xuống `Issue Log` (Excel) để báo cáo Ban giám đốc, hoặc tải `Audit Memo` (Word) để xem văn bản thuyết minh.

---

## Use Case 3: Chạy toàn trình (End-to-End Both Stages)

**Mô tả:** 
Khi nhận đủ hồ sơ, kiểm toán viên muốn hệ thống chạy đánh giá rủi ro tổng thể dựa trên cả thông tin quy trình lẫn dữ liệu số.

**Luồng thực thi:**
1. Upload toàn bộ bộ tài liệu trong `sample_audit_documents/`.
2. Chọn Stage: **BOTH**.
3. Hệ thống sẽ trích xuất (Extraction) -> Nhận diện bảng (Normalization) -> Quét rủi ro quy trình (Doc Agent) -> Quét lỗi số liệu (Data Agent) -> Tổng hợp báo cáo.
4. Kết quả sẽ hiển thị Findings đa dạng: Từ lỗi thiết kế kiểm soát đến bút toán sai lệch.

---

## Use Case 4: Xử lý bằng chứng phi cấu trúc (OCR + Email)

**Mô tả:**
Kiểm toán viên cần xác minh ảnh kiểm kê tồn kho và email xác nhận để bổ sung bằng chứng cho findings.

**Input Data:**
- `inventory_count.png`
- `confirmation_letter.eml`

**Luồng thực thi:**
1. Upload 2 file trên và chạy Stage: **FIELDWORK**.
2. Kiểm tra Findings có liên kết tới bằng chứng phi cấu trúc.
3. Tải xuống `Audit Memo` để xác nhận nội dung giải trình.
