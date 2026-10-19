import os
from dotenv import load_dotenv
from oracleug.utils.generic import to_int

load_dotenv(override=True)

from pathlib import Path

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


class OracleSettings:
    def __init__(self):
        if not os.path.exists(env_path):
            raise Exception("No se encontró el archivo de entorno")
        try:
            # oracle credentials
            self.db_name: str = os.getenv("DB_NAME_ORA", '')
            self.db_user: str = os.getenv("DB_USER_ORA", '')
            self.db_pass: str = os.getenv("DB_PASS_ORA", '')
            self.db_host: str = os.getenv("DB_HOST_ORA", '')
            self.db_port: int = to_int(os.getenv("DB_PORT_ORA", '1521'))
            self.db_dns: str = os.getenv("DB_DNS_ORA", '')
            self.min_conns: int = to_int(os.getenv("DB_MIN_CONNS_ORA", ''))
            self.max_conns: int = to_int(os.getenv("DB_MAX_CONNS_ORA", ''))
            self.incr_conns: int = to_int(os.getenv("DB_INCR_CONNS_ORA", ''))
            self.pool: str = os.getenv("DB_POOL_ORA", '')
            # security
            self.__secret_key: str = os.getenv("SECRET_KEY_UG", "")
            self.__algorithm: str = os.getenv("ALGORITHM", "HS256")
            self.__access_token_expire_minutes: int = to_int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", '60'))

        except Exception as e:
            raise Exception(f"Error al cargar las configuraciones de Oracle: {e}")

    def get_secret_key(self) -> str:
        return self.__secret_key

    def get_algorithm(self) -> str:
        return self.__algorithm

    def get_access_token_expire_minutes(self) -> int:
        return self.__access_token_expire_minutes
