from oracleug.ora_db import Oradb, ODBType

db = Oradb()


class Empleados:
    def __init__(self):
        self.__script__ = """SELECT B.CORRELATIVO, B.NOMBRE, B.CODDEPA, B.DEPARTAMENTO, A.FOTO
                             FROM DBAFISICC.CACARNETBITB A,
                                  DBAFISICC.EMPLEADOSDYNAMICSVW B
                             WHERE A.CORRELATIVO = B.CORRELATIVO"""

        self.__coddepa__ = """SELECT B.CORRELATIVO, B.NOMBRE, B.CODDEPA, B.DEPARTAMENTO, A.FOTO
                              FROM DBAFISICC.CACARNETBITB A,
                                   DBAFISICC.EMPLEADOSDYNAMICSVW B
                              WHERE A.CORRELATIVO = B.CORRELATIVO
                                AND B.CODDEPA = :1"""

    def get_empleados(self):
        print("Ejecutando script para obtener empleados...")
        return db.execute_query(query=self.__script__, params=[])

    def get_empleados_coddepa(self, coddepa: str):
        print("Ejecutando script para obtener empleados...")
        parametros = [{
            "nombre": "coddepa",
            "valor": coddepa,
            "tipo": ODBType.VARCHAR2,
            "direccion": "IN",
        }]
        return db.execute_query(query=self.__coddepa__, params=parametros)
