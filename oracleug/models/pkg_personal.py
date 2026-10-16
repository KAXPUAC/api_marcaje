from oracleug.ora_db import Oradb, ODBType, ODBDirection, ODBFunctionType
from oracleug.utils.params import params

db = Oradb()
types = ODBType()
direct = ODBDirection()


class PkgPersonal:
    def __init__(self, usuario: str = "API", aplicacion: str = "API", ip: str = "0.0.0.0"):
        self.usuario = usuario
        self.aplicacion = aplicacion
        self.ip = ip
        self.retval = params('RETVAL', '', types.SYS_REFCURSOR, direct.OUT)
        self.sqlcode = params('PSQLCODE', '', types.NUMBER, direct.OUT)

    def ingreso_personal(self, pcodpers: str):
        parametros = [
            params('PCODPERS', pcodpers, types.VARCHAR2, direct.IN),
            params('PMENSAJE', '', types.VARCHAR2, direct.OUT),
            params('PAPLICACION', self.aplicacion, types.VARCHAR2, direct.IN),
            params('PUSUARIOAPLICACION', self.usuario, types.VARCHAR2, direct.IN),
            params('PIP', self.ip, types.VARCHAR2, direct.IN),
            self.sqlcode
        ]
        nombre_procedure = "DBAFISICC.PKG_PERSONAL.INGRESO_PERSONAL"
        return db.execute_function(nombre_procedure, parametros, type_function=ODBFunctionType.STRING)
