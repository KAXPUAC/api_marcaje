from fastapi import APIRouter, UploadFile, File, Path, Form, HTTPException, Depends, Request, Body
from fastapi.security import OAuth2PasswordBearer
from services.auth_service import facial_login, get_current_user
from oracleug.scripts.reconocimiento import Reconocimiento
from services.rekognition_service import RekognitionService
from services.liveness_session_service import LivenessSessionService
from schemas.recognize import RecognizeResponse, RecognizedUserResponse
from schemas.auth import (
    LivenessLoginResponse,
    LivenessRequest,
    LivenessSessionRequest,
    LivenessSessionResponse,
    LivenessVerifyRequest,
    RecognizeLivenessResponse,
)
from aws.aws_settings import aws_settings
from oracleug.security import decode_access_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recognize", tags=["Reconocimiento Facial"])
optional_oauth2 = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


@router.post("/liveness/session", response_model=LivenessSessionResponse)
async def create_liveness_session(
        request: Request,
        data: LivenessSessionRequest | None = Body(default=None),
        token: str | None = Depends(optional_oauth2),
):
    """Crea una sesión que el cliente debe completar usando Face Liveness."""
    flow = data.flow if data else "login"
    owner = None
    if flow == "verify" and not token:
        raise HTTPException(
            status_code=401,
            detail="El flujo verify requiere el token del operador",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if flow == "verify" and token:
        owner_payload = decode_access_token(token)
        if owner_payload is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        owner = owner_payload.get("username")
    try:
        session_id = RekognitionService.crear_sesion_liveness()
        LivenessSessionService.register(
            session_id=session_id,
            owner=owner,
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


@router.post("/liveness", response_model=LivenessLoginResponse)
async def authenticate_with_liveness(request: Request, data: LivenessRequest,
                                     token: str | None = Depends(optional_oauth2), ):
    """Valida liveness, busca el rostro y genera los tokens de autenticación."""
    try:
        LivenessSessionService.consume(data.session_id, flow="login")
        liveness = RekognitionService.obtener_resultado_liveness(data.session_id)
        confidence = liveness.get("confidence")
        score = float(confidence) if confidence is not None else None
        is_live = liveness[
                      "status"] == "SUCCEEDED" and score is not None and score >= aws_settings.face_liveness_confidence_threshold()
        if not is_live:
            return {
                "success": False,
                "is_live": False,
                "liveness_score": score,
                "spoof_detected": liveness["status"] == "FAILED" or (
                        score is not None and score < aws_settings.face_liveness_confidence_threshold()),
                "message": "No se pudo verificar que exista una persona real frente a la cámara.",
            }

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

        response = facial_login(
            correlativo=match["external_image_id"],
            ip=request.state.client_ip,
            auth_method="facial_liveness",
        )
        return {
            "success": True,
            "is_live": True,
            "liveness_score": score,
            "spoof_detected": False,
            **response,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error autenticando con Face Liveness")
        raise HTTPException(status_code=500, detail="Error procesando la autenticación facial") from e


@router.post("/liveness/verify", response_model=RecognizeLivenessResponse)
async def verify_liveness_for_marking(
        request: Request,
        data: LivenessVerifyRequest,
        current_user: dict = Depends(get_current_user),
):
    """Valida liveness y reconoce una persona sin cambiar la sesión del operador."""
    try:
        LivenessSessionService.consume(
            data.session_id,
            flow="verify",
            owner=current_user.get("username"),
        )
        liveness = RekognitionService.obtener_resultado_liveness(data.session_id)
        confidence = liveness.get("confidence")
        score = float(confidence) if confidence is not None else None
        is_live = liveness[
                      "status"] == "SUCCEEDED" and score is not None and score >= aws_settings.face_liveness_confidence_threshold()
        if not is_live:
            return {
                "success": False,
                "is_live": False,
                "liveness_score": score,
                "spoof_detected": liveness["status"] == "FAILED" or (
                        score is not None and score < aws_settings.face_liveness_confidence_threshold()),
                "message": "La imagen no corresponde a una persona real.",
            }

        reference_image = liveness.get("reference_image")
        if not reference_image:
            raise HTTPException(status_code=400, detail="La sesión no contiene una imagen de referencia")

        departamento = data.departamento.strip()
        if not departamento:
            raise HTTPException(status_code=400, detail="El departamento es obligatorio")

        match = RekognitionService.buscar_rostro_en_departamento(
            departamento_id=departamento,
            image_bytes=reference_image,
            umbral=90.0,
            crear_collection=False,
        )
        if not match:
            return {
                "success": False,
                "is_live": True,
                "liveness_score": score,
                "spoof_detected": False,
                "departamento": departamento,
                "message": "No se reconoció el rostro en el departamento seleccionado.",
            }

        return {
            "success": True,
            "is_live": True,
            "liveness_score": score,
            "spoof_detected": False,
            "departamento": departamento,
            "correlativo": match["external_image_id"],
            "similarity": match["similarity"],
            "confidence": match["confidence"],
            "face_id": match["face_id"],
            "message": None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error verificando Face Liveness para marcaje")
        raise HTTPException(status_code=500, detail="Error procesando la verificación facial") from e


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
