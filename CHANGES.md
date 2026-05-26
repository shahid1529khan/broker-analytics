# Changes from Original AI Studio Export

## Critical fixes (would prevent the app from running)

### `yield-platform/backend/services/pdf_parser.py`
- Changed `model="claude-3-5-sonnet-20241022"` → `model="claude-sonnet-4-5"` (outdated model string)

### `server.ts` → DELETED
- Was an AI Studio Gemini scaffold file with mock API routes, Gemini API calls, and fake analytics data
- Completely incompatible with this project's FastAPI backend architecture
- Deleted entirely

### `package.json`
- Removed `server.ts`-dependent scripts (`dev: tsx server.ts`, `build: esbuild server.ts ...`)
- Replaced with clean Vite SPA scripts (`dev: vite`, `build: vite build`)
- Removed server.ts dependencies: `express`, `@google/genai`, `pdfkit`, `xlsx`, `http-proxy-middleware`, `tsx`, `esbuild`, `concurrently`
- Kept only frontend dependencies: React, Recharts, Supabase, Lucide, Tailwind, React Router

### `vite.config.ts`
- Removed AI Studio HMR/file-watching override comments
- Added Vite dev server proxy: `/api` → `http://localhost:8000` (routes frontend API calls to FastAPI during local dev)

## Important fixes (would cause bugs or data errors)

### `yield-platform/backend/db/models.py`
- Changed `file_path: str` → `file_path: Optional[str] = None` in `StatementUploadBase`
- The uploads route already sets `file_path = None` when Supabase Storage isn't configured; model now matches

### `yield-platform/backend/requirements.txt`
- Added `email-validator>=2.1.0` (required by Pydantic `EmailStr` — app crashes on startup without it)
- Added version pins to all dependencies for reproducible installs

### `src/api/client.ts`
- Improved error logging to show HTTP status code and response body (was only logging `statusText`)
- Updated `API_BASE_URL` default to `/api` (works with Vite proxy, no hardcoded localhost port)
- Added inline comment explaining FormData Content-Type behaviour

## New files added

### `src/.env.example`
- Documents `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL` with instructions

### `README.md`
- Complete setup guide: Supabase schema, backend startup, frontend startup, first user setup, production deployment

### `CHANGES.md`
- This file
