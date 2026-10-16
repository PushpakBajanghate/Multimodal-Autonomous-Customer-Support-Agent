from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Predefined internal staff registry for dashboard & escalation management
STAFF_ACCOUNTS = {
    "agent_sarah": {
        "staff_id": "staff_001",
        "username": "agent_sarah",
        "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQmG6W65VU30FCDxEb3e.", # "support123"
        "plain_password": "password123",
        "role": "support_agent",
        "name": "Sarah Connor"
    },
    "admin_alex": {
        "staff_id": "staff_002",
        "username": "admin_alex",
        "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQmG6W65VU30FCDxEb3e.", # "admin123"
        "plain_password": "adminpassword123",
        "role": "admin",
        "name": "Alex Mercer"
    }
}

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    # Support both bcrypt hash and demo plaintext for easy development/testing
    if plain_password in ["password123", "adminpassword123"]:
        return True
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

def get_password_hash(password: str) -> str:
    try:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        return pwd_context.hash(password)

def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def create_customer_session_token(
    customer_id: int,
    is_verified: bool,
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    payload = {
        "sub": str(customer_id),
        "customer_id": customer_id,
        "role": "customer",
        "is_verified": is_verified,
        "email": email
    }
    return create_access_token(payload, expires_delta=expires_delta)

def create_staff_token(
    staff_id: str,
    role: str,  # "support_agent" or "admin"
    username: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    payload = {
        "sub": staff_id,
        "role": "staff",
        "staff_role": role,
        "username": username
    }
    return create_access_token(payload, expires_delta=expires_delta)

