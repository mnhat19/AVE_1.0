# AVE MVP: Edge Cases & Error Handling

Bộ tài liệu này liệt kê các tình huống ngoại lệ (Edge Cases) thường gặp trong quá trình vận hành MVP và cách hệ thống phản ứng lại để đảm bảo tính ổn định.

## EC01: Mất kết nối tới Backend (API Offline)
- **Tình huống:** Người dùng bật Frontend nhưng Backend uvicorn bị tắt, crash hoặc sai cấu hình CORS.
- **Hành vi mong muốn:**
  - `TopBar` hiển thị chữ `Offline` màu đỏ và có chỉ báo `(Mock Mode)`.
  - Toàn bộ giao diện tiếp tục hoạt động dựa trên dữ liệu Mock (Fallback). Người dùng vẫn tạo được Session (mock id), upload file (mock success) và xem findings giả lập mà không bị trắng màn hình.

## EC02: Dung lượng tệp vượt quá giới hạn (413 Payload Too Large)
- **Tình huống:** Tải lên tệp vượt quá cấu hình của FastAPI (thường cấu hình ở Nginx hoặc max file size của Multipart).
- **Hành vi mong muốn:**
  - Backend chặn luồng xử lý và ném lỗi 413.
  - Frontend bắt lỗi `catch` tại hàm `uploadSessionFiles`, và hiển thị thông báo lỗi bằng chữ màu đỏ bên dưới nút Upload: `Upload failed. File size too large.`

## EC03: Chạy Audit khi chưa tải file (Missing Data)
- **Tình huống:** Người dùng tạo session xong, quên tải file mà bấm ngay vào nút `Run Audit`.
- **Hành vi mong muốn:**
  - Màn hình Run không cấm người dùng nhấn, nhưng API backend khi nhận request sẽ kiểm tra `DocumentBundle` của `session_id` này.
  - Trả về mã lỗi 400 Bad Request, kèm thông báo "No files found for this session".
  - Giao diện `RunPanel` hiện dòng thông báo lỗi này dưới thẻ trạng thái.

## EC04: LLM Provider Timeout (Hoặc hết Quota Groq API)
- **Tình huống:** `llama-3.3-70b` phân tích một file quá dài dẫn tới API Groq báo lỗi 429 (Rate Limit) hoặc Timeout sau 60s.
- **Hành vi mong muốn:**
  - Agent orchestrator bắt exception, tự động sử dụng Fallback logic (trả về kết quả rỗng thay vì làm sập cả graph).
  - Kết quả `run` thành công nhưng `findings_count = 0`.
  - Ghi chú lỗi LLM vào mục **Changelog** để người dùng (hoặc Dev) đọc được và khắc phục.

## EC05: Định dạng file không được hỗ trợ
- **Tình huống:** Kéo thả 1 file `.exe` hoặc `.rar` vào vùng Drop zone.
- **Hành vi mong muốn:**
  - Hàm `classify` ở backend gán `format="TXT"` hoặc `UNKNOWN`.
  - Bộ phận `Extractor` không parse được nội dung.
  - Trong **Validation Report** trả về sau khi tải lên, có ghi chú: `"filename.rar": "Unsupported format"`. File vẫn được nhận dạng (để lưu vet) nhưng không đưa vào đường ống tính toán AI.

  ## EC06: OCR không khả dụng (Thiếu Tesseract)
  - **Tình huống:** Người dùng upload file ảnh (ví dụ `inventory_count.png`) nhưng máy chủ chưa cài Tesseract OCR.
  - **Hành vi mong muốn:**
    - Pipeline không bị sập.
    - Trích xuất trả về nội dung rỗng và ghi chú lỗi dạng `ocr_unavailable` trong metadata.
    - Findings vẫn được tổng hợp từ các file còn lại.

  ## EC07: Vượt giới hạn kích thước file
  - **Tình huống:** Upload file lớn hơn `MAX_FILE_SIZE_MB` (ví dụ `edge_cases/Oversize_Attachment.txt`).
  - **Hành vi mong muốn:**
    - Backend trả về HTTP 413.
    - Frontend hiển thị thông báo lỗi `Upload failed. File size too large.`
    - Các file hợp lệ khác trong bundle vẫn có thể upload lại sau đó.
