from oracleug.models.pkg_people import PkgPeople
from oracleug.models.pkg_personal import PkgPersonal
from oracleug.scripts.empleados import Empleados
from services.auth_service import get_current_user
from services.marking_service import normalize_marking_response
from schemas.people import MarkingResponse
from fastapi import APIRouter, Depends, Request

router = APIRouter(prefix="/people", tags=["Colaboradores, Docentes"])


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


@router.post("/marcar", response_model=MarkingResponse)
async def marcar(request: Request, codpers: str, current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    pkg = PkgPersonal(usuario=usuario, ip=request.state.client_ip)
    return normalize_marking_response(pkg.ingreso_personal(pcodpers=codpers))


@router.post("/marcar_doc", response_model=MarkingResponse)
async def ingreso_doc(request: Request, codpers: str, laboratorio: str,
                      current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    pkg = PkgPersonal(usuario=usuario, ip=request.state.client_ip)
    return normalize_marking_response(
        pkg.ingreso_docente(pcodpers=codpers, maquina="", lab=laboratorio)
    )
