from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    username: str
    email: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserPayload(BaseModel):
    username: str
    user_id: Optional[int] = None
    role: Optional[str] = None
