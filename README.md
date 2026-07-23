# ECHURA AI Chatbot SaaS

Recovered and rebuilt FastAPI + React SaaS prototype for business chatbots.

## Features

- Business profile setup with tone, policies, FAQs, and service context.
- Demo chatbot endpoint with workflow memory for bookings and inquiries.
- Admin login with bearer-token protected analytics.
- Funnel, lead, activity, and business performance dashboard.
- SQLite by default, configurable with `DATABASE_URL`.

## Run

```powershell
cd backend
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --reload
```

For the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env` to enable admin login.
