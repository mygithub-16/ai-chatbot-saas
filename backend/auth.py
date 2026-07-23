from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.config import get_settings
from backend.models import User

settings = get_settings()
SECRET_KEY = settings.admin_token_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


# ==========================================
# 1. Password Hashing & Verification Engine
# ==========================================

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return "pbkdf2_sha256$120000$" + base64.b64encode(salt).decode("ascii") + "$" + base64.b64encode(derived_key).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_blob, derived_blob = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_blob.encode("ascii"))
        stored_derived_key = base64.b64decode(derived_blob.encode("ascii"))
        calculated_derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(calculated_derived_key, stored_derived_key)
    except Exception:
        return False


# ==========================================
# 2. Token Generation & User Context Hooks
# ==========================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_request_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Authenticates a user via JWT provided in the Authorization header.
    Expected Format: Authorization: Bearer <token>
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing or invalid authentication token"
        )

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user_identifier = int(user_id)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    user = db.query(User).filter(User.id == user_identifier).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_optional_request_user(request: Request, db: Session = Depends(get_db)):
    """Optional user fetcher helper."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return None

    try:
        user_identifier = int(user_id)
    except ValueError:
        return None

    return db.query(User).filter(User.id == user_identifier).first()


# ==========================================
# 3. Production Administration Guards
# ==========================================

def require_admin(request: Request, db: Session = Depends(get_db)):
    """
    Production Guard: Secures administrative routes using both user model properties
    and your required secret 64-character verification tokens.
    """
    # 1. Inspect user via standard token flow
    user = get_request_user(request, db)

    # 2. Check database model configuration flag
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrative access denied.")

    # 3. Enforce the Secret Admin Token verification check from headers
    provided_token = request.headers.get("X-Admin-Secret-Token")
    expected_token = os.getenv("ADMIN_DASHBOARD_SECRET")

    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="System auth configuration error."
        )

    # Uses constant-time string comparison to prevent side-channel timing attacks
    if not provided_token or not hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid administrative signature token.")

    return user


def require_business_owner_or_admin(user, business_owner_id: int):
    if getattr(user, "is_admin", False):
        return user
    if getattr(user, "id", None) != business_owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business access required")
    return user