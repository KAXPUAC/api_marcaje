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

    # Nuevo script optimizado con UNION ALL para aprovechar índices según el parámetro provisto
    __usuario_o_correlativo = """
                              SELECT B.CODPERS,
                                     A.USUARIO,
                                     B.GRACAD,
                                     B.NOMBRE1 || ' ' || B.NOMBRE2     AS NOMBRES,
                                     B.APELLIDO1 || ' ' || B.APELLIDO2 AS APELLIDOS,
                                     A.GMAIL                           AS EMAIL,
                                     A.GMAIL,
                                     A.GMAIL2,
                                     A.CORRELATIVO
                              FROM DBAFISICC.CACARNETUSUARIOTB A
                                       JOIN DBAFISICC.NOPERSONALTB B ON B.CORRELATIVO = A.CORRELATIVO
                              WHERE A.CORRELATIVO = :correlativo
                                AND :correlativo IS NOT NULL
                                AND A.TIPO = 1
                                AND A.ACTIVO = 1
                                AND B.STATUS <> 'B'

                              UNION ALL

                              SELECT B.CODPERS,
                                     A.USUARIO,
                                     B.GRACAD,
                                     B.NOMBRE1 || ' ' || B.NOMBRE2     AS NOMBRES,
                                     B.APELLIDO1 || ' ' || B.APELLIDO2 AS APELLIDOS,
                                     A.GMAIL                           AS EMAIL,
                                     A.GMAIL,
                                     A.GMAIL2,
                                     A.CORRELATIVO
                              FROM DBAFISICC.CACARNETUSUARIOTB A
                                       JOIN DBAFISICC.NOPERSONALTB B ON B.CORRELATIVO = A.CORRELATIVO
                              WHERE A.USUARIO = :usuario
                                AND :correlativo IS NULL
                                AND :usuario IS NOT NULL
                                AND A.TIPO = 1
                                AND A.ACTIVO = 1
                                AND B.STATUS <> 'B' \
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

    def get_usuario_o_correlativo(self, correlativo: int = None, usuario: str = None):
        """
        Busca un usuario por correlativo o por nombre de usuario.
        Se puede enviar cualquiera de los dos parámetros.
        """
        parametros = [
            {
                "nombre": "correlativo",
                "valor": int(correlativo) if correlativo is not None else None,
                "tipo": ODBType.INT,
                "direccion": "IN",
            },
            {
                "nombre": "usuario",
                "valor": usuario,
                "tipo": ODBType.VARCHAR2,
                "direccion": "IN",
            }
        ]
        return self.__con.execute_query(query=self.__usuario_o_correlativo, params=parametros)
