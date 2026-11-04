from oracleug.models.pkg_people import PkgPeople
from services.auth_service import get_current_user
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/people", tags=["Colaboradores, Docentes"])


@router.get("", tags=["Colaboradores, Docentes"])
async def get_people(correlativo: str, current_user: dict = Depends(get_current_user)):
    # user = current_user
    pkg = PkgPeople()
    return pkg.datosnopersonaltb(correlativo=correlativo)
