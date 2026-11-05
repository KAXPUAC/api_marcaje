from oracleug.models.pkg_people import PkgPeople
from oracleug.models.pkg_personal import PkgPersonal
from services.auth_service import get_current_user
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/people", tags=["Colaboradores, Docentes"])


@router.get("/info_admin", tags=["Colaboradores, Docentes"])
async def get_people(correlativo: str, current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    pkg = PkgPeople(usuario=usuario)
    return pkg.datosnopersonaltb(correlativo=correlativo)


@router.get("/info_doc", tags=["Colaboradores, Docentes"])
async def get_doc(correlativo: str, current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    pkg = PkgPeople(usuario=usuario)
    return pkg.datosnopersonaltb(correlativo=correlativo)


@router.post("/marcar", tags=["Colaboradores, Docentes"])
async def marcar(codpers: str, current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    pkg = PkgPersonal(usuario=usuario)
    return pkg.ingreso_personal(pcodpers=codpers)


@router.post("/marcar_doc", tags=["Colaboradores, Docentes"])
async def ingeso_doc(codpers: str, laboratorio: str, current_user: dict = Depends(get_current_user)):
    usuario = str(current_user['username']).upper()
    pkg = PkgPersonal(usuario=usuario)
    return pkg.ingreso_docente(pcodpers=codpers, maquina="", lab=laboratorio)
