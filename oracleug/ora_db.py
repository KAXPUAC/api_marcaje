import base64
import oracledb
from typing import List, Union

from oracleug.oracle_settings import OracleSettings


class ODBType:
    """Clase que define los tipos de datos de Oracle"""

    VARCHAR2 = "VARCHAR2"
    DECIMAL = "NUMBER"
    SYS_REFCURSOR = "CURSOR"
    PSQLCODE = "PSQLCODE"
    NUMBER = "NUMBER"
    DATE = "DATE"
    INT = "INTEGER"
    VARCHARLIST = "ARRAYVARCHAR2"
    BLOB = "BLOB"
    LONG_RAW = "LONG_RAW"
    RAW = "RAW"


class ODBDirection:
    """Clase que indica si el parametro es de salida, entrada o ambos"""
    IN = 'IN'
    OUT = 'OUT'
    INOUT = 'IN/OUT'


class ODBFunctionType:
    """Clase que define los tipos de funciones de Oracle"""

    NUMBER = "INT"
    STRING = "STRING"
    CURSOR = "CURSOR"


# Configuración de los tipos de retorno de las funciones Oracle.
_CURSOR_FN = {
    "cursor_type": oracledb.CURSOR,
    "retval_key": "RETORNO_FUNCION",
    "default_retval": [],
    "process_result": True,
}
_STRING_FN = {
    "cursor_type": oracledb.STRING,
    "retval_key": "RETORNO_FUNCION",
    "default_retval": None,
    "process_result": False,
}
_NUMBER_FN = {
    "cursor_type": oracledb.NATIVE_INT,
    "retval_key": "RETORNO_FUNCION",
    "default_retval": None,
    "process_result": False,
}

_FUNCTION_TYPES = {
    ODBFunctionType.CURSOR: _CURSOR_FN,
    "SYS_REFCURSOR": _CURSOR_FN,
    ODBFunctionType.STRING: _STRING_FN,
    ODBFunctionType.NUMBER: _NUMBER_FN,
    "NUMBER": _NUMBER_FN,
}


class Oradb:
    """
    Clase que proporciona métodos para conectar y administrar una conexión a una base de datos Oracle.

    Attributes:
        db_user (str): Nombre de usuario para la conexión a la base de datos.
        db_pass (str): Contraseña para la conexión a la base de datos.
        db_dns (str): DSN (Data Source Name) para la conexión a la base de datos.
        min_conns (int): Número mínimo de conexiones en el pool.
        max_conns (int): Número máximo de conexiones en el pool.
        incr_conns (int): Incremento de conexiones en el pool.
        host (str): Host de la base de datos.
        service (str): Nombre del servicio de la base de datos.
        pool (obj): Pool de conexiones Oracle.
        connection (obj): Conexión activa a la base de datos.
        transaction (bool): Indica si la conexión está en una transacción o no.
    """

    def __init__(self):
        """
        Inicializa una instancia de OracleDBConnector y configura los atributos necesarios para la conexión.
        """
        settings = OracleSettings()
        self.db_user = settings.db_user
        self.db_pass = settings.db_pass
        self.db_dns = settings.db_dns
        self.min_conns = settings.min_conns
        self.max_conns = settings.max_conns
        self.incr_conns = settings.incr_conns
        self.host = settings.db_host
        self.service = settings.db_name
        self.db_port = settings.db_port
        self.dsn = settings.db_dns
        self.pool = None
        self.connection = None
        self.transaction = False

    def convert_camel_case(self, texto: str) -> str:
        """
        Convierte una cadena en formato snake_case a camelCase.

        Args:
            texto (str): La cadena en formato snake_case a convertir.

        Returns:
            str: La cadena convertida en formato camelCase.
        """
        palabras = texto.split("_")
        camel_case = "_".join(palabra.capitalize() for palabra in palabras)
        return camel_case

    def process_sys_refcursor(self, sys_refcursor):
        """
        Procesa un objeto SYS_REFCURSOR y devuelve una lista de diccionarios.

        Args:
            sys_refcursor: El objeto SYS_REFCURSOR a procesar.

        Returns:
            List[dict]: Una lista de diccionarios que representa las filas en el SYS_REFCURSOR.
        """
        header = [self.convert_camel_case(col[0]) for col in sys_refcursor.description]
        cursor_results = []
        for row in sys_refcursor:
            row_dict = {}
            for i, col_name in enumerate(header):
                col_value = row[i]
                if isinstance(col_value, oracledb.LOB):
                    col_value = col_value.read()
                row_dict[col_name] = col_value
            cursor_results.append(row_dict)
        return cursor_results

    @staticmethod
    def _convert_value(value):
        """Convierte LOB a su contenido y bytes a base64."""
        if isinstance(value, oracledb.LOB):
            value = value.read()
        if isinstance(value, bytes):
            value = base64.b64encode(value).decode("utf-8")
        return value

    def _read_rows(self, cursor) -> List[dict]:
        """Lee las filas de un cursor y las devuelve como lista de diccionarios."""
        header = [self.convert_camel_case(col[0]) for col in cursor.description]
        return [
            {header[i]: self._convert_value(row[i]) for i in range(len(header))}
            for row in cursor
        ]

    def _process_cursor(self, cursor_var) -> List[dict]:
        """Procesa una variable de cursor OUT y devuelve sus filas."""
        if cursor_var is None:
            return []
        value = cursor_var.getvalue()
        if value is None:
            return []
        header = [self.convert_camel_case(col[0]) for col in value.description]
        return [dict(zip(header, row)) for row in value.fetchall()]

    @staticmethod
    def _bind_params(cursor, params):
        """
        Crea las variables de cursor para cada parámetro y devuelve
        (lista de parámetros a enviar, diccionario de variables por clave).
        """
        ora_param = {}
        send_param = []
        for param in params:
            direc = param["direccion"]
            nombre = param["nombre"].lower()
            if direc == "IN":
                key = f"in_{nombre}"
                var = cursor.var(param["tipo"])
                var.setvalue(0, param["valor"])
            elif direc == "OUT":
                key = f"out_{nombre}"
                var = cursor.var(param["tipo"])
            elif direc == "IN/OUT":
                key = f"out_{nombre}"
                var = cursor.var(param["tipo"])
                var.setvalue(0, param["valor"])
            else:
                continue
            ora_param[key] = var
            send_param.append(var)
        return send_param, ora_param

    @staticmethod
    def _process_query_params(cursor, params):
        """
        Procesa los parámetros de una consulta y devuelve
        (lista de parámetros a enviar, variables dinámicas, nombres de variables dinámicas).
        """
        send_params = []
        dynamic_vars = []
        dynamic_var_names = []
        ora_psqlcode = {}

        for param in params:
            param_name = param["nombre"]
            param_value = param["valor"]
            param_type = param["tipo"]
            param_direction = param["direccion"]

            if param_type == ODBType.DATE:
                pass  # sin conversión
            elif param_type == ODBType.SYS_REFCURSOR:
                param_value = cursor.var(oracledb.CURSOR)
            elif param_type in [
                ODBType.INT,
                ODBType.DECIMAL,
                ODBType.NUMBER,
                ODBType.VARCHAR2,
            ]:
                param_value = str(param_value) if param_value is not None else None
            elif param_type == ODBType.VARCHARLIST:
                param_value = oracledb.Array(param_value, oracledb.STRING, 32767)
            elif param_type == ODBType.PSQLCODE:
                ora_psqlcode["PSQLCODE"] = cursor.var(oracledb.DB_TYPE_VARCHAR)
                ora_psqlcode["PSQLCODE"].setvalue(0, "0")
            elif param_type == ODBType.BLOB:
                if isinstance(param_value, str):
                    param_value = param_value.encode("utf-8")
            elif param_type in [ODBType.LONG_RAW, ODBType.RAW]:
                if param_direction == "IN":
                    if isinstance(param_value, str):
                        param_value = param_value.encode("utf-8")
                elif param_direction in ["OUT", "IN/OUT"]:
                    db_type = (
                        oracledb.DB_TYPE_LONG_RAW
                        if param_type == ODBType.LONG_RAW
                        else oracledb.DB_TYPE_RAW
                    )
                    param_value = cursor.var(db_type)

            if param_direction == "IN":
                send_params.append(param_value)
            if param_direction in ["OUT", "IN/OUT"]:
                dynamic_var = (
                    ora_psqlcode["PSQLCODE"]
                    if param_type == ODBType.PSQLCODE
                    else param_value
                )
                send_params.append(dynamic_var)
                dynamic_vars.append(dynamic_var)
                dynamic_var_names.append(param_name)

        return send_params, dynamic_vars, dynamic_var_names

    def create_pool(self):
        """
        Crea un pool de conexiones Oracle.

        Returns:
            None

        Raises:
            ConnectionError: Si ocurre un error al crear el pool de conexiones.
        """
        try:
            self.pool = oracledb.create_pool(
                user=self.db_user,
                password=self.db_pass,
                dsn=self.db_dns,
                min=self.min_conns,
                max=self.max_conns,
                increment=self.incr_conns,
            )
        except oracledb.DatabaseError as e:
            raise ConnectionError("Error al crear el pool de conexiones: " + str(e))

    def close_connection(self):
        """
        Cierra la conexión activa.

        Returns:
            None
        """
        if self.connection is not None:
            if self.transaction and self.pool is not None:
                self.pool.release(self.connection)
            else:
                self.connection.close()
            self.connection = None
            self.transaction = False

    def connect(self, transaction=False):
        """
        Establece una conexión utilizando el pool de conexiones si es una transacción,
        o una conexión directa si no es una transacción.

        Returns:
            None

        Raises:
            ConnectionError: Si ocurre un error al establecer la conexión.
        """
        try:
            if transaction:
                if self.pool is None:
                    self.create_pool()
                self.connection = self.pool.acquire()
            else:
                self.dsn = oracledb.makedsn(
                    self.host, self.db_port, service_name=self.service
                )
                self.connection = oracledb.connect(
                    user=self.db_user, password=self.db_pass, dsn=self.dsn
                )
            self.transaction = transaction
        except oracledb.DatabaseError as e:
            raise ConnectionError("Error al establecer la conexión: " + str(e))

    def commit(self):
        """
        Realiza un commit en la conexión activa.

        Returns:
            None
        """
        if self.connection is not None:
            self.connection.commit()

    def rollback(self):
        """
        Realiza un rollback en la conexión activa.

        Returns:
            None
        """
        if self.connection is not None:
            self.connection.rollback()

    def begin_transaction(self):
        """
        Inicia una transacción de base de datos, esto abre la conexión a la base
        de datos y la mantiene así hasta que se ejecute un commit o rollback

        Returns:
            None
        """
        if self.connection is None:
            self.connect(transaction=True)
            self.connection.begin()

    def commit_transaction(self):
        """
        Confirma las transacciones ejecutadas en la base de datos y cierra la conexión

        Returns:
            None
        """
        if self.connection is not None:
            self.connection.commit()
            self.close_connection()

    def rollback_transaction(self):
        """
        Revierte las transacciones ejecutadas en la base de datos y cierra la conexión

        Returns:
            None
        """
        if self.connection is not None:
            self.connection.rollback()
            self.close_connection()

    def execute_procedure(
            self, procedure_name: str, params: List[dict]
    ) -> Union[dict, None]:
        """
        Ejecuta un procedimiento almacenado en Oracle con los parámetros proporcionados.

        Args:
            procedure_name (str): Nombre del procedimiento almacenado a ejecutar.
            params (List[dict]): Lista de diccionarios que contienen información de los parámetros.
                Cada diccionario debe contener las siguientes claves:
                - "nombre": Nombre del parámetro.
                - "valor": Valor del parámetro.
                - "tipo": Tipo de dato del parámetro (debe ser uno de los valores definidos en la clase ODBType).
                - "direccion": Dirección del parámetro (debe ser uno de los valores: "IN", "OUT", "IN/OUT").

        Returns:
            Union[dict, None]: Un diccionario con los valores de los parámetros de salida o None si ocurre un error.

        Raises:
            ConnectionError: Si ocurre un error al crear o establecer la conexión con la base de datos.
        """
        try:
            if not self.transaction:
                self.connect()
            with self.connection.cursor() as cursor:
                send_param, ora_param = self._bind_params(cursor, params)
                cursor.callproc(procedure_name, send_param)

                result = {}
                for param in params:
                    key = f'out_{param["nombre"].lower()}'
                    if param["tipo"] == oracledb.DB_TYPE_CURSOR:
                        result[param["nombre"]] = self._process_cursor(ora_param.get(key))
                    elif param["direccion"] in ("OUT", "IN/OUT"):
                        if key in ora_param:
                            result[param["nombre"]] = ora_param[key].getvalue()
                return result
        except (oracledb.DatabaseError, oracledb.InterfaceError) as e:
            if not self.transaction and self.connection is not None:
                self.connection.rollback()
            return {"OOPS": str(e)}
        finally:
            if not self.transaction:
                self.commit()
                self.close_connection()

    def execute_function(
            self, function_name: str, params: List[dict], type_function: str
    ) -> Union[dict, None]:
        """
        Ejecuta una función en Oracle con los parámetros proporcionados.

        Args:
            function_name (str): Nombre de la función a ejecutar.
            params (List[dict]): Lista de diccionarios que contienen información de los parámetros.
                Cada diccionario debe contener las siguientes claves:
                - "nombre": Nombre del parámetro.
                - "valor": Valor del parámetro.
                - "tipo": Tipo de dato del parámetro (debe ser uno de los valores definidos en la clase ODBType).
                - "direccion": Dirección del parámetro (debe ser uno de los valores: "IN", "OUT", "IN/OUT").
            type_function (str): Tipo de función a ejecutar NUMBER, STRING, SYS_REFCURSOR.

        Returns:
            Union[dict, None]: Un diccionario con los valores de retorno y los parámetros de salida o None si ocurre un error.

        Raises:
            ConnectionError: Si ocurre un error al crear o establecer la conexión con la base de datos.
        """
        config = _FUNCTION_TYPES.get(type_function)
        if config is None:
            raise ValueError(f"Tipo de función no soportado: {type_function}")

        try:
            if not self.transaction:
                self.connect()
            with self.connection.cursor() as cursor:
                send_param, ora_param = self._bind_params(cursor, params)
                retval = cursor.callfunc(function_name, config["cursor_type"], send_param)

                result = {}
                for param in params:
                    key = f'out_{param["nombre"].lower()}'
                    if param["tipo"] == oracledb.DB_TYPE_CURSOR:
                        result[param["nombre"]] = self._process_cursor(ora_param.get(key))
                    elif param["direccion"] in ("OUT", "IN/OUT"):
                        if key in ora_param:
                            result[param["nombre"]] = ora_param[key].getvalue()

                if config["process_result"] and retval is not None:
                    cursor_results = self.process_sys_refcursor(retval)
                else:
                    cursor_results = config["default_retval"] if retval is None else retval
                return {config["retval_key"]: cursor_results, **result}
        except (oracledb.DatabaseError, oracledb.InterfaceError) as e:
            if not self.transaction and self.connection is not None:
                self.connection.rollback()
            return {"OOPS": str(e)}
        finally:
            if not self.transaction:
                self.commit()
                self.close_connection()

    def execute_query(self, query: str, params: List[dict]) -> Union[List[dict], None]:
        """
        Ejecuta una consulta SQL en Oracle con los parámetros proporcionados.
        """
        try:
            if not self.transaction:
                self.connect()
            with self.connection.cursor() as cursor:
                send_params, dynamic_vars, dynamic_var_names = self._process_query_params(cursor, params)
                cursor.execute(query, send_params)

                if cursor.description:
                    return self._read_rows(cursor)

                if dynamic_vars:
                    out_results = {}
                    for name, var in zip(dynamic_var_names, dynamic_vars):
                        out_results[self.convert_camel_case(name)] = self._convert_value(var.getvalue())
                    return [out_results]

                return None
        except (oracledb.DatabaseError, oracledb.InterfaceError) as e:
            if not self.transaction and self.connection is not None:
                self.connection.rollback()
            return {"OOPS": str(e)}
        finally:
            if not self.transaction:
                self.commit()
                self.close_connection()

    def execute_query_with_transaction(
            self, query: str, params: List[dict]
    ) -> Union[List[dict], None]:
        """
        Ejecuta una consulta SQL en Oracle con los parámetros proporcionados dentro de una transacción.

        Args:
            query (str): Consulta SQL a ejecutar.
            params (List[dict]): Lista de diccionarios que contienen información de los parámetros.
                Cada diccionario debe contener las siguientes claves:
                - "nombre": Nombre del parámetro.
                - "valor": Valor del parámetro.
                - "tipo": Tipo de dato del parámetro (debe ser uno de los valores definidos en la clase ODBType).
                - "direccion": Dirección del parámetro (debe ser uno de los valores: "IN", "OUT", "IN/OUT").

        Returns:
            Union[List[dict], None]: Una lista de diccionarios que representa las filas resultantes de la consulta,
            o None si ocurre un error.

        Raises:
            ConnectionError: Si ocurre un error al crear o establecer la conexión con la base de datos.
        """
        try:
            self.begin_transaction()

            with self.connection.cursor() as cursor:
                send_params, _, _ = self._process_query_params(cursor, params)
                cursor.execute(query, send_params)

                if cursor.description:
                    return self._read_rows(cursor)
                return None
        except (oracledb.DatabaseError, oracledb.InterfaceError) as e:
            self.rollback_transaction()
            return {"OOPS": str(e)}
        finally:
            self.commit_transaction()

    def disconnect(self):
        """
        Cierra la conexión del pool de conexiones.

        Returns:
            None
        """
        if self.pool is not None:
            self.pool.close()
            self.pool = None
