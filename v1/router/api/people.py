from oracleug.models.pkg_laboratorio import PkgLaboratorio
from oracleug.models.pkg_people import PkgPeople
from oracleug.models.pkg_personal import PkgPersonal
from oracleug.scripts.empleados import Empleados
from services.auth_service import get_current_user
from services.attendance_service import (
    build_attendance_response,
    get_user_type,
    get_value,
)
from services.recognition_service import find_user_data_by_image, get_liveness_image
from schemas.people import (
    AdministrativeAttendanceResponse,
    AdministrativeLivenessRequest,
    AttendanceResponse,
    PhotoBase64Response,
    TeacherLivenessRequest,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/people", tags=["Colaboradores, Docentes"])


@router.post(
    "/asistencia/administrative",
    response_model=AttendanceResponse,
    summary="Marcar asistencia administrativa",
    description=(
            "Reconoce el rostro dentro del departamento indicado y registra la "
            "entrada o salida de un usuario administrativo."
    ),
)
def mark_administrative_attendance(
        request: Request,
        file: UploadFile = File(..., description="Imagen JPG/PNG"),
        departamento: str = Form(..., description="Código de departamento"),
        current_user: dict = Depends(get_current_user),
):
    """Marca entrada o salida de un administrativo."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    image_bytes = file.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        usuario = find_user_data_by_image(image_bytes, departamento.strip())
        _, tipo_usuario = get_user_type(usuario, {1})
        resultado = PkgPersonal(
            usuario=str(current_user.get("username", "API")).upper(),
            ip=request.state.client_ip,
        ).ingreso_personal(
            pcodpers=str(get_value(usuario, "Codpers")),
        )
        return build_attendance_response(
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
    response_model=AdministrativeAttendanceResponse,
    response_model_by_alias=True,
    summary="Marcar asistencia administrativa con prueba de vida",
    description=(
            "Valida la prueba de vida de Amazon, reconoce al usuario administrativo "
            "en el departamento indicado y registra su entrada o salida."
    ),
)
def mark_administrative_attendance_liveness(
        request: Request,
        data: AdministrativeLivenessRequest,
        current_user: dict = Depends(get_current_user),
):
    """Valida liveness y marca entrada o salida de un administrativo."""
    try:
        image_bytes = get_liveness_image(
            data.session_id,
            "attendance_admin",
            owner=current_user.get("username"),
        )
        usuario = find_user_data_by_image(image_bytes, data.departamento.strip())
        _, tipo_usuario = get_user_type(usuario, {1})
        resultado = PkgPersonal(
            usuario=str(current_user.get("username", "API")).upper(),
            ip=request.state.client_ip,
        ).ingreso_personal(
            pcodpers=str(get_value(usuario, "Codpers")),
        )
        asistencia = build_attendance_response(
            resultado,
            usuario,
            tipo_usuario,
            departamento=data.departamento,
        )
        return AdministrativeAttendanceResponse.model_validate({
            **asistencia.model_dump(),
            **usuario,
        })
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
def mark_teacher_attendance(
        request: Request,
        file: UploadFile = File(..., description="Imagen JPG/PNG"),
        laboratorio: str = Form(..., description="Código del laboratorio o salón"),
        current_user: dict = Depends(get_current_user),
):
    """Marca entrada o salida de un docente o tutor."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    image_bytes = file.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        usuario = find_user_data_by_image(image_bytes)
        _, tipo_usuario = get_user_type(usuario, {2, 3})
        resultado = PkgPersonal(
            usuario=str(current_user.get("username", "API")).upper(),
            ip=request.state.client_ip,
        ).ingreso_docente(
            pcodpers=str(get_value(usuario, "Codpers")),
            maquina="",
            lab=laboratorio,
        )
        return build_attendance_response(
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
def mark_teacher_attendance_liveness(
        request: Request,
        data: TeacherLivenessRequest,
        current_user: dict = Depends(get_current_user),
):
    """Valida liveness y marca entrada o salida de un docente o tutor."""
    try:
        image_bytes = get_liveness_image(
            data.session_id,
            "attendance_teacher",
            owner=current_user.get("username"),
        )
        usuario = find_user_data_by_image(image_bytes)
        _, tipo_usuario = get_user_type(usuario, {2, 3})
        resultado = PkgPersonal(
            usuario=str(current_user.get("username", "API")).upper(),
            ip=request.state.client_ip,
        ).ingreso_docente(
            pcodpers=str(get_value(usuario, "Codpers")),
            maquina="",
            lab=data.laboratorio,
        )
        return build_attendance_response(
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
def get_laboratorios(request: Request, current_user: dict = Depends(get_current_user)):
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


@router.get(
    "/es_administrativo",
    summary="Verificar pertenencia a Informática o Prestaciones",
)
def belongs_to_allowed_department(current_user: dict = Depends(get_current_user)):
    """Indica si el usuario pertenece a Informática o Prestaciones."""
    coddepa = str(current_user.get("coddepa") or "").strip()
    return {
        "pertenece": coddepa in {"0306", "0313"},
        "coddepa": coddepa or None,
        "departamento": current_user.get("departamento"),
    }


@router.get("/info_admin")
def get_people(request: Request, correlativo: str,
                     current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    empleado = Empleados()
    return empleado.get_usuario_por_correlativo(correlativo=int(correlativo))


@router.get("/info_doc")
def get_doc(request: Request, correlativo: str,
                   current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    pkg = PkgPeople(usuario=usuario, ip=request.state.client_ip)
    return pkg.datosnopersonaltb(correlativo=correlativo)


@router.get(
    "/foto/{correlativo}",
    response_class=Response,
    summary="Obtener foto como bytes",
)
def get_photo_bytes(
        correlativo: int,
        current_user: dict = Depends(get_current_user),
):
    """Devuelve la foto LONG RAW asociada al correlativo."""
    try:
        foto = Empleados().get_foto_bytes(correlativo)
        if foto is None:
            raise HTTPException(status_code=404, detail="Foto no encontrada")
        return Response(content=foto, media_type="application/octet-stream")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error obteniendo la foto del correlativo %s", correlativo)
        raise HTTPException(status_code=500, detail="Error obteniendo la foto") from exc


@router.get(
    "/fotoB64/{correlativo}",
    response_model=PhotoBase64Response,
    summary="Obtener foto como base64",
)
def get_photo_base64(
        correlativo: int,
        current_user: dict = Depends(get_current_user),
) -> PhotoBase64Response:
    """Devuelve la foto LONG RAW asociada al correlativo en base64."""
    try:
        foto = Empleados().get_foto_base64(correlativo)
        if foto is None:
            raise HTTPException(status_code=404, detail="Foto no encontrada")
        return PhotoBase64Response(
            correlativo=correlativo,
            foto_base64=foto,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error obteniendo la foto base64 del correlativo %s", correlativo)
        raise HTTPException(status_code=500, detail="Error obteniendo la foto") from exc
