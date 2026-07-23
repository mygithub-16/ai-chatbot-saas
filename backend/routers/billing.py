from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.auth import get_request_user
from backend.models import User, Business, Event
from backend.billing import initialize_paystack_transaction, verify_paystack_signature, get_plan

router = APIRouter(tags=["Billing"])


class PaystackInitializePayload(BaseModel):
    plan: str = Field(min_length=3, max_length=64)
    callback_url: str = Field(min_length=10)


@router.post("/api/client/billing/initialize-paystack")
def client_billing_initialize_paystack(
    payload: PaystackInitializePayload,
    user: User = Depends(get_request_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    business = db.query(Business).filter(Business.owner_id == user.id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business profile not found")
        
    requested_plan = payload.plan.lower()
    if requested_plan not in {"starter", "growth", "scale"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan name")
        
    plan_obj = get_plan(requested_plan)
    amount_ngn = plan_obj.monthly_price_ngn
    
    metadata = {
        "business_id": business.id,
        "user_id": user.id,
        "plan": requested_plan,
        "amount_usd": plan_obj.monthly_price
    }
    
    try:
        response_data = initialize_paystack_transaction(
            email=user.email,
            amount_ngn=amount_ngn,
            callback_url=payload.callback_url,
            metadata=metadata
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initialize payment: {str(e)}")
        
    if not response_data.get("status"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response_data.get("message", "Failed to initialize payment with Paystack")
        )
        
    event = Event(
        event_name="billing_initiated",
        timestamp=datetime.now(timezone.utc),
        session_id=f"paystack-{business.id}-{int(datetime.now(timezone.utc).timestamp())}",
        user_id=user.id,
        business_id=business.id,
        metadata_json={"plan": requested_plan, "amount_ngn": amount_ngn},
    )
    db.add(event)
    db.commit()
    
    return {
        "ok": True,
        "authorization_url": response_data["data"]["authorization_url"],
        "reference": response_data["data"]["reference"]
    }


@router.post("/api/webhooks/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    body = await request.body()
    paystack_secret = os.getenv("PAYSTACK_SECRET_KEY", "")
    
    if paystack_secret:
        if not verify_paystack_signature(body, x_paystack_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
            
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")
        
    event_type = payload.get("event")
    if event_type == "charge.success":
        data = payload.get("data", {})
        metadata = data.get("metadata", {})
        business_id = metadata.get("business_id")
        plan = metadata.get("plan")
        user_id = metadata.get("user_id")
        
        if not business_id or not plan:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing business_id or plan in metadata")
            
        business = db.query(Business).filter(Business.id == int(business_id)).first()
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
            
        business.plan = plan.lower()
        business.subscription_status = "active"
        db.commit()
        db.refresh(business)
        
        event = Event(
            event_name="billing_upgraded",
            timestamp=datetime.now(timezone.utc),
            session_id=f"paystack-webhook-{business.id}",
            user_id=int(user_id) if user_id else None,
            business_id=business.id,
            metadata_json={
                "plan": plan,
                "status": "active",
                "reference": data.get("reference"),
                "gateway": "paystack"
            },
        )
        db.add(event)
        db.commit()
        
    return {"status": "success"}
