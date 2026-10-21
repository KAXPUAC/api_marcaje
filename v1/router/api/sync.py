from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException
from oracleug.models.dynamics import Dynamics
from requests import Request
from services.rekognition_service import RekognitionService
from aws.aws_settings import aws_settings
from services.sync_service import SyncService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["Sincronización"])


@router.post("/departamento/{coddepa}/")
async def sync_departamento(coddepa: str):
    """Sincroniza un departamento."""
    try:
        return SyncService.sincronizar_departamento(coddepa)
    except Exception as e:
        message = f"Error al verificar estado del departamento {coddepa}: {e}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=str(message))

@router.post("/departamento/{coddepa}/status/")
async def status_departamento(coddepa: str):
    """Verifica si la collection existe y cuántas caras tiene."""

    collection_id = RekognitionService.obtener_nombre_coleccion(coddepa)
    try:
        desc = aws_settings.rekognition().describe_collection(CollectionId=collection_id)
        return {
            "Coleccion": collection_id,
            "Cantidad Rostros": desc.get('FaceCount', 0),
            "Creado": str(desc.get('CreationTimestamp'))
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return {"collection_id": collection_id, "face_count": 0, "exists": False}
        raise


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
