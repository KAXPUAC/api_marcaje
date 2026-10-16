from fastapi import APIRouter, HTTPException
from services.sync_service import SyncService
from services.s3_service import S3Service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["Sincronización"])

@router.post("/departamento/{coddepa}/status")
async def departamento_status(coddepa: str):
    """Verifica el estado de sincronización de un departamento."""
    try:
        return SyncService.sincronizar_departamento(coddepa)
    except Exception as e:
        message = f"Error al verificar estado del departamento {coddepa}: {e}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=str(message))


@router.get("/buckets")
async def listar_buckets():
    """Lista los buckets de S3 disponibles."""
    try:
        s3 = S3Service()
        return s3.list_buckets()
    except Exception as e:
        message = f"Error al listar buckets: {e}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=str(message))