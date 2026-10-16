from fastapi import FastAPI
from v1.router.api import empleados, sync, recognize

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    print(f"Received item_id: {item_id}, q: {q}")
    return {"item_id": item_id, "q": q}


app.include_router(empleados.router, prefix="/api/v1", tags=["empleados"])
app.include_router(recognize.router, prefix="/api/v1", tags=["Reconocimiento Facial"])
app.include_router(sync.router, prefix="/api/v1", tags=["Sincronización"])
