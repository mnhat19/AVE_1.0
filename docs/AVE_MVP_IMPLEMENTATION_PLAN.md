# Ke hoach trien khai MVP AVE (Frontend + Backend)

## 1) Muc tieu MVP
- Co giao dien web day du cho quy trinh: tao session -> upload ho so -> chay audit -> xem ket qua -> tai file -> gui feedback.
- Ket noi truc tiep voi FastAPI backend, chay end-to-end tren localhost.
- Giao dien nhat quan voi thiet ke tu bo Stitch (control room, audit-grade) va co kha nang mo rong.

## 2) Hien trang (baseline)
- Backend FastAPI da co cac endpoint cho session, upload, run, findings, download, feedback.
- Pipeline audit end-to-end da hoat dong, co test data va test_pipeline.
- Bo giao dien Stitch da co 5 man hinh HTML (session setup, upload, audit engine, analysis dashboard, finding detail) + DESIGN.md cho he mau va typography.

## 3) Pham vi MVP
### Frontend
- App shell + navigation + wizard/stepper 4 buoc.
- Man hinh Session: tao session, luu session_id vao localStorage, copy session_id.
- Man hinh Upload: drag-drop, progress, danh sach file + validation report.
- Man hinh Run: chon stage, goi run, hien trang thai, thong bao loi.
- Man hinh Results: KPI cards, bang findings (filter/search), panel downloads, changelog.
- Feedback modal: action ACCEPT/REJECT/MODIFY + comment.
- Health indicator (goi /health, hien llm_provider).

### Backend
- On dinh API contracts, xu ly loi 400/404/413/500 ro rang.
- CORS cho frontend (neu can gioi han origin thi cau hinh theo .env).
- Bao dam output files co ten va duong dan on dinh de tai xuong.

## 4) Ke hoach trien khai theo pha

### Cap nhat thuc thi (May 6, 2026)
- Pha 0: Hoan thanh (frontend scaffold + tokens + layout + stepper + panel skeleton).
- Pha 1: Hoan thanh (session + upload flow, localStorage, drag-drop, validation view).
- Pha 2: Hoan thanh (run workflow, status, downloads, changelog, run summary KPIs).
- Pha 3: Hoan thanh (findings list, filter/search, feedback modal, feedback update).

### Pha 0 - Khoi tao frontend (1-2 ngay)
- Tao frontend React + Vite + TypeScript.
- Tao cau truc thu muc:
  - src/app (routing, layout)
  - src/components (ui, form, table, modal)
  - src/features (session, upload, run, results)
  - src/services (api client)
  - src/styles (tokens tu DESIGN.md)
- Dinh nghia design tokens (colors, typography, radius, spacing) theo DESIGN.md.
- Tao layout co sidebar + topbar, background grid, them fonts Sora + Source Sans 3.

Deliverables:
- App skeleton chay duoc, layout chuan, theme tokens trung khop.

Trang thai:
- Hoan thanh (frontend/ tao bo khung, style tokens, topbar/sidenav/stepper, panel skeleton).

### Pha 1 - Session + Upload (2-3 ngay)
- Implement tao session (POST /api/v1/sessions).
- Luu session_id vao localStorage, hien tren topbar, nut copy.
- Upload multi-file (POST /api/v1/sessions/{session_id}/upload):
  - drag-drop + file picker
  - progress state
  - danh sach file (ten, format, stage, status)
  - hien validation report neu co
- Xu ly loi (size_limit -> 413), thong bao ro rang.

Deliverables:
- Flow tao session va upload thanh cong, data hien thi dung.

Trang thai:
- Hoan thanh (UI session + upload da ket noi API, luu session_id, upload drag-drop, bao loi va validation report).

### Pha 2 - Run + Results tong quan (2-3 ngay)
- Man hinh Run: chon stage INTERIM/FIELDWORK/BOTH.
- Goi run (POST /api/v1/sessions/{session_id}/run) va hien trang thai:
  - loading, success, error
  - neu pipeline lau, hien spinner + message
- Results tong quan:
  - KPI cards (findings_count, anomalies_count, consolidated_count)
  - changelog (versioned_notes)
  - download panel (issue_log, risk_register, memo)

Deliverables:
- Co ket qua tong quan va tai file duoc.

Trang thai:
- Hoan thanh (run goi API, hien status + KPI + changelog + download links).

### Pha 3 - Findings + Feedback (2-3 ngay)
- Goi GET /api/v1/sessions/{session_id}/findings.
- Bang findings voi filter severity, status, search.
- Feedback modal:
  - POST /api/v1/findings/{finding_id}/feedback
  - cap nhat trang thai sau khi gui
- Man hinh detail (optional MVP): reuse layout tu finding_detail html.

Deliverables:
- Kiem toan vien co the gui feedback va xem danh sach findings.

Trang thai:
- Hoan thanh (bang findings + filter/search + feedback modal + cap nhat status).

### Pha 4 - Hoan thien + QA (1-2 ngay)
- Mobile-first tuning, accessibility (focus states, aria-labels).
- Mock data fallback khi API khong chay.
- Smoke test end-to-end tren localhost.
- Cap nhat README huong dan chay frontend.

Deliverables:
- MVP end-to-end chay duoc, tai file, feedback, UI on dinh.

Trang thai:
- Hoan thanh (accessibility aria-labels, mock mode fallback, smoke test tren frontend, README cap nhat).

## 5) Cong viec backend bo sung (neu can)
- Them CORS origin trong settings (cho frontend dev server).
- Them gioi han kich thuoc file va thong bao loi ro rang (da co 413).
- Dam bao idempotent cho /run neu can.
- Them thong tin progress neu muon real-time (websocket/long-poll) - khong bat buoc MVP.

## 6) Tieu chi nghiem thu MVP
- Tao session va upload thanh cong tren UI.
- Run audit thanh cong va hien counts.
- Download issue_log, risk_register, memo thanh cong.
- Feedback cap nhat trang thai finding.
- UI nhat quan voi DESIGN.md, hoat dong tot tren mobile.

## 7) Rui ro va giam thieu
- Pipeline chay lau -> hien loading/timeout giong y nghia.
- API loi 500 -> thong bao ro rang + huong dan kiem tra .env.
- File lon -> thong bao 413 va huong dan tach nho.

## 8) Backlog sau MVP
- Streaming logs cho buoc Run.
- Evidence link detail theo page/sheet/row.
- Auth + role-based access.
- Audit report export da dinh dang theo template firm.
