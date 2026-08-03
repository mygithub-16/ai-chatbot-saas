from __future__ import annotations

import os
import hashlib
import hmac
import httpx
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class Plan:
    name: str
    monthly_price: int  # USD price
    monthly_price_ngn: int  # NGN price
    message_limit: int
    business_limit: int
    analytics: bool = False


PLANS = {
    "starter": Plan("starter", 29, 45000, 1_000, 1),
    "growth": Plan("growth", 79, 120000, 10_000, 5, True),
    "scale": Plan("scale", 199, 300000, 50_000, 25, True),
}


def get_plan(plan_name: str | None) -> Plan:
    return PLANS.get((plan_name or "starter").lower(), PLANS["starter"])


def plan_summary(plan_name: str | None) -> dict:
    plan = get_plan(plan_name)
    return {
        "name": plan.name,
        "monthly_price": plan.monthly_price,
        "monthly_price_ngn": plan.monthly_price_ngn,
        "message_limit": plan.message_limit,
        "business_limit": plan.business_limit,
        "analytics": plan.analytics,
    }


def can_create_business(plan_name: str | None, current_count: int) -> bool:
    return current_count < get_plan(plan_name).business_limit


def initialize_paystack_transaction(
    email: str,
    amount_ngn: int,
    callback_url: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Initializes a transaction with Paystack.
    Returns the API response JSON which includes 'authorization_url' and 'reference'.
    """
    paystack_secret = os.getenv("PAYSTACK_SECRET_KEY", "")
    if not paystack_secret or paystack_secret.startswith("sk_test_dummy") or paystack_secret == "sk_test_paystack_dummy_secret_key_12345":
        # Mock initialization fallback for development/demo mode when no real key is configured
        mock_reference = f"mock-ref-{hashlib.md5(email.encode()).hexdigest()[:8]}-{metadata.get('business_id', 0)}"
        sep = "&" if "?" in callback_url else "?"
        auth_url = f"{callback_url}{sep}payment_mock_success=true&reference={mock_reference}&plan={metadata.get('plan', 'starter')}"
        
        return {
            "status": True,
            "message": "Authorization URL created (Mock Mode)",
            "data": {
                "authorization_url": auth_url,
                "access_code": "mock-access-code",
                "reference": mock_reference
            }
        }

    headers = {
        "Authorization": f"Bearer {paystack_secret}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "amount": amount_kobo,
        "callback_url": callback_url,
        "metadata": metadata
    }

    url = "https://api.paystack.co/transaction/initialize"
    
    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"Paystack initialization failed (status {response.status_code}): {response.text}")
        return response.json()


def verify_paystack_signature(payload_body: bytes, signature: str | None) -> bool:
    """
    Verifies that the webhook payload matches the signature sent by Paystack.
    """
    paystack_secret = os.getenv("PAYSTACK_SECRET_KEY", "")
    if not paystack_secret:
        return False
    if not signature:
        return False

    computed = hmac.new(
        paystack_secret.encode("utf-8"),
        payload_body,
        hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(computed, signature)

