from pydantic import BaseModel
from typing import Any, Literal, Optional


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


class LivenessSessionResponse(BaseModel):
    session_id: str
    region: str
    identity_pool_id: str


class LivenessSessionRequest(BaseModel):
    flow: Literal["login", "verify"] = "login"


class LivenessRequest(BaseModel):
    session_id: str


class LivenessLoginResponse(BaseModel):
    success: bool
    is_live: bool
    liveness_score: Optional[float] = None
    spoof_detected: bool = False
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    refresh_expires_in: Optional[int] = None
    token_type: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    correlativo: Optional[str] = None
    auth_method: Optional[str] = None
    datos_usuario: Optional[dict[str, Any]] = None
    message: Optional[str] = None


class LivenessVerifyRequest(BaseModel):
    session_id: str
    departamento: str


class RecognizeLivenessResponse(BaseModel):
    success: bool
    is_live: bool
    liveness_score: Optional[float] = None
    spoof_detected: bool = False
    departamento: Optional[str] = None
    correlativo: Optional[str] = None
    similarity: Optional[float] = None
    confidence: Optional[float] = None
    face_id: Optional[str] = None
    message: Optional[str] = None


class UserPayload(BaseModel):
    username: str
    user_id: Optional[int] = None
    role: Optional[str] = None
