"""
Authentication middleware using JWT tokens.
Protects staff dashboard endpoints with Bearer token authentication.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

import structlog
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings

logger = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


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
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> UserInfo:
    """Extract and validate the current staff user from a JWT."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token_data = verify_token(credentials.credentials)
    return UserInfo(username=token_data.sub, role=token_data.role)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[UserInfo]:
    """Return the authenticated user when present, otherwise None."""
    if credentials is None:
        return None
    try:
        token_data = verify_token(credentials.credentials)
        return UserInfo(username=token_data.sub, role=token_data.role)
    except HTTPException:
        return None


def require_role(roles: Sequence[str] | str):
    """
    Dependency factory requiring the user to have one of the specified roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(["admin"]))])
    """
    allowed_roles = [roles] if isinstance(roles, str) else list(roles)

    async def role_checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return role_checker
