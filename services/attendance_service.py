from fastapi import HTTPException

from schemas.people import AttendanceResponse
from services.marking_service import normalize_marking_response
from services.recognition_service import (
    find_user_data_by_image,
    get_liveness_image,
)


def get_value(data: dict, name: str, default=None):
    if not isinstance(data, dict):
        return default
    for key, value in data.items():
        if str(key).upper() == name.upper():
            return value
    return default


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
