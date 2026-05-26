# Yield Platform — AI-Powered Commission Statement Analysis

A full-stack web application for Yield Business Brokers to ingest, normalise, and analyse mortgage broker commission statements.

## Architecture

- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Recharts
- **Backend**: Python FastAPI + Supabase (PostgreSQL) + Anthropic Claude API
- **Auth**: Supabase Auth (JWT passed to FastAPI on every request)
- **Storage**: Supabase Storage (bucket: `statements`)

---

## Setup: Database (Supabase)

1. Create a new project at https://supabase.com
2. Go to **SQL Editor** and run the full contents of `yield-platform/backend/supabase/schema.sql`
3. Go to **Storage** → create a bucket named `statements` (set to private)
4. Go to **Project Settings → API** and copy your Project URL, anon key, and service role key

Seed at least one aggregator before uploading statements:
```sql
INSERT INTO public.aggregators (name) VALUES ('Connective'), ('AFG'), ('FAST'), ('Finsure');
```

---

## Setup: Backend (FastAPI)

```bash
cd yield-platform/backend
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ANTHROPIC_API_KEY in .env

pip install -r requirements.txt
uvicorn backend.main:app --reload
# Runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## Setup: Frontend (React)

```bash
# From the project root (where package.json is)
cp .env.example .env.local
# Fill in VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.local
# Leave VITE_API_URL commented out — Vite proxy forwards /api to localhost:8000

npm install
npm run dev
# Runs on http://localhost:5173
```

---

## First User Setup

After running the schema, you need to create your first user record manually.

1. Sign up via the Login page (this creates a Supabase Auth user)
2. Create an organisation record in Supabase:
```sql
INSERT INTO public.organisations (name) VALUES ('Yield Business Brokers');
```
3. Link your auth user to the organisation:
```sql
INSERT INTO public.users (auth_id, email, organisation_id)
VALUES (
  '<your-auth-user-id-from-supabase-auth-users>',
  'your@email.com',
  (SELECT id FROM public.organisations WHERE name = 'Yield Business Brokers')
);
```

---

## Production Deployment

- **Backend**: Deploy to [Railway](https://railway.app) — set env vars in Railway dashboard, set `ALLOWED_ORIGINS` to your Vercel frontend URL
- **Frontend**: Deploy to [Vercel](https://vercel.com) — set `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and `VITE_API_URL` (your Railway backend URL) in Vercel env vars

---
