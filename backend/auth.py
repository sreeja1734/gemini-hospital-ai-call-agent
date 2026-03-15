"""
Authentication middleware using JWT tokens.
Protects API endpoints with Bearer token authentication.
"""
import structlog
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings

logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security scheme
security = HTTPBearer(auto_error=False)

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


class TokenPayload(BaseModel):
    sub: str
    role: str = "user"
    exp: Optional[datetime] = None


class UserInfo(BaseModel):
    username: str
    role: str = "user"


def create_access_token(
    username: str,
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenPayload:
    """Decode and verify a JWT token, returning its payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> UserInfo:
    """
    FastAPI dependency to extract and validate the current user from a JWT.
    Returns a UserInfo if valid, raises 401 otherwise.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token_data = verify_token(credentials.credentials)
    return UserInfo(username=token_data.sub, role=token_data.role)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[UserInfo]:
    """
    Like get_current_user, but returns None instead of raising if unauthenticated.
    Useful for endpoints that work with or without auth.
    """
    if credentials is None:
        return None
    try:
        token_data = verify_token(credentials.credentials)
        return UserInfo(username=token_data.sub, role=token_data.role)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency factory: returns a dependency that requires the user to have the specified role.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    async def role_checker(
        user: UserInfo = Depends(get_current_user),
    ) -> UserInfo:
        if user.role != required_role and user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker
