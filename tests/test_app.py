from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db import init_db, SessionLocal
from backend.models import User, Business, Lead, Event, ConversationSession
from backend.calendar_service import create_calendar_event
from backend.billing import get_plan, initialize_paystack_transaction
from backend.prompt_architect import architect

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    db = SessionLocal()
    try:
        # Seed test admin & test business
        admin_email = "testadmin@example.com"
        user = db.query(User).filter(User.email == admin_email).first()
        if not user:
            user = User(
                email=admin_email,
                password_hash="pbkdf2_sha256$120000$salt$hash",
                auth_provider="local",
                business_name="Test Business",
                is_admin=True,
                calendar_token='{"token": "mock-access-token", "refresh_token": "mock-refresh-token"}',
                calendar_id="primary",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        business = db.query(Business).filter(Business.owner_id == user.id).first()
        if not business:
            business = Business(
                owner_id=user.id,
                name="Test Spa",
                business_name="Test Spa & Salon",
                business_description="Premium spa services",
                services_products="Massage, Facial, Manicure",
                faqs="Open 9am-6pm daily",
                policies="Strict 24h cancellation",
                tone_style="friendly and professional",
                plan="starter",
                subscription_status="active",
            )
            db.add(business)
            db.commit()
    finally:
        db.close()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_user_registration_and_login():
    reg_email = "newuser@example.com"
    db = SessionLocal()
    db.query(User).filter(User.email == reg_email).delete()
    db.commit()
    db.close()

    reg_res = client.post("/api/auth/register", json={"email": reg_email, "password": "password123"})
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert reg_data["ok"] is True
    assert "access_token" in reg_data
    token = reg_data["access_token"]

    # Test me endpoint
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["email"] == reg_email

    # Test login endpoint
    login_res = client.post("/api/auth/login", json={"email": reg_email, "password": "password123"})
    assert login_res.status_code == 200
    assert login_res.json()["ok"] is True


def test_widget_chat_flow():
    # Test widget iframe HTML page
    iframe_res = client.get("/widget/1")
    assert iframe_res.status_code == 200
    assert "text/html" in iframe_res.headers["content-type"]

    # Test widget chat turn
    session_id = "test-session-123"
    chat_payload = {
        "message": "Hi, I'd like to book a Massage tomorrow at 2pm. My name is Alex, phone 555-0199",
        "session_id": session_id,
        "business_id": 1,
    }
    chat_res = client.post("/api/widget/chat", json=chat_payload)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["ok"] is True
    assert "response" in chat_data


def test_google_calendar_oauth_and_mock_event():
    # Login as testadmin to get token
    db = SessionLocal()
    user = db.query(User).filter(User.email == "testadmin@example.com").first()
    db.close()
    
    # Test Google Calendar Authorize endpoint
    from backend.auth import create_access_token
    auth_token = create_access_token(data={"sub": str(user.id)})

    auth_res = client.get("/auth/google-calendar/authorize", headers={"Authorization": f"Bearer {auth_token}"})
    assert auth_res.status_code == 200
    assert "authorization_url" in auth_res.json()

    # Test Mock Google Calendar event creation directly
    mock_token_str = '{"token": "mock-access-token"}'
    slots = {"name": "Alex", "phone": "555-0199", "service": "Massage", "date": "2026-08-01", "time": "14:00"}
    event_res = create_calendar_event(mock_token_str, "primary", slots, "Test Spa & Salon")
    assert event_res.get("mock") is True
    assert "id" in event_res


def test_paystack_billing_mock():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "testadmin@example.com").first()
    db.close()

    from backend.auth import create_access_token
    auth_token = create_access_token(data={"sub": str(user.id)})

    os.environ["PAYSTACK_SECRET_KEY"] = "sk_test_paystack_dummy_secret_key_12345"
    init_res = client.post(
        "/api/client/billing/initialize-paystack",
        json={"plan": "growth", "callback_url": "http://localhost:5173/#client-dashboard"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert init_res.status_code == 200
    assert init_res.json()["ok"] is True
    assert "authorization_url" in init_res.json()


def test_prompt_architect():
    result = architect.build_default("barber", "KC Cuts")
    assert result.validation_passed is True
    assert "KC Cuts" in result.content
