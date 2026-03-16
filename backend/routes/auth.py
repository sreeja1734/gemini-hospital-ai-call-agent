"""
Authentication routes for hospital staff.
"""
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import UserInfo, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = structlog.get_logger()

STAFF_USERS = {
    "admin": {
        "password": "admin123",
        "role": "admin",
    },
    "doctor1": {
        "password": "doctor123",
        "role": "doctor",
    },
    "reception1": {
        "password": "recep123",
        "role": "receptionist",
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
    """Authenticate a staff user and return a JWT access token."""
    user = STAFF_USERS.get(req.username)
    if not user or req.password != user["password"]:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(username=req.username, role=user["role"])
    logger.info("Staff user logged in", username=req.username, role=user["role"])
    return TokenResponse(
        access_token=token,
        username=req.username,
        role=user["role"],
    )


@router.get("/me")
async def get_me(user: UserInfo = Depends(get_current_user)):
    """Return the currently authenticated staff user."""
    return {"username": user.username, "role": user.role}
