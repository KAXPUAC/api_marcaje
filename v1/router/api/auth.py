from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from services.auth_service import facial_login, get_current_user
from services.rekognition_service import RekognitionService
from schemas.auth import RefreshTokenRequest, SocialLoginRequest, TokenResponse, TokenMeResponse
from services.auth_service import login_api, logout, refresh_access_token, social_login

router = APIRouter(prefix='/auth', tags=["Autenticación"])


@router.post("/token", response_model=TokenResponse)
async def get_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    return login_api(form_data.username, form_data.password, ip=request.state.client_ip)


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, data: RefreshTokenRequest):
    return refresh_access_token(data.refresh_token, ip=request.state.client_ip)


@router.post("/google", response_model=TokenResponse)
async def google_login(request: Request, data: SocialLoginRequest):
    return social_login("google", data.id_token, ip=request.state.client_ip)


@router.post("/microsoft", response_model=TokenResponse)
async def microsoft_login(request: Request, data: SocialLoginRequest):
    return social_login("microsoft", data.id_token, ip=request.state.client_ip)


@router.post("/facial", response_model=TokenResponse)
async def facial_auth(request: Request, file: UploadFile = File(..., description="Imagen JPG/PNG")):
    """Auténtica al usuario buscando su rostro en todos los departamentos."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (JPG/PNG)")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        match = RekognitionService.buscar_rostro_en_todos_departamentos(
            image_bytes=image_bytes,
            umbral=90.0,
        )
        if not match:
            raise HTTPException(
                status_code=401,
                detail="No se encontró coincidencia en los departamentos indexados",
            )

        return facial_login(
            correlativo=match["external_image_id"],
            ip=request.state.client_ip,
            auth_method="facial",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Error procesando la autenticación facial",
        ) from exc


@router.post("/logout")
async def logout_token(data: RefreshTokenRequest):
    logout(data.refresh_token)
    return {"message": "Sesión cerrada correctamente"}


# 3. Ejemplo de ruta protegida
@router.get("/users/me", response_model=TokenMeResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
