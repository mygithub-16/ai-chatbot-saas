from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from backend.db import Base


class TimestampMixin:
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(512), nullable=True)
    auth_provider = Column(String(64), nullable=False, default="local")
    business_name = Column(String(255), nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    calendar_token = Column(Text, nullable=True)
    calendar_id = Column(String(255), nullable=True)

    businesses = relationship("Business", back_populates="owner")


class Business(TimestampMixin, Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=False, index=True)
    business_description = Column(Text, nullable=True)
    services_products = Column(Text, nullable=True)
    faqs = Column(Text, nullable=True)
    policies = Column(Text, nullable=True)
    tone_style = Column(String(128), nullable=False, default="friendly and professional")
    personality_prompt = Column(Text, nullable=True)
    lead_capture_enabled = Column(Boolean, nullable=False, default=True)
    plan = Column(String(64), nullable=False, default="starter")
    subscription_status = Column(String(64), nullable=False, default="trial")
    address = Column(String(512), nullable=True)
    lat_long = Column(String(128), nullable=True)

    owner = relationship("User", back_populates="businesses")
    leads = relationship("Lead", back_populates="business")
    events = relationship("Event", back_populates="business")
    sessions = relationship("ConversationSession", back_populates="business")


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    business_type = Column(String(128), nullable=False, default="unknown")
    contact = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    source = Column(String(64), nullable=False, default="web")
    acquisition_channel = Column(String(64), nullable=False, default="landing_page")
    session_id = Column(String(128), nullable=True, index=True)
    status = Column(String(64), nullable=False, default="NEW")
    buying_probability = Column(Integer, nullable=False, default=0)
    urgency_score = Column(Integer, nullable=False, default=0)
    metadata_json = Column(JSON, nullable=False, default=dict)

    business = relationship("Business", back_populates="leads")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    session_id = Column(String(128), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True, index=True)
    metadata_json = Column(JSON, nullable=False, default=dict)

    business = relationship("Business", back_populates="events")


class ConversationSession(TimestampMixin, Base):
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True, index=True)
    intent = Column(String(128), nullable=True)
    status = Column(String(64), nullable=False, default="collecting")
    slots_json = Column(JSON, nullable=False, default=dict)
    missing_slots_json = Column(JSON, nullable=False, default=list)
    history_json = Column(JSON, nullable=False, default=list)
    workflow_state_json = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    business = relationship("Business", back_populates="sessions")
