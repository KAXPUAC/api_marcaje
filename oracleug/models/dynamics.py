from oracleug.ora_db import Oradb, ODBType, ODBDirection, ODBFunctionType
from oracleug.utils.params import params

db = Oradb()
types = ODBType()
direct = ODBDirection()


class Dynamics:
    def __init__(self, usuario: str = "API"):
        self.__usuario = usuario
        self.__retval = params('RETVAL', '', types.SYS_REFCURSOR, direct.OUT)

    def obtener_departamentos(self):
        parametros = [
            self.__retval
        ]
        nombre_procedure = "DBAFISICC.DYNAMICS.OBTENER_DEPARTAMENTOS"
        return db.execute_procedure(nombre_procedure, parametros)
