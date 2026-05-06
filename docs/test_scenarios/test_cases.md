# AVE MVP: Test Cases

Bộ Test Cases này dùng để kiểm thử ứng dụng từ góc độ người dùng (Black-box testing) trên giao diện Frontend, kết nối với Backend nội bộ.

## TC01: Khởi tạo Session thành công
- **Pre-condition**: Backend chạy tại `localhost:8000`, Frontend tại `localhost:5173`.
- **Steps**:
  1. Mở trình duyệt, truy cập Frontend.
  2. Tại bảng **Session Initialization**, nhấn nút `Create Session`.
- **Expected Result**: 
  - Giao diện vô hiệu hóa nút (disable) trong 1-2 giây.
  - Sau đó, hiển thị thông báo thành công.
  - Ở mục **Session Metadata** bên dưới và trên **TopBar**, `Session ID` (chuỗi 8 ký tự) xuất hiện.
  - Biểu tượng trạng thái API báo `Operational`.

## TC02: Tải lên hồ sơ kiểm toán (Upload Bundle)
- **Pre-condition**: Đã thực hiện TC01 (Có Session ID).
- **Steps**:
  1. Kéo thả các file: `journal_entries.csv`, `trial_balance.xlsx`, `lead_schedule.xlsx`, `ageing.csv`, `reconciliation.xlsx`, `confirmation_letter.eml`.
  2. Bấm nút `Upload Bundle`.
- **Expected Result**:
  - Giao diện báo `Uploading...`
  - Bảng **Upload Queue** hiển thị đầy đủ các file với format đúng.
  - Status chuyển sang `VALID` hoặc `SUCCESS`.
  - `Validation Report` (nếu có) hiển thị JSON chi tiết các hạng mục thiếu.

## TC03: Thực thi luồng Fieldwork Audit
- **Pre-condition**: Có Session ID và đã upload thành công data (TC02).
- **Steps**:
  1. Di chuyển xuống phần **Execution Controls**.
  2. Nhấp chọn nút `FIELDWORK`.
  3. Bấm `Run Audit`.
- **Expected Result**:
  - Nút chuyển sang trạng thái `Running...` và bị disable.
  - Bảng **Execution Status** hiển thị `Running`.
  - Bảng **Execution Plan** bắt đầu liệt kê các task (Doc Agent, Data Agent).
  - Sau khi xong, Status đổi thành `Completed`.

## TC04: Xem và lọc kết quả (Findings)
- **Pre-condition**: Đã thực hiện TC03, audit run status là Completed.
- **Steps**:
  1. Kéo xuống mục **Findings Overview**.
  2. Kiểm tra 3 thẻ KPI: Findings, Anomalies, Consolidated (phải > 0).
  3. Trong bảng Findings, chọn Severity Filter = `HIGH`.
  4. Copy một keyword bất kỳ từ mô tả của Finding hiện có (ví dụ một từ khóa trong Description).
  5. Dán keyword đó vào ô Search.
- **Expected Result**:
  - Bảng tự động rút gọn, chỉ hiển thị findings có Severity = HIGH và chứa keyword vừa dán.

## TC05: Gửi phản hồi (Feedback) cho Finding
- **Pre-condition**: Có Findings trong bảng.
- **Steps**:
  1. Nhấn nút `Feedback` ở dòng Finding đầu tiên.
  2. Cửa sổ Modal hiện lên, hiển thị đúng Description của Finding đó.
  3. Chọn Action = `MODIFY`, nhập Comment = `Đã kiểm tra chứng từ gốc, số liệu hợp lý, cần giảm trừ rủi ro.`
  4. Nhấn `Submit`.
- **Expected Result**:
  - Modal tự đóng.
  - Dòng Finding tương ứng tự cập nhật Status từ `OPEN` sang `IN_PROGRESS`.

## TC06: Tải xuống báo cáo
- **Pre-condition**: Audit Run đã Completed.
- **Steps**:
  1. Tại bảng **Downloads**, nhấn nút `Download` cạnh `Issue Log (XLSX)`.
- **Expected Result**:
  - Trình duyệt tải xuống file `issue_log_<session_id>.xlsx`. Mở file lên kiểm tra thấy có format bảng chuẩn chỉ của Excel.
