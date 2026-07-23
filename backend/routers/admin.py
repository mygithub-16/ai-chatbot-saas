from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User, Business, Lead, Event

router = APIRouter(tags=["Admin & Analytics"])


class AdminBusinessPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    business_name: Optional[str] = Field(default=None, max_length=255)
    business_description: str = Field(default="")
    services_products: str = Field(default="")
    faqs: str = Field(default="")
    policies: str = Field(default="")
    tone_style: str = Field(default="friendly and professional", max_length=128)
    personality_prompt: str = Field(default="")
    owner_email: Optional[str] = Field(default=None, max_length=255)
    lead_capture_enabled: bool = True


class AdminBusinessUpdatePayload(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    business_name: Optional[str] = Field(default=None, max_length=255)
    business_description: Optional[str] = Field(default=None)
    services_products: Optional[str] = Field(default=None)
    faqs: Optional[str] = Field(default=None)
    policies: Optional[str] = Field(default=None)
    tone_style: Optional[str] = Field(default=None, max_length=128)
    personality_prompt: Optional[str] = Field(default=None)
    owner_email: Optional[str] = Field(default=None, max_length=255)
    lead_capture_enabled: Optional[bool] = None


def serialize_admin_business(business: Business) -> Dict[str, Any]:
    has_calendar = False
    calendar_id = None
    if business.owner:
        has_calendar = bool(business.owner.calendar_token)
        calendar_id = business.owner.calendar_id

    return {
        "id": business.id,
        "owner_id": business.owner_id,
        "owner_email": getattr(getattr(business, "owner", None), "email", None),
        "name": business.name,
        "business_name": business.business_name,
        "business_description": business.business_description or "",
        "services_products": business.services_products or "",
        "faqs": business.faqs or "",
        "policies": business.policies or "",
        "tone_style": business.tone_style or "friendly and professional",
        "personality_prompt": business.personality_prompt or "",
        "lead_capture_enabled": business.lead_capture_enabled,
        "plan": business.plan,
        "subscription_status": business.subscription_status,
        "has_calendar_connected": has_calendar,
        "calendar_id": calendar_id,
        "created_at": business.created_at.isoformat() if business.created_at else None,
    }


@router.get("/admin/businesses")
@router.get("/businesses")
def admin_list_businesses(db: Session = Depends(get_db)) -> Dict[str, Any]:
    businesses = db.query(Business).order_by(Business.created_at.desc()).all()
    return {"businesses": [serialize_admin_business(business) for business in businesses]}


@router.post("/admin/businesses")
def admin_create_business(payload: AdminBusinessPayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
    owner = None
    if payload.owner_email:
        owner = db.query(User).filter(User.email == payload.owner_email.strip().lower()).first()
        if owner is None:
            owner = User(
                email=payload.owner_email.strip().lower(),
                auth_provider="local",
                business_name=payload.business_name or payload.name,
                is_admin=False,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

    business = Business(
        owner_id=owner.id if owner else None,
        name=payload.name,
        business_name=payload.business_name or payload.name,
        business_description=payload.business_description,
        services_products=payload.services_products,
        faqs=payload.faqs,
        policies=payload.policies,
        tone_style=payload.tone_style,
        personality_prompt=payload.personality_prompt,
        lead_capture_enabled=payload.lead_capture_enabled,
    )
    db.add(business)
    db.commit()
    db.refresh(business)

    return {"ok": True, "business": serialize_admin_business(business)}


@router.patch("/admin/businesses/{business_id}")
def admin_update_business(business_id: int, payload: AdminBusinessUpdatePayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
    business = db.query(Business).filter(Business.id == business_id).first()
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    if payload.owner_email is not None:
        owner = db.query(User).filter(User.email == payload.owner_email.strip().lower()).first()
        if owner is None:
            owner = User(
                email=payload.owner_email.strip().lower(),
                auth_provider="local",
                business_name=payload.business_name or business.business_name,
                is_admin=False,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)
        business.owner_id = owner.id

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
    return {"ok": True, "business": serialize_admin_business(business)}


@router.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    recent_window_start = now - timedelta(days=1)
    previous_window_start = now - timedelta(days=2)

    event_names = ["page_view", "demo_started", "demo_completed", "lead_submitted", "business_created"]
    event_counts = {event_name: db.query(Event).filter(Event.event_name == event_name).count() for event_name in event_names}
    recent_counts = {
        event_name: db.query(Event).filter(Event.event_name == event_name, Event.timestamp >= recent_window_start).count()
        for event_name in event_names
    }
    previous_counts = {
        event_name: db.query(Event)
        .filter(Event.event_name == event_name, Event.timestamp >= previous_window_start, Event.timestamp < recent_window_start)
        .count()
        for event_name in event_names
    }

    page_views = event_counts["page_view"]
    lead_submissions = event_counts["lead_submitted"]
    overall_conversion_rate = round((lead_submissions / page_views) * 100, 2) if page_views else 0.0

    def delta(current: int, previous: int) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)

    avg_lead_score = db.query(func.avg(Lead.buying_probability)).scalar() or 0

    return {
        "totals": {
            "page_views": page_views,
            "demo_starts": event_counts["demo_started"],
            "demo_completions": event_counts["demo_completed"],
            "leads": lead_submissions,
            "businesses": db.query(Business).count(),
            "overall_conversion_rate": overall_conversion_rate,
            "average_lead_score": round(float(avg_lead_score), 2),
        },
        "deltas": {
            "page_views": delta(event_counts["page_view"], previous_counts["page_view"]),
            "demo_starts": delta(event_counts["demo_started"], previous_counts["demo_started"]),
            "demo_completions": delta(event_counts["demo_completed"], previous_counts["demo_completed"]),
            "leads": delta(event_counts["lead_submitted"], previous_counts["lead_submitted"]),
            "businesses": delta(event_counts["business_created"], previous_counts["business_created"]),
        },
        "window_counts": recent_counts,
    }


@router.get("/analytics/leads")
def analytics_leads(db: Session = Depends(get_db)) -> Dict[str, Any]:
    leads = db.query(Lead).all()
    bucket_counts = {"HOT": 0, "WARM": 0, "COLD": 0}
    source_counts: Dict[str, int] = {}
    score_total = 0

    for lead in leads:
        score = lead.buying_probability or 0
        score_total += score
        if lead.status and lead.status.upper() in bucket_counts:
            bucket = lead.status.upper()
        elif score >= 70 or (lead.urgency_score or 0) >= 4:
            bucket = "HOT"
        elif score >= 40 or (lead.urgency_score or 0) >= 2:
            bucket = "WARM"
        else:
            bucket = "COLD"
        bucket_counts[bucket] += 1
        source_key = lead.source or "unknown"
        source_counts[source_key] = source_counts.get(source_key, 0) + 1

    average_score = round(score_total / len(leads), 2) if leads else 0.0
    recent_leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(10).all()

    return {
        "counts": bucket_counts,
        "average_lead_score": average_score,
        "source_breakdown": dict(sorted(source_counts.items(), key=lambda item: item[1], reverse=True)),
        "total_leads": len(leads),
        "recent_leads": [
            {
                "id": lead.id,
                "name": lead.name,
                "status": lead.status,
                "business_type": lead.business_type,
                "source": lead.source,
                "buying_probability": lead.buying_probability,
                "urgency_score": lead.urgency_score,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
            }
            for lead in recent_leads
        ],
    }


@router.get("/analytics/activity")
def analytics_activity(limit: int = 20, db: Session = Depends(get_db)) -> Dict[str, Any]:
    sanitized_limit = max(1, min(limit, 50))
    events = db.query(Event).order_by(Event.timestamp.desc()).limit(sanitized_limit).all()
    labels = {
        "page_view": "Page viewed",
        "demo_started": "Demo started",
        "demo_completed": "Demo completed",
        "lead_submitted": "Lead submitted",
        "business_created": "Business created",
    }
    return {
        "events": [
            {
                "id": event.id,
                "event_name": event.event_name,
                "label": labels.get(event.event_name, event.event_name.replace("_", " ").title()),
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "session_id": event.session_id,
                "user_id": event.user_id,
                "business_id": event.business_id,
                "metadata": event.metadata_json or {},
            }
            for event in events
        ]
    }
