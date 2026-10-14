from oracleug.ora_db import Oradb, ODBType, ODBDirection, ODBFunctionType
from oracleug.utils.params import params

db = Oradb()
types = ODBType()
direct = ODBDirection()


class PkgCatalogo:
    def __init__(self, usuario):
        self.usuario = usuario

    def sel_paises(self, centro_america: str = "0"):
        parametros = [
            params('PCENTROAMERICA', centro_america, types.VARCHAR2, direct.IN),
            params('PSQLCODE', '', types.NUMBER, direct.OUT),
            params('PERROR', '', types.VARCHAR2, direct.OUT),
            params('PRESP', '', types.VARCHAR2, direct.OUT),
            params('RETVAL', '', types.SYS_REFCURSOR, direct.OUT),
            params('PUSUARIOAPLICACION', self.usuario, types.VARCHAR2, direct.IN),
            params('PAPLICACION', '', types.VARCHAR2, direct.IN),
            params('PIP', '', types.VARCHAR2, direct.IN),
        ]
        nombre_procedure = "DBAFISICC.PKG_CATALOGO.SEL_GNPAISESTB"
        return db.execute_procedure(nombre_procedure, parametros)
