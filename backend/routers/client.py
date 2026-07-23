from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.auth import get_request_user
from backend.models import User, Business, Lead, Event

router = APIRouter(prefix="/api/client", tags=["Client Dashboard"])


class ClientBusinessUpdatePayload(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    business_name: Optional[str] = Field(default=None, max_length=255)
    business_description: Optional[str] = Field(default=None)
    services_products: Optional[str] = Field(default=None)
    faqs: Optional[str] = Field(default=None)
    policies: Optional[str] = Field(default=None)
    tone_style: Optional[str] = Field(default=None, max_length=128)
    personality_prompt: Optional[str] = Field(default=None)
    lead_capture_enabled: Optional[bool] = None


def serialize_client_business(business: Business) -> Dict[str, Any]:
    owner = business.owner
    has_calendar = bool(owner and owner.calendar_token)
    calendar_id = (owner.calendar_id if owner else None) or "primary"
    return {
        "id": business.id,
        "owner_id": business.owner_id,
        "name": business.name,
        "business_name": business.business_name,
        "business_description": business.business_description or "",
        "services_products": business.services_products or "",
        "faqs": business.faqs or "",
        "policies": business.policies or "",
        "tone_style": business.tone_style or "friendly and professional",
        "personality_prompt": business.personality_prompt or "",
        "lead_capture_enabled": business.lead_capture_enabled,
        "plan": business.plan or "starter",
        "subscription_status": business.subscription_status or "trial",
        "has_calendar_connected": has_calendar,
        "calendar_id": calendar_id if has_calendar else None,
    }


@router.get("/business")
def get_client_business(user: User = Depends(get_request_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    business = db.query(Business).filter(Business.owner_id == user.id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business profile not found")
    return {"ok": True, "business": serialize_client_business(business)}


@router.patch("/business")
def update_client_business(
    payload: ClientBusinessUpdatePayload, 
    user: User = Depends(get_request_user), 
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    business = db.query(Business).filter(Business.owner_id == user.id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business profile not found")
    
    update_fields = {
        "name": payload.name,
        "business_name": payload.business_name,
        "business_description": payload.business_description,
        "services_products": payload.services_products,
        "faqs": payload.faqs,
        "policies": payload.policies,
        "tone_style": payload.tone_style,
        "personality_prompt": payload.personality_prompt,
        "lead_capture_enabled": payload.lead_capture_enabled,
    }
    for field_name, field_value in update_fields.items():
        if field_value is not None:
            setattr(business, field_name, field_value)
            
    db.commit()
    db.refresh(business)
    return {"ok": True, "business": serialize_client_business(business)}


@router.get("/leads")
def get_client_leads(user: User = Depends(get_request_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    business = db.query(Business).filter(Business.owner_id == user.id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business profile not found")
        
    leads = db.query(Lead).filter(Lead.business_id == business.id).order_by(Lead.created_at.desc()).all()
    return {
        "ok": True,
        "leads": [
            {
                "id": lead.id,
                "name": lead.name,
                "business_type": lead.business_type,
                "contact": lead.contact,
                "email": lead.email,
                "source": lead.source,
                "status": lead.status,
                "buying_probability": lead.buying_probability,
                "urgency_score": lead.urgency_score,
                "metadata_json": lead.metadata_json or {},
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
            }
            for lead in leads
        ]
    }


@router.get("/analytics")
def get_client_analytics(user: User = Depends(get_request_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    business = db.query(Business).filter(Business.owner_id == user.id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business profile not found")
        
    event_names = ["page_view", "demo_started", "demo_completed", "lead_submitted"]
    counts = {
        event_name: db.query(Event).filter(Event.business_id == business.id, Event.event_name == event_name).count()
        for event_name in event_names
    }
    
    page_views = counts["page_view"]
    leads_count = counts["lead_submitted"]
    conversion_rate = round((leads_count / page_views) * 100, 2) if page_views else 0.0
    
    recent_events = (
        db.query(Event)
        .filter(Event.business_id == business.id)
        .order_by(Event.timestamp.desc())
        .limit(15)
        .all()
    )
    
    leads = db.query(Lead).filter(Lead.business_id == business.id).all()
    bucket_counts = {"HOT": 0, "WARM": 0, "COLD": 0}
    score_total = 0
    for lead in leads:
        score = lead.buying_probability or 0
        score_total += score
        if lead.status and lead.status.upper() in bucket_counts:
            bucket = lead.status.upper()
        elif score >= 70:
            bucket = "HOT"
        elif score >= 40:
            bucket = "WARM"
        else:
            bucket = "COLD"
        bucket_counts[bucket] += 1
        
    avg_lead_score = round(score_total / len(leads), 2) if leads else 0.0
    
    return {
        "ok": True,
        "totals": {
            "page_views": page_views,
            "demo_starts": counts["demo_started"],
            "demo_completions": counts["demo_completed"],
            "leads": leads_count,
            "conversion_rate": conversion_rate,
            "avg_lead_score": avg_lead_score,
        },
        "lead_quality": bucket_counts,
        "recent_activity": [
            {
                "id": event.id,
                "event_name": event.event_name,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "metadata": event.metadata_json or {},
            }
            for event in recent_events
        ]
    }


@router.post("/calendar/disconnect")
def google_calendar_disconnect(
    user: User = Depends(get_request_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    user_record = db.query(User).filter(User.id == user.id).first()
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    user_record.calendar_token = None
    user_record.calendar_id = None
    db.commit()
    return {"ok": True, "message": "Google Calendar disconnected successfully"}
