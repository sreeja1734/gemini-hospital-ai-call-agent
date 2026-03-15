"""
Auth routes — login, token refresh, and user management.
"""
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ..auth import (
    create_access_token,
    pwd_context,
    get_current_user,
    UserInfo,
)
from ..config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = structlog.get_logger()

# For demonstration/hackathon — in production, store users in the database.
# Passwords are hashed with bcrypt.
DEMO_USERS = {
    "admin": {
        "password_hash": pwd_context.hash("admin123"),
        "role": "admin",
    },
}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate a user and return a JWT access token."""
    user = DEMO_USERS.get(req.username)
    if not user or not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(username=req.username, role=user["role"])
    logger.info("User logged in", username=req.username, role=user["role"])
    return TokenResponse(
        access_token=token,
        username=req.username,
        role=user["role"],
    )


@router.get("/me")
async def get_me(user: UserInfo = Depends(get_current_user)):
    """Return the currently authenticated user info."""
    return {"username": user.username, "role": user.role}
