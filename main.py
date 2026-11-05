from fastapi import FastAPI, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from v1.router.api import sync, recognize, auth, people
from services.auth_service import login_api, refresh_access_token
from schemas.auth import RefreshTokenRequest, TokenResponse
from services.request_service import get_client_ip

app = FastAPI()


@app.middleware("http")
async def set_client_ip(request: Request, call_next):
    """Deja la IP disponible en todas las peticiones GET y POST."""
    request.state.client_ip = get_client_ip(request)
    return await call_next(request)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/token", response_model=TokenResponse)
async def get_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    return login_api(username=form_data.username, password=form_data.password, ip=request.state.client_ip)


@app.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, data: RefreshTokenRequest):
    return refresh_access_token(data.refresh_token, ip=request.state.client_ip)


app.include_router(auth.router, prefix="/api/v1", tags=["Autenticación"])
app.include_router(recognize.router, prefix="/api/v1", tags=["Reconocimiento Facial"])
app.include_router(sync.router, prefix="/api/v1", tags=["Sincronización"])
app.include_router(people.router, prefix="/api/v1", tags=["Colaboradores, Docentes"])
