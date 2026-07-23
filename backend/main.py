from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    HAS_SLOWAPI = True
except ImportError:
    HAS_SLOWAPI = False

from backend.config import get_settings
from backend.db import init_db
from backend.seed import seed_admin

from backend.routers.auth import router as auth_router
from backend.routers.client import router as client_router
from backend.routers.widget import router as widget_router
from backend.routers.admin import router as admin_router
from backend.routers.billing import router as billing_router
from backend.routers.prompt import router as prompt_router

settings = get_settings()

app = FastAPI(
    title="ECHURA AI Chatbot SaaS",
    description="Production-grade AI Chatbot SaaS Platform",
    version="1.0.0",
)

if HAS_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Secure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Secret-Token", "X-User-Id"],
)

# Register Modular Routers
app.include_router(auth_router)
app.include_router(client_router)
app.include_router(widget_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(prompt_router)

FRONTEND_ROOT = Path("frontend")
FRONTEND_DIST = FRONTEND_ROOT / "dist"

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    try:
        seed_admin()
    except Exception as exc:
        print(f"Startup admin check: {exc}")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    # Allow API and widget routes to pass through if unmatched
    if full_path.startswith(("api/", "auth/", "widget/", "admin/")):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    dist_file = FRONTEND_DIST / full_path
    if dist_file.exists() and dist_file.is_file():
        return FileResponse(dist_file)

    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.exists():
        return FileResponse(dist_index)

    return JSONResponse({"status": "ok", "message": "ECHURA AI Chatbot SaaS API Server Ready"})
