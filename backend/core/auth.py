"""
JWT Auth Layer — Multi-tenancy and per-user data connector scoping.
Issues JWTs with embedded user ID, role, and permitted data sources.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt

from core.config import settings

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = settings.SECRET_KEY if hasattr(settings, "SECRET_KEY") else "changeme-in-production-use-env-var"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

# ── Models ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str = ""
    organization: str = ""

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    permitted_sources: List[str]

class TokenPayload(BaseModel):
    sub: str           # user id
    email: str
    role: str          # "admin" | "analyst" | "viewer"
    org: str
    permitted_sources: List[str]   # ["sql", "excel", "salesforce"]
    exp: datetime


# ── In-Memory User Store (replace with DB in production) ─────────────────────
# Format: {email: {hashed_password, id, role, org, permitted_sources}}
_USER_STORE: Dict[str, Dict] = {
    "admin@talkingbi.ai": {
        "id": "usr_001",
        "hashed_password": pwd_ctx.hash("admin123"),
        "full_name": "Admin User",
        "role": "admin",
        "org": "TalkingBI",
        "permitted_sources": ["sql", "excel", "salesforce", "shopify"],
    },
    "analyst@talkingbi.ai": {
        "id": "usr_002",
        "hashed_password": pwd_ctx.hash("analyst123"),
        "full_name": "Analyst User",
        "role": "analyst",
        "org": "TalkingBI",
        "permitted_sources": ["sql", "excel"],
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_access_token(data: Dict) -> str:
    payload = {**data, "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[Dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Auth Functions ────────────────────────────────────────────────────────────

def authenticate_user(email: str, password: str) -> Optional[Dict]:
    user = _USER_STORE.get(email)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user

def register_user(data: UserCreate) -> Dict:
    if data.email in _USER_STORE:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "id": f"usr_{len(_USER_STORE)+1:03d}",
        "hashed_password": hash_password(data.password),
        "full_name": data.full_name,
        "role": "analyst",
        "org": data.organization or "default",
        "permitted_sources": ["sql", "excel"],
    }
    _USER_STORE[data.email] = user
    return user

def issue_token(email: str, user: Dict) -> TokenResponse:
    token = create_access_token({
        "sub": user["id"],
        "email": email,
        "role": user["role"],
        "org": user["org"],
        "permitted_sources": user["permitted_sources"],
    })
    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        email=email,
        role=user["role"],
        permitted_sources=user["permitted_sources"],
    )


# ── FastAPI Dependency ────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Dict]:
    """
    Dependency that extracts and validates the JWT bearer token.
    Returns the decoded token payload or None if auth is disabled.
    """
    # If no secret key configured, auth is effectively disabled (dev mode)
    if SECRET_KEY == "changeme-in-production-use-env-var":
        return {"sub": "dev", "email": "dev@local", "role": "admin", "permitted_sources": ["sql", "excel", "salesforce", "shopify"]}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    return payload


def require_source_access(source: str):
    """Factory: returns a FastAPI dependency that checks source permissions."""
    async def _dep(user: Dict = Depends(get_current_user)):
        if user.get("role") == "admin":
            return user
        permitted = user.get("permitted_sources", [])
        if source not in permitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have access to the '{source}' data source",
            )
        return user
    return _dep
