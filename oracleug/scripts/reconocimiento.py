from typing import Optional

from oracleug.ora_db import ODBType, Oradb


class Reconocimiento:
    """Consultas Oracle utilizadas por los métodos de reconocimiento facial."""

    __datos_usuario = """
                SELECT DISTINCT B.CODPERS,
                       A.USUARIO,
                       B.GRACAD,
                       B.NOMBRE1 || ' ' || B.NOMBRE2     AS NOMBRES,
                       B.APELLIDO1 || ' ' || B.APELLIDO2 AS APELLIDOS,
                       A.GMAIL                           AS EMAIL,
                       A.GMAIL,
                       A.GMAIL2,
                       A.CORRELATIVO,
                       D.CODDEPA,
                       D.DEPARTAMENTO,
                       C.NOMBREPILA,
                       C.DPI,
                       C.CARNET,
                       C.CARNET1,
                       C.CARNET2
                FROM DBAFISICC.CACARNETUSUARIOTB A
                         JOIN DBAFISICC.NOPERSONALTB B
                              ON B.CORRELATIVO = A.CORRELATIVO
                         LEFT JOIN DBAFISICC.EMPLEADOSDYNAMICSVW D
                                   ON D.CORRELATIVO = A.CORRELATIVO
                         LEFT JOIN DBAFISICC.CACARNETBITB C
                                   ON C.CORRELATIVO = A.CORRELATIVO
                WHERE A.CORRELATIVO = :correlativo
                  AND A.TIPO = 1
                  AND A.ACTIVO = 1
                  AND A.LOGIN_USUARIO = 1
                  AND B.STATUS <> 'B'
                """

    def __init__(self):
        self.__con = Oradb()

    def get_datos_usuario(self, correlativo: str) -> Optional[dict]:
        parametros = [{
            "nombre": "correlativo",
            "valor": int(correlativo),
            "tipo": ODBType.INT,
            "direccion": "IN",
        }]
        resultado = self.__con.execute_query(
            query=self.__datos_usuario,
            params=parametros,
        )

        if isinstance(resultado, dict):
            if any(str(key).upper() == "OOPS" for key in resultado):
                raise RuntimeError("Error consultando los datos del usuario")
            filas = [resultado]
        elif isinstance(resultado, list):
            filas = resultado
        else:
            filas = []

        if not filas:
            return None

        return {
            key: filas[0].get(key)
            for key in (
                "Codpers",
                "Usuario",
                "Gracad",
                "Nombres",
                "Apellidos",
                "Email",
                "Gmail",
                "Gmail2",
                "Correlativo",
                "Coddepa",
                "Departamento",
                "Nombrepila",
                "Dpi",
                "Carnet",
                "Carnet1",
                "Carnet2",
            )
        }
