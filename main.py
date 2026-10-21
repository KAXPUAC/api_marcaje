from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordRequestForm
from v1.router.api import sync, recognize, auth
from services.auth_service import login_api
from schemas.auth import TokenResponse

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/token", response_model=TokenResponse)
async def get_token(form_data: OAuth2PasswordRequestForm = Depends()):
    return login_api(form_data.username, form_data.password)


app.include_router(auth.router, prefix="/api/v1", tags=["Autenticación"])
app.include_router(recognize.router, prefix="/api/v1", tags=["Reconocimiento Facial"])
app.include_router(sync.router, prefix="/api/v1", tags=["Sincronización"])
