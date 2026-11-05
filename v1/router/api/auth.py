from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from services.auth_service import get_current_user
from schemas.auth import RefreshTokenRequest, TokenResponse
from services.auth_service import login_api, refresh_access_token

router = APIRouter()


@router.post("/token", response_model=TokenResponse)
async def get_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    return login_api(form_data.username, form_data.password, ip=request.state.client_ip)


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, data: RefreshTokenRequest):
    return refresh_access_token(data.refresh_token, ip=request.state.client_ip)


# 3. Ejemplo de ruta protegida
@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"message": "Acceso concedido", "user": current_user}
