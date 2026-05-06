Thiet ke mot web app "AI Audit Tool" danh cho kiem toan vien, ket noi backend FastAPI va tap trung vao quy trinh: tao session -> upload ho so -> chay audit -> xem ket qua -> tai file -> gui feedback. Vibe: professional, trustworthy, audit-grade, tinh gon nhung manh me, cam giac "control room" nhe. Mobile-first, accessible (WCAG), thao tac ro rang, feedback nhanh.

Yeu cau UI/UX:
- Bo cuc theo wizard/stepper (4 buoc): Session, Upload, Run, Results.
- Top bar co Health indicator (OK/Warning), base URL, va Session ID + nut copy.
- Section Upload co drag-drop, progress, danh sach file (ten, format, stage, status), hien validation report neu co.
- Section Run co chon stage (INTERIM, FIELDWORK, BOTH), nut Run, trang thai dang xu ly, thong bao loi.
- Results co KPI cards (findings_count, anomalies_count, consolidated_count), bang Findings (filter severity, status, search), panel Downloads (issue_log, risk_register, memo), va Timeline/Changelog.
- Feedback modal cho moi finding (action: ACCEPT/REJECT/MODIFY, comment).
- Thiet ke bang, chips, badges, empty state, error state.

Thong tin backend (base URL: http://localhost:8000):
1) GET /health -> { status, llm_provider }
2) GET /api/v1/ping -> { status: "ok" }
3) POST /api/v1/sessions -> { session_id, status }
4) POST /api/v1/sessions/{session_id}/upload (multipart: files[], optional bundle_id form field)
   Response: { session_id, files: [{file_id, filename, format, stage, status}], validation }
5) POST /api/v1/sessions/{session_id}/run (form field: stage, default BOTH)
   Response: { session_id, stage, findings_count, anomalies_count, consolidated_count, output_paths, changelog, audit_tasks, execution_plan }
6) GET /api/v1/sessions/{session_id}/findings -> [{ id, stage, description, severity, status, confidence_score }]
7) GET /api/v1/sessions/{session_id}/download/{file_type}
   file_type: issue_log | memo | risk_register
8) POST /api/v1/findings/{finding_id}/feedback (form fields: action, comment)
   action: ACCEPT | REJECT | MODIFY

Yeu cau ky thuat:
- Tao frontend bang React + Vite + TypeScript (clean structure), CSS Modules hoac Tailwind (chon 1, nhung code sach va de mo rong).
- Su dung fetch/axios voi baseURL config, tach service layer (api.ts) va hooks (useSession, useUpload, useRun, useFindings).
- Xu ly loi HTTP 400/404/413/500 ro rang, hien toast va inline error.
- Luu session_id vao localStorage de reload khong mat.
- Cac form co validation nhe (session_id ton tai, chon stage truoc khi run, it nhat 1 file).

Yeu cau thiet ke chi tiet:
- Typography: heading font "Sora" hoac "Space Grotesk"; body font "Source Sans 3". Tranh Inter/Roboto/Arial.
- Color system: nen gradient xam nhat + xanh teal/emerald lam accent; khong dung tim. Dinh nghia CSS variables.
- Background: co pattern nhe (grid/line/blur shape).
- Motion: page-load fade + staggered reveal cho cards; hover micro-contrast cho buttons.

Output mong muon:
- Tra ve code hoan chinh (HTML/CSS/JS) theo React + Vite + TS, co README nho cach run.
- Bao gom mock data fallback neu API chua chay, de demo UI.
- Bao dam mobile-first, accessibility (aria-label, focus states).