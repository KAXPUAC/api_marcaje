from oracleug.ora_db import Oradb, ODBType, ODBDirection


class Usuarios:
    __query1 = """ SELECT USUARIO,
                          GMAIL
                   FROM DBAFISICC.CACARNETUSUARIOTB
                   WHERE UPPER(USUARIO) = :USUARIO
                     AND ACTIVO = 1
                     AND LOGIN_USUARIO = 1
                     AND TIPO = 10"""

    def __init__(self):
        self.__con = Oradb()

    def get_usuario(self, usuario: str):
        parametros = [{
            "nombre": "usuario",
            "valor": usuario.strip().upper(),
            "tipo": ODBType.VARCHAR2,
            "direccion": ODBDirection.IN,
        }]
        return self.__con.execute_query(query=self.__query1, params=parametros)
