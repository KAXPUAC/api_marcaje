from fastapi import HTTPException

from aws.aws_settings import aws_settings
from oracleug.scripts.reconocimiento import Reconocimiento
from schemas.recognize import RecognizedUserResponse
from services.liveness_session_service import LivenessSessionService
from services.rekognition_service import RekognitionService


def get_liveness_image(session_id: str) -> bytes:
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


def find_user_by_image(image_bytes: bytes, department_id: str | None = None):
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
    return RecognizedUserResponse.model_validate(usuario)
