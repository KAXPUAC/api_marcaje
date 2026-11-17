from fastapi import FastAPI, Request
from v1.router.api import sync, recognize, auth, people
from services.request_service import get_client_ip
from services.sqlite_store import sqlite_store

app = FastAPI(title="API de Marcaje", version="1.0.0",
              description="API para el sistema de marcaje de personal y docentes, con reconocimiento facial y autenticación social.")


@app.middleware("http")
async def set_client_ip(request: Request, call_next):
    """Deja la IP disponible en todas las peticiones GET y POST."""
    request.state.client_ip = get_client_ip(request)
    return await call_next(request)


@app.get("/health")
def health_check():
    sqlite_ok = sqlite_store.check_health()
    return {
        "status": "ok" if sqlite_ok else "degraded",
        "sqlite": "ok" if sqlite_ok else "error",
    }


app.include_router(auth.router, prefix="/api/v1", tags=["Autenticación"])
app.include_router(recognize.router, prefix="/api/v1", tags=["Reconocimiento Facial"])
app.include_router(sync.router, prefix="/api/v1", tags=["Sincronización"])
app.include_router(people.router, prefix="/api/v1", tags=["Colaboradores, Docentes"])
