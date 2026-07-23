from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from pathlib import Path


def health_snapshot() -> dict:
    return {
        "ok": True,
        "service": "ai-chatbot-saas",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "database_url": redact_secret(os.getenv("DATABASE_URL", "sqlite:///./chatbot_saas.db")),
    }


def project_paths() -> dict:
    root = Path(__file__).resolve().parents[1]
    return {
        "root": str(root),
        "frontend": str(root / "frontend"),
        "database": str(root / "chatbot_saas.db"),
    }


def redact_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"
