from oracleug.models.pkg_laboratorio import PkgLaboratorio
from oracleug.models.pkg_people import PkgPeople
from oracleug.models.pkg_personal import PkgPersonal
from oracleug.scripts.empleados import Empleados
from oracleug.scripts.reconocimiento import Reconocimiento
from services.auth_service import get_current_user
from services.liveness_session_service import LivenessSessionService
from services.marking_service import normalize_marking_response
from services.rekognition_service import RekognitionService
from schemas.people import (
    AdministrativeLivenessRequest,
    AttendanceResponse,
    TeacherLivenessRequest,
)
from aws.aws_settings import aws_settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/people", tags=["Colaboradores, Docentes"])


def _value(data: dict, name: str, default=None):
    if not isinstance(data, dict):
        return default
    for key, value in data.items():
        if str(key).upper() == name.upper():
            return value
    return default


def _find_user_by_image(image_bytes: bytes, department_id: str | None = None) -> dict:
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


def _get_user_type(usuario: dict, allowed_types: set[int]) -> tuple[str, str]:
    accounts = usuario.get("Usuarios") or []
    for account in accounts:
        tipo = _value(account, "Tipo")
        try:
            tipo_int = int(tipo)
        except (TypeError, ValueError):
            continue
        if tipo_int in allowed_types:
            return str(tipo_int), str(_value(account, "TipoUsuario", ""))

    tipo = _value(usuario, "Tipo")
    try:
        if int(tipo) in allowed_types:
            return str(tipo), str(_value(usuario, "TipoUsuario", ""))
    except (TypeError, ValueError):
        pass

    raise HTTPException(
        status_code=403,
        detail="La persona reconocida no tiene el tipo de usuario permitido",
    )


def _attendance_response(
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
    return AttendanceResponse(
        marcado=marcado,
        abrir_puerta=marcado,
        codpers=str(_value(usuario, "Codpers")) if _value(usuario, "Codpers") is not None else None,
        tipo_usuario=tipo_usuario,
        departamento=departamento,
        laboratorio=laboratorio,
        retorno_funcion=retorno,
        mensaje=mensaje,
        psqlcode=sqlcode,
    )


def _get_liveness_image(session_id: str, flow: str) -> bytes:
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


@router.post(
    "/asistencia/administrative",
    response_model=AttendanceResponse,
    summary="Marcar asistencia administrativa",
    description=(
            "Reconoce el rostro dentro del departamento indicado y registra la "
            "entrada o salida de un usuario administrativo."
    ),
)
async def mark_administrative_attendance(
        request: Request,
        file: UploadFile = File(..., description="Imagen JPG/PNG"),
        departamento: str = Form(..., description="Código de departamento"),
        current_user: dict = Depends(get_current_user),
):
    """Marca entrada o salida de un administrativo."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        usuario = _find_user_by_image(image_bytes, departamento.strip())
        _, tipo_usuario = _get_user_type(usuario, {1})
        resultado = PkgPersonal(
            usuario=str(current_user.get("username", "API")).upper(),
            ip=request.state.client_ip,
        ).ingreso_personal(
            pcodpers=str(_value(usuario, "Codpers")),
        )
        return _attendance_response(
            resultado,
            usuario,
            tipo_usuario,
            departamento=departamento,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error marcando asistencia administrativa")
        raise HTTPException(status_code=500, detail="Error realizando el marcaje") from exc


@router.post(
    "/asistencia/administrative/liveness",
    response_model=AttendanceResponse,
    summary="Marcar asistencia administrativa con prueba de vida",
    description=(
            "Valida la prueba de vida de Amazon, reconoce al usuario administrativo "
            "en el departamento indicado y registra su entrada o salida."
    ),
)
async def mark_administrative_attendance_liveness(
        request: Request,
        data: AdministrativeLivenessRequest,
        current_user: dict = Depends(get_current_user),
):
    """Valida liveness y marca entrada o salida de un administrativo."""
    try:
        image_bytes = _get_liveness_image(data.session_id, "attendance_admin")
        usuario = _find_user_by_image(image_bytes, data.departamento.strip())
        _, tipo_usuario = _get_user_type(usuario, {1})
        resultado = PkgPersonal(
            usuario=str(current_user.get("username", "API")).upper(),
            ip=request.state.client_ip,
        ).ingreso_personal(
            pcodpers=str(_value(usuario, "Codpers")),
        )
        return _attendance_response(
            resultado,
            usuario,
            tipo_usuario,
            departamento=data.departamento,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error marcando administrativo con liveness")
        raise HTTPException(status_code=500, detail="Error realizando el marcaje") from exc


@router.post(
    "/asistencia/teacher",
    response_model=AttendanceResponse,
    summary="Marcar asistencia de docente o tutor",
    description=(
            "Reconoce el rostro en todas las colecciones, valida que sea docente "
            "o tutor y registra la entrada o salida en el laboratorio indicado."
    ),
)
async def mark_teacher_attendance(
        request: Request,
        file: UploadFile = File(..., description="Imagen JPG/PNG"),
        laboratorio: str = Form(..., description="Código del laboratorio o salón"),
        current_user: dict = Depends(get_current_user),
):
    """Marca entrada o salida de un docente o tutor."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        usuario = _find_user_by_image(image_bytes)
        _, tipo_usuario = _get_user_type(usuario, {2, 3})
        resultado = PkgPersonal(
            usuario=str(current_user.get("username", "API")).upper(),
            ip=request.state.client_ip,
        ).ingreso_docente(
            pcodpers=str(_value(usuario, "Codpers")),
            maquina="",
            lab=laboratorio,
        )
        return _attendance_response(
            resultado,
            usuario,
            tipo_usuario,
            laboratorio=laboratorio,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error marcando asistencia docente")
        raise HTTPException(status_code=500, detail="Error realizando el marcaje") from exc


@router.post(
    "/asistencia/teacher/liveness",
    response_model=AttendanceResponse,
    summary="Marcar asistencia de docente o tutor con prueba de vida",
    description=(
            "Valida la prueba de vida de Amazon, reconoce al docente o tutor en "
            "todas las colecciones y registra su entrada o salida en el laboratorio."
    ),
)
async def mark_teacher_attendance_liveness(
        request: Request,
        data: TeacherLivenessRequest,
        current_user: dict = Depends(get_current_user),
):
    """Valida liveness y marca entrada o salida de un docente o tutor."""
    try:
        image_bytes = _get_liveness_image(data.session_id, "attendance_teacher")
        usuario = _find_user_by_image(image_bytes)
        _, tipo_usuario = _get_user_type(usuario, {2, 3})
        resultado = PkgPersonal(
            usuario=str(current_user.get("username", "API")).upper(),
            ip=request.state.client_ip,
        ).ingreso_docente(
            pcodpers=str(_value(usuario, "Codpers")),
            maquina="",
            lab=data.laboratorio,
        )
        return _attendance_response(
            resultado,
            usuario,
            tipo_usuario,
            laboratorio=data.laboratorio,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error marcando docente con liveness")
        raise HTTPException(status_code=500, detail="Error realizando el marcaje") from exc


@router.get(
    "/laboratorios",
    summary="Listar laboratorios y salones autorizados",
    description=(
            "Devuelve los laboratorios y salones de estudio a los que tiene "
            "acceso el usuario autenticado."
    ),
)
async def get_laboratorios(request: Request, current_user: dict = Depends(get_current_user)):
    """Devuelve los laboratorios y salones permitidos para el usuario."""
    try:
        usuario = str(current_user.get("username", "")).upper()
        resultado = PkgLaboratorio(usuario=usuario).laboratorio_pertenece(
            usuario=usuario,
            pip=request.state.client_ip,
        )
        if isinstance(resultado, dict):
            for key, value in resultado.items():
                if str(key).upper() == "RETVAL":
                    return value
        if isinstance(resultado, list):
            return resultado
        return []
    except Exception as exc:
        logger.exception("Error obteniendo laboratorios del usuario")
        raise HTTPException(status_code=500, detail="Error obteniendo los laboratorios") from exc


@router.get("/info_admin")
async def get_people(request: Request, correlativo: str,
                     current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    empleado = Empleados()
    return empleado.get_usuario_por_correlativo(correlativo=int(correlativo))


@router.get("/info_doc")
async def get_doc(request: Request, correlativo: str,
                  current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    pkg = PkgPeople(usuario=usuario, ip=request.state.client_ip)
    return pkg.datosnopersonaltb(correlativo=correlativo)
