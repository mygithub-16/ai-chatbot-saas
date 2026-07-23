from __future__ import annotations

import os
import time
import json
import base64
import hmac
import hashlib
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.auth import hash_password, verify_password, create_access_token, get_request_user
from backend.config import get_settings
from backend.models import User, Business, Event

router = APIRouter(tags=["Authentication"])
settings = get_settings()


class LoginRegisterPayload(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


def _admin_secret() -> str:
    return settings.admin_token_secret


def _admin_login_credentials() -> Tuple[str, str]:
    return settings.admin_email.strip().lower(), settings.admin_password


def issue_admin_token(email: str) -> str:
    payload = {
        "email": email.strip().lower(),
        "issued_at": int(time.time()),
    }
    payload_blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(_admin_secret().encode(), payload_blob.encode(), hashlib.sha256).hexdigest()
    token_body = base64.urlsafe_b64encode(payload_blob.encode()).decode().rstrip("=")
    return f"{token_body}.{signature}"


def validate_admin_token(token: str) -> Dict[str, Any]:
    token = (token or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required")

    try:
        token_body, signature = token.split(".", 1)
        padding = "=" * (-len(token_body) % 4)
        payload_blob = base64.urlsafe_b64decode(f"{token_body}{padding}".encode()).decode()
        expected_signature = hmac.new(_admin_secret().encode(), payload_blob.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid admin signature")

        payload = json.loads(payload_blob)
        issued_at = int(payload.get("issued_at", 0))
        if int(time.time()) - issued_at > settings.admin_token_ttl_seconds:
            raise ValueError("Admin token expired")

        admin_email, _ = _admin_login_credentials()
        payload_email = str(payload.get("email", "")).strip().lower()
        if admin_email and payload_email != admin_email:
            raise ValueError("Admin token does not match configured admin")

        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token") from exc


@router.post("/auth/register")
@router.post("/api/auth/register")
def register(payload: LoginRegisterPayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Secure production registration with automatic clean business setup."""
    email_clean = payload.email.strip().lower()
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    user = User(
        email=email_clean,
        password_hash=hash_password(payload.password),
        auth_provider="local",
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Automatically set up default business chatbot for user
    business_name = "My Business Chatbot"
    business = Business(
        owner_id=user.id,
        name=business_name,
        business_name=business_name,
        business_description="A helpful business virtual receptionist.",
        services_products="General inquiries, appointment scheduling, customer support.",
        faqs="What hours are you open? We are available online 24/7.\nDo you offer consultations? Yes, contact us for a quote.",
        policies="Please cancel at least 24 hours in advance.",
        tone_style="friendly and professional",
        personality_prompt="You are a warm, helpful receptionist. Assist visitors with services and bookings.",
        plan="starter",
        subscription_status="trial",
    )
    db.add(business)
    db.commit()
    db.refresh(business)

    # Record event
    event = Event(
        event_name="business_created",
        timestamp=user.created_at,
        session_id=f"business-{business.id}",
        user_id=user.id,
        business_id=business.id,
        metadata_json={"source": "client_register", "business_name": business.business_name},
    )
    db.add(event)
    db.commit()
    
    token = create_access_token(data={"sub": str(user.id)})
    return {
        "ok": True, 
        "access_token": token, 
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email},
        "business": {"id": business.id, "name": business.name}
    }


@router.post("/auth/login")
@router.post("/api/auth/login")
def login(payload: LoginRegisterPayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Secure production login verifying password."""
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        
    business = db.query(Business).filter(Business.owner_id == user.id).first()
    token = create_access_token(data={"sub": str(user.id)})
    return {
        "ok": True, 
        "access_token": token, 
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "is_admin": user.is_admin},
        "business": {
            "id": business.id if business else None,
            "name": business.name if business else None,
            "business_name": business.business_name if business else None,
        } if business else None
    }


@router.post("/admin/auth/login")
def admin_login(payload: LoginRegisterPayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
    configured_email, configured_password = _admin_login_credentials()
    submitted_email = payload.email.strip().lower()

    if configured_email and configured_password:
        if submitted_email != configured_email or payload.password != configured_password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")
        token = issue_admin_token(submitted_email)
        return {"access_token": token, "token_type": "bearer", "admin": {"email": submitted_email}}

    admin_user = db.query(User).filter(User.email == submitted_email, User.is_admin.is_(True)).first()
    if not admin_user or not verify_password(payload.password, admin_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")

    token = issue_admin_token(admin_user.email)
    return {"access_token": token, "token_type": "bearer", "admin": {"email": admin_user.email}}


@router.get("/api/auth/me")
def get_current_user_info(user: User = Depends(get_request_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    business = db.query(Business).filter(Business.owner_id == user.id).first()
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
            "business_name": user.business_name,
        },
        "business": {
            "id": business.id,
            "name": business.name,
            "business_name": business.business_name,
            "plan": business.plan,
            "subscription_status": business.subscription_status,
        } if business else None,
    }
