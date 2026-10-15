from fastapi import APIRouter, HTTPException
from services.sync_service import SyncService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["Sincronización"])

@router.post("/departamento/{coddepa}/status")
async def departamento_status(coddepa: str):
    """Verifica el estado de sincronización de un departamento."""
    try:
        return SyncService.sincronizar_departamento(coddepa)
        """return {
            'departamento': coddepa,
            'total_empleados': result['total'],
            'exitosos': result['exitosos'],
            'errores': result['errores']
        }"""
    except Exception as e:
        logger.error(f"Error al verificar estado del departamento {coddepa}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
