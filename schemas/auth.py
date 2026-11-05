from pydantic import BaseModel
from typing import Any, Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    username: str
    email: Optional[str] = None
    token_type: str = "bearer"
    correlativo: Optional[str] = None
    auth_method: str
    datos_usuario: Optional[dict[str, Any]] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserPayload(BaseModel):
    username: str
    user_id: Optional[int] = None
    role: Optional[str] = None
