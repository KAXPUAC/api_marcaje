from fastapi import APIRouter, UploadFile, File, Path, HTTPException, Body
from services.rekognition_service import RekognitionService
from services.liveness_session_service import LivenessSessionService
from services.recognition_service import find_user_by_image, get_liveness_image
from schemas.recognize import RecognizedUserResponse
from schemas.auth import (
    LivenessRequest,
    LivenessSessionRequest,
    LivenessSessionResponse,
)
from aws.aws_settings import aws_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recognize", tags=["Reconocimiento Facial"])


@router.post("/liveness/session", response_model=LivenessSessionResponse)
def create_liveness_session(
        data: LivenessSessionRequest | None = Body(default=None),
):
    """Crea una sesión que el cliente debe completar usando Face Liveness."""
    flow = data.flow if data else "login"
    try:
        session_id = RekognitionService.crear_sesion_liveness()
        LivenessSessionService.register(
            session_id=session_id,
            owner=None,
            flow=flow,
            ttl=aws_settings.face_liveness_session_ttl_seconds(),
        )
        return {
            "session_id": session_id,
            "region": aws_settings.region(),
            "identity_pool_id": aws_settings.identity_pool_id(),
        }
    except Exception as e:
        logger.exception("Error creando sesión de Face Liveness")
        raise HTTPException(status_code=500, detail="No se pudo crear la sesión de liveness") from e


@router.post(
    "/{department_id}/search/liveness",
    response_model=RecognizedUserResponse,
)
def recognize_in_department_with_liveness(
    data: LivenessRequest,
    department_id: str = Path(..., description="Código de departamento (CODDEPA)"),
):
    """Valida liveness y reconoce un rostro dentro de un departamento."""
    try:
        image_bytes = get_liveness_image(data.session_id)
        return find_user_by_image(image_bytes, department_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error en reconocimiento con liveness por departamento")
        raise HTTPException(
            status_code=500,
            detail="Error procesando el reconocimiento facial",
        ) from exc


@router.post("/search/liveness", response_model=RecognizedUserResponse)
def recognize_globally_with_liveness(data: LivenessRequest):
    """Valida liveness y reconoce un rostro en todos los departamentos."""
    try:
        image_bytes = get_liveness_image(data.session_id)
        return find_user_by_image(image_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error en reconocimiento global con liveness")
        raise HTTPException(
            status_code=500,
            detail="Error procesando el reconocimiento facial",
        ) from exc


@router.post("/{department_id}/search", response_model=RecognizedUserResponse)
def recognize_in_department(
                                  file: UploadFile = File(..., description="Imagen JPG/PNG"),
                                  department_id: str = Path(..., description="Código de departamento (CODDEPA)")):
    """Reconoce un rostro en un departamento y devuelve sus datos completos."""
    # Validar tipo de archivo
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (JPG/PNG)")

    # Leer bytes
    image_bytes = file.file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        return find_user_by_image(image_bytes, department_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en reconocimiento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en reconocimiento: {str(e)}")


@router.post("/search", response_model=RecognizedUserResponse)
def search_face_global(
                             file: UploadFile = File(..., description="Imagen JPG/PNG")):
    """Busca un rostro en todas las colecciones y devuelve sus datos asociados."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (JPG/PNG)")

    image_bytes = file.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        return find_user_by_image(image_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error en reconocimiento automático")
        raise HTTPException(
            status_code=500,
            detail="Error procesando el reconocimiento facial",
        ) from exc
