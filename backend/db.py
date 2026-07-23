from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot_saas.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def _sqlite_path() -> Path | None:
    if not DATABASE_URL.startswith("sqlite:///"):
        return None
    return Path(DATABASE_URL.replace("sqlite:///", "", 1))


def _ensure_sqlite_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    table_columns = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in existing_tables
    }
    additions = {
        "users": {
            "password_hash": "TEXT",
            "business_name": "VARCHAR(255)",
            "auth_provider": "VARCHAR(64) DEFAULT 'local'",
            "is_admin": "BOOLEAN DEFAULT 0",
            "calendar_token": "TEXT",
            "calendar_id": "VARCHAR(255)",
            "created_at": "DATETIME",
        },
        "businesses": {
            "business_name": "VARCHAR(255)",
            "business_description": "TEXT",  
            "services_products": "TEXT",
            "faqs": "TEXT",
            "policies": "TEXT",
            "tone_style": "VARCHAR(128)",
            "personality_prompt": "TEXT",
            "lead_capture_enabled": "BOOLEAN DEFAULT 1",
            "plan": "VARCHAR(64)",
            "subscription_status": "VARCHAR(64)",
            "address": "VARCHAR(512)",
            "lat_long": "VARCHAR(128)",
            "created_at": "DATETIME",
        },
        "events": {"metadata_json": "JSON", "timestamp": "DATETIME"},
        "conversation_sessions": {
            "workflow_state_json": "JSON",
            "slots_json": "JSON",
            "missing_slots_json": "JSON",
            "history_json": "JSON",
            "intent": "VARCHAR(128)",
            "status": "VARCHAR(64)",
        },
        "leads": {
            "buying_probability": "INTEGER DEFAULT 0",
            "urgency_score": "INTEGER DEFAULT 0",
            "source": "VARCHAR(64)",
            "status": "VARCHAR(64)",
            "metadata_json": "JSON",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in additions.items():
            if table_name not in table_columns:
                continue
            for column_name, column_type in columns.items():
                if column_name not in table_columns[table_name]:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def init_db() -> None:
    from backend import models  # noqa: F401

    sqlite_path = _sqlite_path()
    if sqlite_path and sqlite_path.parent != Path("."):
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
