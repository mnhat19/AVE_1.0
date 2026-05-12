# AVE MVP Frontend

This is the frontend application for the AI Audit Tool MVP, built with React, TypeScript, and Vite.

## Features
- **Session Management**: Initialize or load audit sessions.
- **Document Upload**: Drag & drop upload for audit evidence and files.
- **Audit Execution**: Trigger the multi-agent backend pipeline (Interim, Fieldwork, or Both).
- **Results Dashboard**: View findings, anomalies, and download generated artifacts (Issue Log, Risk Register, Audit Memo).
- **Feedback Loop**: Provide ACCEPT/REJECT/MODIFY feedback with corrected values.
- **Mock Mode**: Built-in mock data fallback when the backend is unavailable or during UI development.

## Requirements
- Node.js 18+
- npm or yarn

## Setup & Running Locally

1. Install dependencies:
```bash
npm install
```

2. Configure environment (optional):
Create a `.env.local` file in the `frontend` directory:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_MOCK_MODE=false
```

3. Do not commit frontend environment files: `.env.local` and other local env files are for developer use only.

3. Start the development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

5. Run lint checks:
```bash
npm run lint
```

## Mock Mode
If the backend API is not running, the application will automatically fallback to **Mock Mode** in development. It provides simulated API responses so you can test the UI workflows end-to-end without needing a database or LLM provider.

You can force mock mode on/off by setting `VITE_MOCK_MODE=true` in `.env.local`.

## Design & Accessibility
- The interface adheres to the AuditControl AI design system.
- Components are fully responsive (Mobile-first).
- WAI-ARIA labels are included for accessibility compliance.
