# ECHURA AI Chatbot SaaS — Production Deployment Guide

> **Last Updated:** July 2026  
> **Tech Stack:** FastAPI · SQLAlchemy · React (Vite) · OpenAI GPT · Docker

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Database Decision — SQLite vs PostgreSQL](#2-database-decision--sqlite-vs-postgresql)
3. [Pre-Deployment Checklist](#3-pre-deployment-checklist)
4. [Environment Variables (Full Reference)](#4-environment-variables-full-reference)
5. [Step-by-Step Deployment on Render](#5-step-by-step-deployment-on-render)
6. [Alternative Deployment Platforms](#6-alternative-deployment-platforms)
7. [Custom Domain Setup](#7-custom-domain-setup)
8. [Post-Deployment Verification](#8-post-deployment-verification)
9. [Upgrading to PostgreSQL (When to Switch)](#9-upgrading-to-postgresql-when-to-switch)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Browser / Embedded Widget                              │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend  (backend/main.py)                     │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────────┐   │
│  │ Auth Router │  │ Widget   │  │ Admin / Analytics│   │
│  │ /auth/*     │  │ /api/    │  │ /admin/*         │   │
│  │ /api/auth/* │  │ widget/* │  │ /analytics/*     │   │
│  └─────────────┘  └──────────┘  └─────────────────┘   │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────────┐   │
│  │ Client Dash │  │ Billing  │  │ Prompt Architect │   │
│  │ /api/client │  │ Paystack │  │ /api/refine-*    │   │
│  └─────────────┘  └──────────┘  └─────────────────┘   │
│  Uvicorn ASGI · Rate Limited (slowapi) · CORS Guarded  │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┴───────────────┐
          ▼                              ▼
  ┌───────────────┐            ┌──────────────────┐
  │ SQLite / PG   │            │ OpenAI GPT API   │
  │ chatbot_saas.db│           │ (gpt-4o-mini)    │
  └───────────────┘            └──────────────────┘
```

- **Frontend**: React/Vite SPA served as static files from `frontend/dist/` by FastAPI
- **Backend**: FastAPI monolith with modular APIRouters in `backend/routers/`
- **Database**: SQLAlchemy ORM — works with **SQLite** (default) or **PostgreSQL** (production recommended)
- **AI**: OpenAI Chat Completions API called directly per message — no hardcoded responses

---

## 2. Database Decision — SQLite vs PostgreSQL

### ✅ Start with SQLite (Default — No Setup Required)

The app ships configured for SQLite out of the box.

```env
DATABASE_URL=sqlite:///./chatbot_saas.db
```

**Use SQLite when:**
- You are deploying to a **single container / single server** instance
- You are in early stage (< 50 active tenants)
- Your hosting provider offers **persistent disk storage** (Render, Fly.io, DigitalOcean Droplet, VPS)

> **Critical**: If you deploy to Render's free tier or any **ephemeral filesystem** host, the SQLite file will be **wiped on every redeploy**. You must either attach a **persistent disk** (Render) or migrate to PostgreSQL.

---

### 🚀 Upgrade to PostgreSQL (Recommended for Scale)

Switch by updating one environment variable — no code changes needed:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

**Use PostgreSQL when:**
- You expect more than ~50 active paying tenants
- You plan to run multiple server instances (horizontal scaling)
- You are deploying to Render (free tier / any serverless host)
- You want better concurrent write performance and connection pooling

**Recommended providers:**
| Provider | Free Tier | Notes |
| :--- | :--- | :--- |
| [Supabase](https://supabase.com) | ✅ Yes | PostgreSQL · generous free quota |
| [Neon](https://neon.tech) | ✅ Yes | Serverless PostgreSQL · great for Render |
| Render Postgres | Partial | Paid plan, native Render integration |
| Railway | ✅ Yes | Easy setup with Railway deployments |

**Required extra package (already in requirements.txt once you switch):**
```
psycopg2-binary
```
Add this to `backend/requirements.txt` before deploying with PostgreSQL.

---

## 3. Pre-Deployment Checklist

Complete every item before going live:

### Code & Build
- [ ] Run `npm --prefix frontend run build` — confirms React bundle builds cleanly to `frontend/dist/`
- [ ] Run `python -m py_compile backend/main.py` — confirms no Python syntax errors
- [ ] Confirm `.env` is in `.gitignore` (it is — never commit secrets)

### API Keys (Required)
- [ ] `OPENAI_API_KEY` — Get from [platform.openai.com](https://platform.openai.com)
- [ ] Set billing limit on OpenAI to avoid unexpected charges

### Admin Setup
- [ ] Set a strong `ADMIN_EMAIL` and `ADMIN_PASSWORD`
- [ ] Generate a secure random `ADMIN_TOKEN_SECRET` (minimum 32 chars):
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] Generate a secure `ADMIN_DASHBOARD_SECRET` the same way

### Security
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com`
- [ ] Never use `ALLOWED_ORIGINS=*` in production

### Optional Services
- [ ] `PAYSTACK_SECRET_KEY` — for live billing (from [paystack.com](https://paystack.com))
- [ ] `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — for Google Calendar sync

---

## 4. Environment Variables (Full Reference)

Copy this into your hosting provider's environment settings:

```env
# ── Application ──────────────────────────────────────
ENVIRONMENT=production

# ── Database ─────────────────────────────────────────
# Option A: SQLite (single-server with persistent disk)
DATABASE_URL=sqlite:///./chatbot_saas.db

# Option B: PostgreSQL (recommended for production scale)
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# ── AI Engine ────────────────────────────────────────
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini

# Optionally enable additional AI providers
# ANTHROPIC_API_KEY=sk-ant-...
# GEMINI_API_KEY=AI...

# ── Admin Authentication ─────────────────────────────
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your-very-strong-password
ADMIN_TOKEN_SECRET=generate-32-char-random-hex-here
ADMIN_DASHBOARD_SECRET=generate-another-32-char-random-hex
ADMIN_TOKEN_TTL_SECONDS=86400

# ── CORS & Rate Limiting ─────────────────────────────
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
RATE_LIMIT_PER_MINUTE=60

# ── Payment Gateway (Paystack) ───────────────────────
PAYSTACK_SECRET_KEY=sk_live_...

# ── Google Calendar OAuth ────────────────────────────
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google-calendar/callback
```

---

## 5. Step-by-Step Deployment on Render

Render is the recommended platform because the existing `render.yaml` is pre-configured.

### Step 1 — Push to GitHub
```bash
git add .
git commit -m "Production-ready ECHURA SaaS"
git push origin main
```

### Step 2 — Create a New Render Service
1. Go to [render.com](https://render.com) → **New** → **Blueprint**
2. Connect your GitHub repository
3. Render detects `render.yaml` automatically and creates the Docker service

### Step 3 — Set Environment Variables
In Render Dashboard → your service → **Environment**:
- Add every variable from Section 4 above
- Use **Secret** type for API keys and tokens

### Step 4 — Attach Persistent Disk (If using SQLite)
In Render Dashboard → your service → **Disks** → **Add Disk**:
- **Mount path**: `/app/data`
- **Size**: 1 GB (free tier)

Then update your environment variable:
```env
DATABASE_URL=sqlite:////app/data/chatbot_saas.db
```

> If using PostgreSQL instead, create a **Render Postgres** database or use Neon/Supabase — skip this step.

### Step 5 — Trigger Deploy
Click **Manual Deploy** → **Deploy Latest Commit**

Monitor the logs. A successful startup looks like:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 6 — Verify Health Check
```
https://your-app.onrender.com/health
```
Expected response: `{"status": "ok", "environment": "production"}`

---

## 6. Alternative Deployment Platforms

### Railway
1. Install Railway CLI: `npm i -g @railway/cli`
2. `railway login && railway init && railway up`
3. Add environment variables via Railway dashboard
4. Railway auto-detects `Dockerfile`

### Fly.io
```bash
fly auth login
fly launch --name echura-saas
fly secrets set OPENAI_API_KEY=sk-proj-... ADMIN_TOKEN_SECRET=...
fly deploy
```

### DigitalOcean App Platform
1. Create new App → select GitHub repo
2. Choose **Docker** source
3. Set environment variables in the App spec
4. DigitalOcean builds the multi-stage `Dockerfile` automatically

### VPS (Ubuntu/Debian — Manual)
```bash
# On your server:
git clone https://github.com/yourname/ai-chatbot-saas.git
cd ai-chatbot-saas

# Build frontend
npm --prefix frontend install && npm --prefix frontend run build

# Install Python deps
pip install -r backend/requirements.txt

# Run with Gunicorn + Uvicorn workers
gunicorn backend.main:app -k uvicorn.workers.UvicornWorker -w 2 --bind 0.0.0.0:8000
```

Use **Nginx** as a reverse proxy in front of port 8000 and **Certbot** for free SSL.

---

## 7. Custom Domain Setup

### Step 1 — Add Domain in Render
Render Dashboard → your service → **Custom Domains** → **Add Custom Domain**
- Enter: `yourdomain.com` and `www.yourdomain.com`
- Render provides DNS values (CNAME / A records)

### Step 2 — Update DNS Records
Log into your domain registrar (Namecheap, GoDaddy, Cloudflare, etc.):

| Type | Name | Value |
| :--- | :--- | :--- |
| `CNAME` | `www` | `your-service.onrender.com` |
| `ALIAS` or `A` | `@` (root) | IP provided by Render |

DNS propagation takes 5–30 minutes. SSL certificate is issued automatically.

### Step 3 — Update ALLOWED_ORIGINS
```env
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Step 4 — Update Google OAuth Redirect URI (if using Calendar)
```env
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google-calendar/callback
```
Also update the redirect URI in your [Google Cloud Console](https://console.cloud.google.com).

---

## 8. Post-Deployment Verification

Run through this checklist after every deployment:

```
[ ] GET  /health               → {"status":"ok","environment":"production"}
[ ] POST /auth/register        → Creates new user + business, returns JWT token
[ ] POST /auth/login           → Returns JWT token
[ ] GET  /api/client/business  → Returns business profile (with JWT)
[ ] POST /api/widget/chat      → Returns GPT-generated reply (not hardcoded)
[ ] GET  /widget/embed.js      → Returns JavaScript widget embed script
[ ] GET  /widget/{id}          → Returns chat iframe HTML page
[ ] POST /admin/auth/login     → Returns admin bearer token
[ ] GET  /admin/businesses     → Returns list of tenants (with admin token)
[ ] GET  /analytics/overview   → Returns platform metrics (with admin token)
```

---

## 9. Upgrading to PostgreSQL (When to Switch)

The app is fully PostgreSQL-ready via SQLAlchemy. Switching requires:

### Step 1 — Add psycopg2 dependency
```
# backend/requirements.txt
psycopg2-binary
```

### Step 2 — Update DATABASE_URL
```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

### Step 3 — Migrate existing SQLite data (if needed)
Use `pgloader` to migrate your existing SQLite database to PostgreSQL:
```bash
pgloader sqlite:///chatbot_saas.db postgresql://user:password@host/dbname
```

### Step 4 — Redeploy
The `init_db()` function in `backend/db.py` calls `Base.metadata.create_all()` which automatically creates all tables on first run against any database engine.

> No Alembic migrations are required for a fresh PostgreSQL deployment — the schema is fully managed by SQLAlchemy's `create_all`.

---

## Quick Reference

| Command | Purpose |
| :--- | :--- |
| `npm --prefix frontend run build` | Build React production bundle |
| `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` | Run production server |
| `python backend/seed.py` | Create admin user from env vars |
| `python -c "import secrets; print(secrets.token_hex(32))"` | Generate secure random secret |
| `curl https://yourdomain.com/health` | Verify deployment is live |
