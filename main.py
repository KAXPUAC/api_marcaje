from fastapi import FastAPI
from v1.router.api import sync, recognize

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(recognize.router, prefix="/api/v1", tags=["Reconocimiento Facial"])
app.include_router(sync.router, prefix="/api/v1", tags=["Sincronización"])
