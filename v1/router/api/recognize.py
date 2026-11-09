from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from services.auth_service import facial_login, get_current_user
from oracleug.scripts.empleados import Empleados
from services.rekognition_service import RekognitionService
from schemas.recognize import RecognizeResponse
from schemas.auth import LivenessRequest, LivenessSessionResponse, TokenResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recognize", tags=["Reconocimiento Facial"])


@router.post("/liveness/session", response_model=LivenessSessionResponse)
async def create_liveness_session():
    """Crea una sesión que el cliente debe completar usando Face Liveness."""
    try:
        return {"session_id": RekognitionService.crear_sesion_liveness()}
    except Exception as e:
        logger.exception("Error creando sesión de Face Liveness")
        raise HTTPException(status_code=500, detail="No se pudo crear la sesión de liveness") from e


@router.post("/liveness", response_model=TokenResponse)
async def authenticate_with_liveness(request: Request, data: LivenessRequest):
    """Valida liveness, busca el rostro y genera los tokens de autenticación."""
    try:
        liveness = RekognitionService.obtener_resultado_liveness(data.session_id)
        if liveness["status"] != "SUCCEEDED":
            raise HTTPException(
                status_code=401,
                detail=f"La validación de liveness no fue exitosa: {liveness['status']}",
            )

        confidence = liveness.get("confidence")
        if confidence is None or float(confidence) < 90.0:
            raise HTTPException(
                status_code=401,
                detail="La confianza de liveness es insuficiente",
            )

        reference_image = liveness.get("reference_image")
        if not reference_image:
            raise HTTPException(
                status_code=400,
                detail="La sesión no contiene una imagen de referencia",
            )

        match = RekognitionService.buscar_rostro_en_todos_departamentos(
            image_bytes=reference_image,
            umbral=90.0,
        )
        if not match:
            raise HTTPException(
                status_code=401,
                detail="La persona está viva, pero no se encontró coincidencia facial",
            )

        return facial_login(
            correlativo=match["external_image_id"],
            ip=request.state.client_ip,
            auth_method="facial_liveness",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error autenticando con Face Liveness")
        raise HTTPException(status_code=500, detail="Error procesando la autenticación facial") from e


@router.post("", response_model=RecognizeResponse)
async def recognize_face(current_user: dict = Depends(get_current_user),
                         file: UploadFile = File(..., description="Imagen JPG/PNG"),
                         departamento: str = Form(..., description="Código de departamento (CODDEPA)")):
    """
    Reconoce un rostro comparando contra la collection Rekognition del departamento.
    Retorna el correlativo del empleado (ExternalImageId) si hay coincidencia ≥ 90%.
    """
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
            departamento_id=departamento,
            image_bytes=image_bytes,
            umbral=90.0
        )

        if not match:
            return RecognizeResponse(
                success=False,
                message=f"No se encontró coincidencia en el departamento {departamento}"
            )
        empleado = Empleados()
        datos = empleado.get_empleado_info(correlativo=match["external_image_id"])
        return RecognizeResponse(
            success=True,
            correlativo=match["external_image_id"],
            datos_info=datos,
            similarity=match["similarity"],
            face_id=match["face_id"],
            confidence=match["confidence"]
        )

    except Exception as e:
        logger.error(f"Error en reconocimiento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en reconocimiento: {str(e)}")


@router.post("/automatic", response_model=TokenResponse)
async def recognize_face_automatic(request: Request,
                                   file: UploadFile = File(..., description="Imagen JPG/PNG")):
    """Reconoce un rostro buscando en todos los departamentos indexados."""
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (JPG/PNG)")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        match = RekognitionService.buscar_rostro_en_todos_departamentos(
            image_bytes=image_bytes,
            umbral=90.0
        )

        if not match:
            raise HTTPException(
                status_code=401,
                detail="No se encontró coincidencia en los departamentos indexados",
            )

        response = facial_login(
            correlativo=match["external_image_id"],
            ip=request.state.client_ip,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en reconocimiento automático: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en reconocimiento: {str(e)}")
