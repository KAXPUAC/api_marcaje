from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    username: str
    email: str
    token_type: str = "bearer"


class UserPayload(BaseModel):
    username: str
    user_id: Optional[int] = None
    role: Optional[str] = None
