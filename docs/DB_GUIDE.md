# DB_GUIDE.md — Hướng Dẫn Sử Dụng Cơ Sở Dữ Liệu (Tương Tác Trực Tiếp)

## 1. Tổng Quan
Hệ thống dùng SQLite làm mặc định. File DB chính là `audit_mvp.db` (đường dẫn phụ thuộc `DATABASE_URL`).

- DB mặc định: `sqlite:///./audit_mvp.db`
- Vị trí file: thư mục gốc dự án

## 2. Xác Định Đúng File DB Trên Máy
### 2.1. Kiểm tra qua biến môi trường
Trong PowerShell:
```bash
$env:DATABASE_URL
```
Nếu trống, DB mặc định là `audit_mvp.db` tại thư mục gốc.

### 2.2. Kiểm tra file tồn tại
Mở File Explorer và tìm `audit_mvp.db` trong thư mục dự án.

## 3. Công Cụ Tương Tác Trực Tiếp (Không Dùng Python)
Bạn có thể chọn một trong các công cụ sau:

### 3.1. DB Browser for SQLite (khuyến nghị cho SQLite)
1. Cài đặt DB Browser for SQLite.
2. Mở file `audit_mvp.db`.
3. Dùng tab “Browse Data” để xem dữ liệu.
4. Dùng tab “Execute SQL” để chạy lệnh SQL.

### 3.2. DBeaver
1. Tạo kết nối mới → SQLite.
2. Chọn file `audit_mvp.db`.
3. Dùng SQL Editor để truy vấn và chỉnh sửa.

### 3.3. SQLite CLI
Mở PowerShell tại thư mục dự án và chạy:
```bash
sqlite3 audit_mvp.db
```
Sau đó có thể chạy SQL trực tiếp.

## 4. Thao Tác CRUD Chuẩn (SQL Trực Tiếp)
### 4.1. Create
```sql
INSERT INTO audit_sessions (id, status, created_at, last_active_at)
VALUES ('ABC123', 'ACTIVE', datetime('now'), datetime('now'));
```

### 4.2. Read
```sql
SELECT * FROM audit_sessions WHERE id = 'ABC123';
```

### 4.3. Update
```sql
UPDATE audit_sessions
SET status = 'ARCHIVED'
WHERE id = 'ABC123';
```

### 4.4. Delete
```sql
DELETE FROM audit_sessions WHERE id = 'ABC123';
```

## 5. Tình Huống Thực Tế Thường Gặp
### 5.1. Tra cứu tất cả files của một session
```sql
SELECT f.*
FROM file_records f
JOIN document_bundles b ON b.id = f.bundle_id
WHERE b.session_id = 'ABC123';
```

### 5.2. Lọc findings theo stage
```sql
SELECT * FROM audit_findings
WHERE session_id = 'ABC123' AND stage = 'INTERIM';
```

### 5.3. Lấy EvidenceLink theo finding
```sql
SELECT * FROM evidence_links
WHERE finding_id = 'FND-0001';
```

### 5.4. Kiểm tra feedback và knowledge base
```sql
SELECT * FROM auditor_feedback ORDER BY created_at DESC;
SELECT * FROM knowledge_base_entries ORDER BY created_at DESC;
```

### 5.5. Xem execution plan của một phiên
```sql
SELECT * FROM execution_plans
WHERE audit_scope_id IN (
  SELECT id FROM audit_scopes WHERE session_id = 'ABC123'
);
```

## 6. Quản Lý Transaction Trong SQL GUI
- Với DB Browser: bấm “Write Changes” để commit.
- Với DBeaver: dùng nút “Commit” hoặc bật chế độ auto-commit.
- SQLite CLI: mỗi câu lệnh được commit ngay (nếu không dùng BEGIN/COMMIT).

## 7. Xử Lý Dữ Liệu JSON
Một số cột là JSON (ví dụ `tasks`, `objectives`, `applicable_stages`).
Trong SQLite, dữ liệu này lưu dưới dạng text JSON.

Ví dụ cập nhật `objectives`:
```sql
UPDATE audit_scopes
SET objectives = '["Objective 1", "Objective 2"]'
WHERE id = 'SCOPE-001';
```

## 8. Tình Huống Sửa Dữ Liệu An Toàn
### 8.1. Xóa dữ liệu test sai
```sql
DELETE FROM audit_findings WHERE session_id = 'ABC123';
```

### 8.2. Reset lại session
```sql
UPDATE audit_sessions
SET status = 'ACTIVE', last_active_at = datetime('now')
WHERE id = 'ABC123';
```

## 9. Sao Lưu và Phục Hồi
### 9.1. Sao lưu file DB
- Tắt backend.
- Copy file `audit_mvp.db` sang nơi khác.

### 9.2. Phục hồi
- Dừng backend.
- Thay file `audit_mvp.db` bằng bản sao lưu.

## 10. Kiểm Tra và Bảo Trì
- Kiểm tra dung lượng DB định kỳ.
- Dọn dữ liệu test sau khi chạy demo.
- Đảm bảo không mở file DB đồng thời bởi nhiều công cụ.
