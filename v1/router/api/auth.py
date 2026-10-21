from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from services.auth_service import get_current_user
from schemas.auth import TokenResponse
from services.auth_service import login_api

router = APIRouter()


@router.post("/token", response_model=TokenResponse)
async def get_token(form_data: OAuth2PasswordRequestForm = Depends()):
    return login_api(form_data.username, form_data.password)


# 3. Ejemplo de ruta protegida
@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"message": "Acceso concedido", "user": current_user}
