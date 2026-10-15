import oracledb
import sys
import base64
from oracleug.oracle_settings import OracleSettings
from typing import List, Union


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
        self.pool = settings.pool
        self.dsn = settings.db_dns
        self.connection = None
        self.transaction = False
        self.module_name = sys.modules[__name__]

    def convert_camel_case(self, texto: str) -> str:
        """
        Convierte una cadena en formato snake_case a camelCase.

        Args:
            texto (str): La cadena en formato snake_case a convertir.

        Returns:
            str: La cadena convertida en formato camelCase.
        """
        palabras = texto.split("_")
        camel_case = "_".join(
            palabra.capitalize() for i, palabra in enumerate(palabras)
        )
        return camel_case

    def process_sys_refcursor(self, sys_refcursor):
        """
        Procesa un objeto SYS_REFCURSOR y devuelve una lista de diccionarios.

        Args:
            sys_refcursor: El objeto SYS_REFCURSOR a procesar.

        Returns:
            List[dict]: Una lista de diccionarios que representa las filas en el SYS_REFCURSOR.
        """
        cursor_results = []
        for row in sys_refcursor:
            row_dict = {}
            for i, col in enumerate(sys_refcursor.description):
                col_name = col[0]
                col_value = row[i]
                if isinstance(col_value, oracledb.LOB):
                    col_value = col_value.read()
                col_name_camel_case = self.convert_camel_case(col_name)
                row_dict[col_name_camel_case] = col_value

            cursor_results.append(row_dict)
        return cursor_results

    def get_dynamic_values(self, dynamic_var_names, dynamic_vars, dynamic_var_types):
        """
        Obtiene los valores dinámicos de las variables en base a sus nombres, valores y tipos.

        Args:
            dynamic_var_names (list): Lista de nombres de variables dinámicas.
            dynamic_vars (list): Lista de valores de variables dinámicas.
            dynamic_var_types (list): Lista de tipos de variables dinámicas.

        Returns:
            dict: Un diccionario que contiene los valores dinámicos indexados por nombre de variable.
        """
        dynamic_values = {}
        for name, dynamic_var, param_type in zip(
                dynamic_var_names, dynamic_vars, dynamic_var_types
        ):
            if param_type == ODBType.SYS_REFCURSOR:
                value = []
                cursor_var = dynamic_var.getvalue()
                if cursor_var is not None:
                    for row in cursor_var:
                        row_dict = dict(
                            zip([str(d[0]) for d in cursor_var.description], row)
                        )
                        converted_row_dict = {
                            self.convert_camel_case(k): v for k, v in row_dict.items()
                        }
                        value.append(converted_row_dict)
            elif param_type == ODBType.PSQLCODE:
                value = dynamic_var.getvalue()
            else:
                value = dynamic_var
            dynamic_values[name] = value
        return dynamic_values

    function_mappings = {
        ODBFunctionType.CURSOR: {
            "cursor_type": oracledb.CURSOR,
            "retval_key": "RETORNO_FUNCION",
            "default_retval": [],
            "process_result": True,
        },
        ODBFunctionType.STRING: {
            "cursor_type": oracledb.STRING,
            "retval_key": "RETORNO_FUNCION",
            "default_retval": None,
            "process_result": False,
        },
        ODBFunctionType.NUMBER: {
            "cursor_type": oracledb.NATIVE_INT,
            "retval_key": "RETORNO_FUNCION",
            "default_retval": None,
            "process_result": False,
        },
    }

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
                    self.host, "1521", service_name=self.service
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
                ora_param = {}
                send_param = []
                result = {}

                header_table = []
                result_table = []
                for param in params:
                    direc = param["direccion"]
                    if direc == "IN":
                        key = f'in_{(param["nombre"]).lower()}'
                        ora_param[key] = cursor.var(param['tipo'])
                        ora_param[key].setvalue(0, param["valor"])
                        setattr(self.module_name, key, ora_param[key])
                        send_param.append(getattr(self.module_name, key))
                    elif direc == "OUT":
                        key = f'out_{(param["nombre"]).lower()}'
                        ora_param[key] = cursor.var(param['tipo'])
                        setattr(self.module_name, key, ora_param[key])
                        send_param.append(getattr(self.module_name, key))
                    elif direc == "IN/OUT":
                        key = f'out_{(param["nombre"]).lower()}'
                        ora_param[key] = cursor.var(param['tipo'])
                        ora_param[key].setvalue(0, param["valor"])
                        setattr(self.module_name, key, ora_param[key])
                        send_param.append(getattr(self.module_name, key))
                cursor.callproc(procedure_name, send_param)
                for param in params:
                    key = f'out_{(param["nombre"]).lower()}'
                    if param['tipo'] == oracledb.CURSOR:
                        out_ret = ora_param.get(key)
                        if out_ret is None or out_ret.getvalue() is None:
                            result[param['nombre']] = []
                            continue
                        header_table = []
                        result_table = []
                        for nameColumn in out_ret.getvalue().description:
                            header_table.append(self.convert_camel_case(nameColumn[0]))
                        for row in out_ret.getvalue().fetchall():
                            row_table = {}
                            for i in range(len(header_table)):
                                row_table[header_table[i]] = row[i]
                            result_table.append(row_table)
                        result[param['nombre']] = result_table
                    elif param['direccion'] == "OUT" or param['direccion'] == "IN/OUT":
                        if key in ora_param:
                            result[param["nombre"]] = ora_param[key].getvalue()
                return result
        except (oracledb.DatabaseError, oracledb.InterfaceError) as e:
            if not self.transaction:
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
        try:
            if not self.transaction:
                self.connect()
            with self.connection.cursor() as cursor:
                ora_param = {}
                send_param = []
                result = {}

                header_table = []
                row_table = {}
                result_table = []

                for param in params:
                    direc = param["direccion"]
                    if direc == "IN":
                        key = f'in_{(param["nombre"]).lower()}'
                        ora_param[key] = cursor.var(param['tipo'])
                        ora_param[key].setvalue(0, param["valor"])
                        setattr(self.module_name, key, ora_param[key])
                        send_param.append(getattr(self.module_name, key))
                    elif direc == "OUT":
                        key = f'out_{(param["nombre"]).lower()}'
                        ora_param[key] = cursor.var(param['tipo'])
                        setattr(self.module_name, key, ora_param[key])
                        send_param.append(getattr(self.module_name, key))
                    elif direc == "IN/OUT":
                        key = f'out_{(param["nombre"]).lower()}'
                        ora_param[key] = cursor.var(param['tipo'])
                        ora_param[key].setvalue(0, param["valor"])
                        setattr(self.module_name, key, ora_param[key])
                        send_param.append(getattr(self.module_name, key))

                if type_function == 'SYS_REFCURSOR':
                    cursor_type = oracledb.CURSOR
                    retval_key = 'RETORNO_FUNCION'
                    default_retval = []
                    process_result = True
                if type_function == 'NUMBER' or type_function == 'INT':
                    cursor_type = oracledb.NATIVE_INT
                    retval_key = 'RETORNO_FUNCION'
                    default_retval = None
                    process_result = False

                if type_function == 'STRING':
                    cursor_type = oracledb.STRING
                    retval_key = 'RETORNO_FUNCION'
                    default_retval = None
                    process_result = False

                retval = cursor.callfunc(function_name, cursor_type, send_param)

                for param in params:
                    if param['tipo'] == oracledb.DB_TYPE_CURSOR:
                        key = f'out_{(param["nombre"]).lower()}'
                        out_ret = getattr(self.module_name, key)
                        for nameColumn in out_ret.getvalue().description:
                            header_table.append(self.convert_camel_case(nameColumn[0]))
                        for implicit_cursor in out_ret.values:
                            for row in implicit_cursor:
                                for i in range(len(header_table)):
                                    row_table[header_table[i]] = row[i]
                                result_table.append(row_table)
                        result[param['Nombre']] = result_table
                        delattr(self.module_name, key)
                    elif param['direccion'] == "OUT" or param['direccion'] == "IN/OUT":
                        key = f'out_{(param["nombre"]).lower()}'
                        ora_param[key] = getattr(self.module_name, key)
                        result[param["nombre"]] = ora_param[key].getvalue()
                        delattr(self.module_name, key)

                if process_result and retval is not None:
                    cursor_results = self.process_sys_refcursor(retval)
                else:
                    cursor_results = default_retval if retval is None else retval
                return {
                    retval_key: cursor_results,
                    **result
                }
        except (oracledb.DatabaseError, oracledb.InterfaceError) as e:
            if not self.transaction:
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
            if self.transaction is False:
                self.connect()
            with self.connection.cursor() as cursor:
                send_params = []
                dynamic_vars = []
                dynamic_var_names = []
                dynamic_var_types = []
                ora_psqlcode = {}

                for param in params:
                    param_name = param["nombre"]
                    param_value = param["valor"]
                    param_type = param["tipo"]
                    param_direction = param["direccion"]

                    if param_type == ODBType.DATE:
                        param_value = param_value
                    elif param_type == ODBType.SYS_REFCURSOR:
                        param_value = cursor.var(oracledb.CURSOR)
                    elif param_type in [
                        ODBType.INT,
                        ODBType.DECIMAL,
                        ODBType.NUMBER,
                        ODBType.VARCHAR2,
                    ]:
                        param_value = (
                            str(param_value) if param_value is not None else None
                        )
                    elif param_type == ODBType.VARCHARLIST:
                        param_value = oracledb.Array(
                            param_value, oracledb.STRING, 32767
                        )
                    elif param_type == ODBType.PSQLCODE:
                        ora_psqlcode["PSQLCODE"] = cursor.var(oracledb.DB_TYPE_VARCHAR)
                        ora_psqlcode["PSQLCODE"].setvalue(0, "0")
                    elif param_type == ODBType.BLOB:
                        if isinstance(param_value, str):
                            param_value = param_value.encode("utf-8")
                    # --- TRATAMIENTO LONG RAW / RAW PARA PARÁMETROS DE ENTRADA / SALIDA ---
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
                        dynamic_var_types.append(param_type)

                cursor.execute(query, send_params)

                # --- LECTURA DE RESULTADOS (SELECT) ---
                if cursor.description:
                    result = []
                    for row in cursor:
                        row_dict = {}
                        for i, col in enumerate(cursor.description):
                            col_name = col[0]
                            col_value = row[i]

                            # 1. Si es un LOB de Oracle (BLOB / CLOB)
                            if isinstance(col_value, oracledb.LOB):
                                col_value = col_value.read()

                            # 2. Si el valor resulta ser de tipo bytes (LONG RAW, RAW o BLOB leídos)
                            if isinstance(col_value, bytes):
                                col_value = base64.b64encode(col_value).decode("utf-8")

                            col_name_camel_case = self.convert_camel_case(col_name)
                            row_dict[col_name_camel_case] = col_value
                        result.append(row_dict)
                    return result

                # --- LECTURA DE PARÁMETROS OUT / IN/OUT (si no fue un SELECT) ---
                elif dynamic_vars:
                    out_results = {}
                    for name, var, p_type in zip(
                            dynamic_var_names, dynamic_vars, dynamic_var_types
                    ):
                        val = var.getvalue()

                        # Convertir LOB o bytes provenientes de parámetros OUT
                        if isinstance(val, oracledb.LOB):
                            val = val.read()
                        if isinstance(val, bytes):
                            val = base64.b64encode(val).decode("utf-8")

                        out_results[self.convert_camel_case(name)] = val

                    return [out_results]

                else:
                    return None

        except (oracledb.DatabaseError, oracledb.InterfaceError) as e:
            if self.transaction is False:
                self.connection.rollback()
            return {"OOPS": str(e)}
        finally:
            if self.transaction is False:
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
                send_params = []
                dynamic_vars = []
                dynamic_var_names = []
                dynamic_var_types = []
                ora_psqlcode = {}

                for param in params:
                    param_name = param["nombre"]
                    param_value = param["valor"]
                    param_type = param["tipo"]
                    param_direction = param["direccion"]

                    if param_type == ODBType.DATE:
                        param_value = param_value
                    elif param_type == ODBType.SYS_REFCURSOR:
                        param_value = cursor.var(oracledb.CURSOR)
                    elif param_type in [
                        ODBType.INT,
                        ODBType.DECIMAL,
                        ODBType.NUMBER,
                        ODBType.VARCHAR2,
                    ]:
                        param_value = (
                            str(param_value) if param_value is not None else None
                        )
                    elif param_type == ODBType.VARCHARLIST:
                        param_value = oracledb.Array(
                            param_value, oracledb.STRING, 32767
                        )
                    elif param_type == ODBType.PSQLCODE:
                        ora_psqlcode["PSQLCODE"] = cursor.var(oracledb.DB_TYPE_VARCHAR)
                        ora_psqlcode["PSQLCODE"].setvalue(0, "0")
                    elif param_type == ODBType.BLOB:
                        param_value = bytes(param_value, "utf-8")

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
                        dynamic_var_types.append(param_type)

                cursor.execute(query, send_params)

                if cursor.description:
                    result = []
                    for row in cursor:
                        row_dict = {}
                        for i, col in enumerate(cursor.description):
                            col_name = col[0]
                            col_value = row[i]
                            if isinstance(col_value, oracledb.LOB):
                                col_value = col_value.read()
                            col_name_camel_case = self.convert_camel_case(col_name)
                            row_dict[col_name_camel_case] = col_value
                        result.append(row_dict)
                    return result
                else:
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
