from oracleug.ora_db import Oradb, ODBType, ODBDirection, ODBFunctionType
from oracleug.utils.params import params


class PkgPeople:
    def __init__(self, usuario: str = "API", ip: str = "127.0.0.1"):
        self.ip = ip
        self.__usuario = usuario
        self.__conn = Oradb()
        self.__types = ODBType()
        self.__direct = ODBDirection()
        self.__function = ODBFunctionType()
        self.__retval = params('RETVAL', '', self.__types.SYS_REFCURSOR, self.__direct.OUT)
        self.__sqlcode = params('PSQLCODE', '', self.__types.NUMBER, self.__direct.OUT)

    def datosnopersonaltb(self, correlativo: str):
        parametros = [
            params('PCORRELATIVO', correlativo, self.__types.NUMBER, self.__direct.IN),
            self.__retval,
            self.__sqlcode
        ]
        nombre_procedure = "DBAFISICC.PKG_PEOPLE.DATOSNOPERSONALTB"
        return self.__conn.execute_procedure(procedure_name=nombre_procedure, params=parametros)
