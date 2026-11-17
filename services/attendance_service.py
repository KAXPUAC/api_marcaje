from fastapi import HTTPException

from aws.aws_settings import aws_settings
from oracleug.scripts.reconocimiento import Reconocimiento
from schemas.people import AttendanceResponse
from services.liveness_session_service import LivenessSessionService
from services.marking_service import normalize_marking_response
from services.rekognition_service import RekognitionService


def get_value(data: dict, name: str, default=None):
    if not isinstance(data, dict):
        return default
    for key, value in data.items():
        if str(key).upper() == name.upper():
            return value
    return default


def find_user_by_image(image_bytes: bytes, department_id: str | None = None) -> dict:
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


def get_user_type(usuario: dict, allowed_types: set[int]) -> tuple[str, str]:
    accounts = usuario.get("Usuarios") or []
    for account in accounts:
        tipo = get_value(account, "Tipo")
        try:
            tipo_int = int(tipo)
        except (TypeError, ValueError):
            continue
        if tipo_int in allowed_types:
            return str(tipo_int), str(get_value(account, "TipoUsuario", ""))

    tipo = get_value(usuario, "Tipo")
    try:
        if int(tipo) in allowed_types:
            return str(tipo), str(get_value(usuario, "TipoUsuario", ""))
    except (TypeError, ValueError):
        pass

    raise HTTPException(
        status_code=403,
        detail="La persona reconocida no tiene el tipo de usuario permitido",
    )


def build_attendance_response(
    result,
    usuario: dict,
    tipo_usuario: str,
    departamento: str | None = None,
    laboratorio: str | None = None,
) -> AttendanceResponse:
    normalized = normalize_marking_response(result)
    retorno = normalized.get("RETORNO_FUNCION")
    mensaje = normalized.get("PMENSAJE")
    raw_sqlcode = normalized.get("PSQLCODE")
    try:
        sqlcode = int(raw_sqlcode) if raw_sqlcode is not None else None
    except (TypeError, ValueError):
        sqlcode = None

    marcado = sqlcode == 0
    codpers = get_value(usuario, "Codpers")
    return AttendanceResponse(
        marcado=marcado,
        abrir_puerta=marcado,
        codpers=str(codpers) if codpers is not None else None,
        tipo_usuario=tipo_usuario,
        departamento=departamento,
        laboratorio=laboratorio,
        retorno_funcion=retorno,
        mensaje=mensaje,
        psqlcode=sqlcode,
    )


def get_liveness_image(session_id: str, flow: str) -> bytes:
    LivenessSessionService.consume(session_id, flow=flow)
    liveness = RekognitionService.obtener_resultado_liveness(session_id)
    confidence = liveness.get("confidence")
    score = float(confidence) if confidence is not None else None
    if (
        liveness.get("status") != "SUCCEEDED"
        or score is None
        or score < aws_settings.face_liveness_confidence_threshold()
    ):
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
