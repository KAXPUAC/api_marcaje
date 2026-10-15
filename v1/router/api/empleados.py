from fastapi import APIRouter
from oracleug.models.pkg_catalogo import PkgCatalogo

router = APIRouter(prefix="/empleados", tags=["empleados"])

@router.post("/empleados")
async def empleados():
    pkg = PkgCatalogo(usuario="")
    return pkg.sel_paises(centro_america="1")
    print("Endpoint de empleados aún no implementado")
    return {"message": "Endpoint de empleados aún no implementado"}