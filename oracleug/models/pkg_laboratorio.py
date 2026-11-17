from oracleug.ora_db import Oradb, ODBType, ODBDirection, ODBFunctionType
from oracleug.utils.params import params


class PkgLaboratorio:
    def __init__(self, usuario: str = "API"):
        self.__usuario = usuario
        self.__con = Oradb()
        self.__types = ODBType()
        self.__direct = ODBDirection()
        self.__function = ODBFunctionType()
        self.__retval = params('RETVAL', '', self.__types.SYS_REFCURSOR, self.__direct.OUT)
        self.__sqlcode = params('PSQLCODE', '', self.__types.NUMBER, self.__direct.OUT)

    def laboratorio_pertenece(self, usuario: str, pip: str):
        parametros = [
            params("PUSUARIOAPLICACION", usuario, self.__types.VARCHAR2, self.__direct.IN),
            params("PAPLICACION", "", self.__types.VARCHAR2, self.__direct.IN),
            params("PIP", pip, self.__types.VARCHAR2, self.__direct.IN),
            self.__sqlcode,
            self.__retval
        ]
        name_procedure = "DBAFISICC.PKG_LABORATORIO.LABORATORIO_PERTENECE"
        return self.__con.execute_procedure(procedure_name=name_procedure, params=parametros)
