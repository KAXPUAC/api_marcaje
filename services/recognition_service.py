import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import HTTPException

from aws.aws_settings import aws_settings
from oracleug.scripts.reconocimiento import Reconocimiento
from schemas.recognize import RecognizedUserResponse
from services.liveness_session_service import LivenessSessionService
from services.rekognition_service import RekognitionService


_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_liveness_logger = logging.getLogger("liveness")
if not _liveness_logger.handlers:
    _liveness_logger.setLevel(logging.INFO)
    _liveness_logger.addHandler(
        RotatingFileHandler(
            _LOG_DIR / "liveness.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
    )
    _liveness_logger.propagate = False


def get_liveness_image(
    session_id: str,
    flow: str = "recognize",
    owner: str | None = None,
) -> bytes:
    LivenessSessionService.consume(session_id, flow=flow, owner=owner)
    liveness = RekognitionService.obtener_resultado_liveness(session_id)
    confidence = liveness.get("confidence")
    threshold = aws_settings.face_liveness_confidence_threshold()
    _liveness_logger.info(
        "Face Liveness session_id=%s flow=%s status=%s confidence=%s threshold=%s",
        session_id,
        flow,
        liveness.get("status"),
        confidence,
        threshold,
    )
    score = float(confidence) if confidence is not None else None
    is_live = (
        liveness.get("status") == "SUCCEEDED"
        and score is not None
        and score >= threshold
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


def find_user_data_by_image(
    image_bytes: bytes,
    department_id: str | None = None,
) -> dict:
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
        raise HTTPException(status_code=404, detail="No se encontró coincidencia facial")

    usuario = Reconocimiento().get_datos_usuario(match["external_image_id"])
    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron datos asociados al rostro reconocido",
        )
    return usuario


def find_user_by_image(
    image_bytes: bytes,
    department_id: str | None = None,
) -> RecognizedUserResponse:
    return RecognizedUserResponse.model_validate(
        find_user_data_by_image(image_bytes, department_id)
    )
