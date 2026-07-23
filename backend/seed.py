from __future__ import annotations

import os

from dotenv import load_dotenv

from backend.auth import hash_password
from backend.db import SessionLocal, init_db
from backend.models import Business, User

load_dotenv()


def seed_admin() -> None:
    email = os.getenv("ADMIN_EMAIL", "admin@example.com").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    if not email or not password:
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                auth_provider="local",
                business_name="ECHURA Admin",
                is_admin=True,
            )
            db.add(user)
        else:
            user.is_admin = True
            if not user.password_hash:
                user.password_hash = hash_password(password)
        db.commit()
    finally:
        db.close()


def main() -> None:
    init_db()
    seed_admin()


if __name__ == "__main__":
    main()

