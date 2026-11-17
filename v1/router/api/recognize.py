from fastapi import APIRouter, UploadFile, File, Path, HTTPException, Body
from oracleug.scripts.reconocimiento import Reconocimiento
from services.rekognition_service import RekognitionService
from services.liveness_session_service import LivenessSessionService
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
async def create_liveness_session(
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


def _obtener_imagen_liveness(session_id: str) -> bytes:
    LivenessSessionService.consume(session_id, flow="recognize")
    liveness = RekognitionService.obtener_resultado_liveness(session_id)
    confidence = liveness.get("confidence")
    score = float(confidence) if confidence is not None else None
    is_live = (
        liveness.get("status") == "SUCCEEDED"
        and score is not None
        and score >= aws_settings.face_liveness_confidence_threshold()
    )
    if not is_live:
        raise HTTPException(
            status_code=422,
            detail="No se pudo verificar que exista una persona real frente a la cámara",
        )

    reference_image = liveness.get("reference_image")
    if not reference_image:
        raise HTTPException(
            status_code=400,
            detail="La sesión no contiene una imagen de referencia",
        )
    return reference_image


def _buscar_usuario_por_imagen(image_bytes: bytes, department_id: str | None = None):
    if department_id:
        match = RekognitionService.buscar_rostro_en_departamento(
            departamento_id=department_id,
            image_bytes=image_bytes,
            umbral=90.0,
            crear_collection=False,
        )
    else:
        match = RekognitionService.buscar_rostro_en_todos_departamentos(
            image_bytes=image_bytes,
            umbral=90.0,
        )

    if not match:
        raise HTTPException(
            status_code=404,
            detail="No se encontró coincidencia facial",
        )

    usuario = Reconocimiento().get_datos_usuario(match["external_image_id"])
    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron datos asociados al rostro reconocido",
        )
    return RecognizedUserResponse.model_validate(usuario)


@router.post(
    "/{department_id}/search/liveness",
    response_model=RecognizedUserResponse,
)
async def recognize_in_department_with_liveness(
    data: LivenessRequest,
    department_id: str = Path(..., description="Código de departamento (CODDEPA)"),
):
    """Valida liveness y reconoce un rostro dentro de un departamento."""
    try:
        image_bytes = _obtener_imagen_liveness(data.session_id)
        return _buscar_usuario_por_imagen(image_bytes, department_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error en reconocimiento con liveness por departamento")
        raise HTTPException(
            status_code=500,
            detail="Error procesando el reconocimiento facial",
        ) from exc


@router.post("/search/liveness", response_model=RecognizedUserResponse)
async def recognize_globally_with_liveness(data: LivenessRequest):
    """Valida liveness y reconoce un rostro en todos los departamentos."""
    try:
        image_bytes = _obtener_imagen_liveness(data.session_id)
        return _buscar_usuario_por_imagen(image_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error en reconocimiento global con liveness")
        raise HTTPException(
            status_code=500,
            detail="Error procesando el reconocimiento facial",
        ) from exc


@router.post("/{department_id}/search", response_model=RecognizedUserResponse)
async def recognize_in_department(
                                  file: UploadFile = File(..., description="Imagen JPG/PNG"),
                                  department_id: str = Path(..., description="Código de departamento (CODDEPA)")):
    """Reconoce un rostro en un departamento y devuelve sus datos completos."""
    # Validar tipo de archivo
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (JPG/PNG)")

    # Leer bytes
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        # Buscar en Rekognition
        match = RekognitionService.buscar_rostro_en_departamento(
            departamento_id=department_id,
            image_bytes=image_bytes,
            umbral=90.0
        )

        if not match:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró coincidencia en el departamento {department_id}",
            )

        usuario = Reconocimiento().get_datos_usuario(match["external_image_id"])
        if not usuario:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron datos asociados al rostro reconocido",
            )
        return RecognizedUserResponse.model_validate(usuario)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en reconocimiento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en reconocimiento: {str(e)}")


@router.post("/search", response_model=RecognizedUserResponse)
async def search_face_global(
                             file: UploadFile = File(..., description="Imagen JPG/PNG")):
    """Busca un rostro en todas las colecciones y devuelve sus datos asociados."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (JPG/PNG)")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        match = RekognitionService.buscar_rostro_en_todos_departamentos(
            image_bytes=image_bytes,
            umbral=90.0,
        )
        if not match:
            raise HTTPException(
                status_code=404,
                detail="No se encontró coincidencia en los departamentos indexados",
            )
        usuario = Reconocimiento().get_datos_usuario(match["external_image_id"])
        if not usuario:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron datos asociados al rostro reconocido",
            )

        return RecognizedUserResponse.model_validate(usuario)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error en reconocimiento automático")
        raise HTTPException(
            status_code=500,
            detail="Error procesando el reconocimiento facial",
        ) from exc
