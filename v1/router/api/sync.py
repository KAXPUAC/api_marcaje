from fastapi import APIRouter, HTTPException
from oracleug.models.dynamics import Dynamics
from requests import Request
from services.sync_service import SyncService
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


@router.get("/departamentos")
async def get_departamentos():
    """Obtiene la lista de departamentos de Oracle"""
    try:
        dynamics = Dynamics()
        deptos = dynamics.obtener_departamentos()
        if "RETVAL" in deptos:
            return deptos["RETVAL"]
        else:
            message = "No se obtuvo la lista de departamentos"
            logger.error(message)
            raise HTTPException(status_code=500, detail=message)
    except Exception as e:
        message = f"Error al obtener departamentos: {e}"
        raise HTTPException(status_code=500, detail=str(message))
