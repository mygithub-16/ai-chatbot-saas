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
            db.commit()
            db.refresh(user)
        else:
            user.is_admin = True
            if not user.password_hash:
                user.password_hash = hash_password(password)
            db.commit()

        # Ensure admin user has an associated Business profile
        business = db.query(Business).filter(Business.owner_id == user.id).first()
        if not business:
            business = Business(
                owner_id=user.id,
                name="ECHURA Admin Business",
                business_name="ECHURA Admin",
                business_description="System operator and master dashboard administrator.",
                services_products="AI chatbot SaaS platform administration.",
                faqs="How to manage client bots? Use operator dashboard.",
                policies="Master admin access.",
                tone_style="professional",
                personality_prompt="Master system administrator assistant.",
                plan="scale",
                subscription_status="active",
            )
            db.add(business)
            db.commit()
    finally:
        db.close()


def main() -> None:
    init_db()
    seed_admin()


if __name__ == "__main__":
    main()

