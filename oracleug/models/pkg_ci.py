from oracleug.ora_db import Oradb, ODBType, ODBDirection, ODBFunctionType
from oracleug.utils.params import params


class PkgCi:
    def __init__(self, usuario: str = "API"):
        self.__usuario = usuario
        self.__con = Oradb()
        self.__types = ODBType()
        self.__direct = ODBDirection()
        self.__dir_f = ODBFunctionType()
        self.retval = params('RETVAL', '', self.__types.SYS_REFCURSOR, self.__direct.OUT)

    def autenticar_administrativo(self, usuario: str, contrasena: str):
        parametros = [
            params('PUSUARIO', usuario, self.__types.VARCHAR2, self.__direct.IN),
            params('PCONTRASENA', contrasena, self.__types.VARCHAR2, self.__direct.IN),
        ]
        nombre_procedure = "DBAFISICC.PKG_CI.AUTENTICARADMINISTRATIVO"
        return self.__con.execute_function(function_name=nombre_procedure, params=parametros,
                                           type_function=self.__dir_f.NUMBER)

    def autenticar(self, usuario: str, contrasena: str, tipo: int):
        parametros = [
            params('PUSUARIO', usuario, self.__types.VARCHAR2, self.__direct.IN),
            params('PCONTRASENA', contrasena, self.__types.VARCHAR2, self.__direct.IN),
            params('PTIPO', tipo, self.__types.NUMBER, self.__direct.IN),
        ]
        nombre_procedure = "DBAFISICC.PKG_CI.AUTENTICAR"
        return self.__con.execute_function(function_name=nombre_procedure, params=parametros,
                                           type_function=self.__dir_f.NUMBER)
