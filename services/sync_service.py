from aws.aws_settings import aws_settings
from typing import List, Dict
from oracleug.scripts.empleados import Empleados
import logging

logger = logging.getLogger(__name__)

s3_client = aws_settings.s3()


class SyncService:
    @classmethod
    def sincronizar_departamento(cls, coddepa: str) -> Dict:
        empleados = Empleados()
        datos = empleados.get_empleados_coddepa(coddepa)
        return datos
