from oracleug.ora_db import Oradb, ODBType


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

    __info = """SELECT NOMBREPILA, DPI, CARNET
                FROM DBAFISICC.CACARNETBITB
                WHERE CORRELATIVO = :1"""

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
