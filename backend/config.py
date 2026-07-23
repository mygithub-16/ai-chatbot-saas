from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "development")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./chatbot_saas.db")
    admin_email: str = os.getenv("ADMIN_EMAIL", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    admin_token_secret: str = os.getenv("ADMIN_TOKEN_SECRET", os.getenv("ADMIN_DASHBOARD_SECRET", "change-this-in-production-secret-key-32chars"))
    admin_token_ttl_seconds: int = int(os.getenv("ADMIN_TOKEN_TTL_SECONDS", "86400"))
    allowed_origins: List[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173").split(",")
            if origin.strip()
        ]
    )
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

