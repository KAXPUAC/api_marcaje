from typing import Optional

from oracleug.ora_db import ODBType, Oradb


class Reconocimiento:
    """Consultas Oracle utilizadas por los métodos de reconocimiento facial."""

    __datos_usuario = """
                SELECT DISTINCT
                       B.CODPERS,
                       A.USUARIO,
                       B.GRACAD,
                       B.NOMBRE1 || ' ' || B.NOMBRE2     AS NOMBRES,
                       B.APELLIDO1 || ' ' || B.APELLIDO2 AS APELLIDOS,
                       A.GMAIL                           AS EMAIL,
                       A.GMAIL,
                       A.GMAIL2,
                       A.TIPO,
                       C.CORRELATIVO,
                       D.CODDEPA,
                       D.DEPARTAMENTO,
                       C.NOMBREPILA,
                       C.DPI,
                       C.CARNET,
                       C.CARNET1,
                       C.CARNET2,
                       CASE A.TIPO
                           WHEN 1 THEN 'Administrativo'
                           WHEN 2 THEN 'Docente'
                           WHEN 3 THEN 'Tutor'
                           WHEN 4 THEN 'Alumno'
                           ELSE 'Plataforma no definida'
                       END AS TIPO_USUARIO
                FROM DBAFISICC.CACARNETBITB C
                         LEFT JOIN DBAFISICC.NOPERSONALTB B
                                   ON B.CORRELATIVO = C.CORRELATIVO
                         LEFT JOIN DBAFISICC.EMPLEADOSDYNAMICSVW D
                                   ON D.CORRELATIVO = C.CORRELATIVO
                         LEFT JOIN DBAFISICC.CACARNETUSUARIOTB A
                                   ON A.CORRELATIVO = C.CORRELATIVO
                WHERE C.CORRELATIVO = :correlativo
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

        usuario_filas = [
            fila for fila in filas
            if fila.get("Tipo") is not None
        ]
        usuario_principal = usuario_filas[0] if usuario_filas else filas[0]

        datos_usuario = {
            key: filas[0].get(key)
            for key in (
                "Codpers",
                "Gracad",
                "Nombres",
                "Apellidos",
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
        datos_usuario.update({
            "Usuario": usuario_principal.get("Usuario"),
            "Email": usuario_principal.get("Email"),
            "Gmail": usuario_principal.get("Gmail"),
            "Gmail2": usuario_principal.get("Gmail2"),
            "TipoUsuario": usuario_principal.get("Tipo_Usuario"),
        })
        datos_usuario["Usuarios"] = [
            {
                "Tipo": fila.get("Tipo"),
                "TipoUsuario": fila.get("Tipo_Usuario"),
                "Usuario": fila.get("Usuario"),
                "Email": fila.get("Email"),
                "Gmail": fila.get("Gmail"),
                "Gmail2": fila.get("Gmail2"),
            }
            for fila in usuario_filas
        ]
        return datos_usuario
