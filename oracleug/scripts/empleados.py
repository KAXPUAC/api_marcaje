import base64

from oracleug.ora_db import ODBType, Oradb


class Empleados:
    __script = """SELECT B.CORRELATIVO, B.NOMBRE, B.CODDEPA, B.DEPARTAMENTO, A.FOTO
                  FROM DBAFISICC.CACARNETBITB A,
                       DBAFISICC.EMPLEADOSDYNAMICSVW B
                  WHERE A.CORRELATIVO = B.CORRELATIVO"""

    __coddepa = """SELECT B.CORRELATIVO, B.NOMBRE, B.CODDEPA, B.DEPARTAMENTO, A.FOTO
                   FROM DBAFISICC.CACARNETBITB A,
                        DBAFISICC.EMPLEADOSDYNAMICSVW B
                   WHERE A.CORRELATIVO = B.CORRELATIVO
                     AND B.CODDEPA = :1"""

    __info = """SELECT NOMBREPILA, DPI, CARNET, CORRELATIVO
                FROM DBAFISICC.CACARNETBITB
                WHERE CORRELATIVO = :1"""

    __foto_por_correlativo = """
                SELECT FOTO
                FROM DBAFISICC.CACARNETBITB
                WHERE CORRELATIVO = :1
                """

    __usuario_por_correlativo = """
                SELECT B.CODPERS,
                       A.USUARIO,
                       B.GRACAD,
                       B.NOMBRE1 || ' ' || B.NOMBRE2     AS NOMBRES,
                       B.APELLIDO1 || ' ' || B.APELLIDO2 AS APELLIDOS,
                       A.GMAIL                           AS EMAIL,
                       A.GMAIL,
                       A.GMAIL2,
                       A.CORRELATIVO,
                       D.CODDEPA,
                       D.DEPARTAMENTO
                FROM DBAFISICC.CACARNETUSUARIOTB A
                         JOIN DBAFISICC.NOPERSONALTB B ON B.CORRELATIVO = A.CORRELATIVO
                         LEFT JOIN DBAFISICC.EMPLEADOSDYNAMICSVW D ON D.CORRELATIVO = A.CORRELATIVO
                WHERE A.CORRELATIVO = :correlativo
                  AND A.TIPO = 1
                  AND A.ACTIVO = 1
                  AND A.LOGIN_USUARIO = 1
                  AND B.STATUS <> 'B'
                """

    __usuario_por_usuario = """
                SELECT B.CODPERS,
                       A.USUARIO,
                       B.GRACAD,
                       B.NOMBRE1 || ' ' || B.NOMBRE2     AS NOMBRES,
                       B.APELLIDO1 || ' ' || B.APELLIDO2 AS APELLIDOS,
                       A.GMAIL                           AS EMAIL,
                       A.GMAIL,
                       A.GMAIL2,
                       A.CORRELATIVO,
                       D.CODDEPA,
                       D.DEPARTAMENTO
                FROM DBAFISICC.CACARNETUSUARIOTB A
                         JOIN DBAFISICC.NOPERSONALTB B ON B.CORRELATIVO = A.CORRELATIVO
                         LEFT JOIN DBAFISICC.EMPLEADOSDYNAMICSVW D ON D.CORRELATIVO = A.CORRELATIVO
                WHERE UPPER(A.USUARIO) = UPPER(:usuario)
                  AND A.TIPO = 1
                  AND A.ACTIVO = 1
                  AND A.LOGIN_USUARIO = 1
                  AND B.STATUS <> 'B'
                """

    __email = """
                SELECT B.CODPERS,
                       A.USUARIO,
                       B.GRACAD,
                       B.NOMBRE1 || ' ' || B.NOMBRE2     AS NOMBRES,
                       B.APELLIDO1 || ' ' || B.APELLIDO2 AS APELLIDOS,
                       A.GMAIL                           AS EMAIL,
                       A.GMAIL,
                       A.GMAIL2,
                       A.CORRELATIVO,
                       D.CODDEPA,
                       D.DEPARTAMENTO
                FROM DBAFISICC.CACARNETUSUARIOTB A
                         JOIN DBAFISICC.NOPERSONALTB B ON B.CORRELATIVO = A.CORRELATIVO
                         LEFT JOIN DBAFISICC.EMPLEADOSDYNAMICSVW D ON D.CORRELATIVO = A.CORRELATIVO
                WHERE UPPER(TRIM(A.GMAIL)) = UPPER(TRIM(:email))
                  AND A.TIPO = 1
                  AND A.ACTIVO = 1
                  AND A.LOGIN_GOOGLE = 1
                  AND B.STATUS <> 'B'
                """

    def __init__(self):
        self.__con = Oradb()

    def get_empleados(self):
        return self.__con.execute_query(query=self.__script, params=[])

    def get_empleados_coddepa(self, coddepa: str):
        parametros = [{
            "nombre": "coddepa",
            "valor": coddepa,
            "tipo": ODBType.VARCHAR2,
            "direccion": "IN",
        }]
        return self.__con.execute_query(query=self.__coddepa, params=parametros)

    def get_empleado_info(self, correlativo: str):
        parametros = [{
            "nombre": "correlativo",
            "valor": int(correlativo),
            "tipo": ODBType.INT,
            "direccion": "IN",
        }]
        return self.__con.execute_query(query=self.__info, params=parametros)

    def get_foto_bytes(self, correlativo: int) -> bytes | None:
        """Obtiene la foto LONG RAW del usuario como bytes."""
        parametros = [{
            "nombre": "correlativo",
            "valor": int(correlativo),
            "tipo": ODBType.INT,
            "direccion": "IN",
        }]
        resultado = self.__con.execute_query(
            query=self.__foto_por_correlativo,
            params=parametros,
        )

        if not isinstance(resultado, list) or not resultado:
            return None

        foto = resultado[0].get("Foto")
        if foto is None:
            return None
        if isinstance(foto, bytes):
            return foto
        if isinstance(foto, str):
            return base64.b64decode(foto)
        raise TypeError("El campo FOTO no contiene un valor binario válido")

    def get_foto_base64(self, correlativo: int) -> str | None:
        """Obtiene la foto LONG RAW del usuario codificada en base64."""
        foto = self.get_foto_bytes(correlativo)
        return base64.b64encode(foto).decode("ascii") if foto else None

    def get_usuario_por_correlativo(self, correlativo: int):
        parametros = [{
            "nombre": "correlativo",
            "valor": int(correlativo),
            "tipo": ODBType.INT,
            "direccion": "IN",
        }]
        return self.__con.execute_query(query=self.__usuario_por_correlativo, params=parametros)

    def get_usuario_por_usuario(self, usuario: str):
        parametros = [{
            "nombre": "usuario",
            "valor": usuario.strip().upper(),
            "tipo": ODBType.VARCHAR2,
            "direccion": "IN",
        }]
        return self.__con.execute_query(query=self.__usuario_por_usuario, params=parametros)

    def get_usuario_por_email(self, email: str):
        parametros = [{
            "nombre": "email",
            "valor": email.strip(),
            "tipo": ODBType.VARCHAR2,
            "direccion": "IN",
        }]
        return self.__con.execute_query(query=self.__email, params=parametros)
