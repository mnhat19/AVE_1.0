# AVE Audit Control Hub

AVE_1.2 là nền tảng hỗ trợ kiểm toán bằng AI, tập trung vào thu thập bằng chứng, trích xuất tài liệu, phân tích rủi ro và tạo báo cáo.
Nó bao gồm backend FastAPI, frontend React + Vite, công cụ tạo dữ liệu mẫu và các script kiểm thử đầu-cuối.

## Tính năng chính
- Quản lý phiên kiểm toán
- Upload tài liệu nhiều định dạng
- Chạy pipeline phân tích kiểm toán (INTERIM, FIELDWORK, BOTH)
- Xuất báo cáo: Issue Log, Risk Register, Audit Memo
- Chế độ Mock khi backend chưa chạy

## Yêu cầu
- Python 3.11+
- Node.js 18+ và npm
- Tesseract OCR (tùy chọn cho ảnh scan)
- `pypff` nếu muốn xử lý tệp PST

## Cài đặt
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Cấu hình
Sao chép tệp môi trường mẫu và sửa giá trị:
```bash
copy .env.example .env
```

Thiết lập:
- `LLM_PROVIDER=groq|mistral|ollama`
- `GROQ_API_KEY` khi dùng `groq`
- `MISTRAL_API_KEY` khi dùng `mistral`

## Chạy backend
```bash
uvicorn main:app --reload --port 8000
```

## Chạy frontend
```bash
cd frontend
npm install
npm run dev
```

Mở `http://localhost:5173` để truy cập giao diện.

## Luồng sử dụng
1. Khởi động backend và frontend.
2. Tạo phiên kiểm toán mới.
3. Upload tài liệu từ `sample_audit_documents/INTERIM` và `sample_audit_documents/FIELDWORK`.
4. Chọn giai đoạn `INTERIM`, `FIELDWORK` hoặc `BOTH`.
5. Chạy audit và xem kết quả.
6. Tải xuống báo cáo phát hiện và rủi ro.

## Tạo dữ liệu mẫu
```bash
python generate_real_documents_complete.py
```

## Kiểm thử CLI
```bash
python test_pipeline.py
```

## Lưu ý GitHub
Các tệp sau không nên đẩy lên GitHub:
- `.venv/`, `outputs/`, `uploads/`
- `.env`, `.env.*`, `frontend/.env.local`
- `*.log`, `*.db`, `*.sqlite`, `*.pyc`
- `node_modules/`, `frontend/node_modules/`
