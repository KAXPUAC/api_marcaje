from aws.aws_settings import aws_settings
from typing import List, Dict
from oracleug.scripts.empleados import Empleados
import unicodedata
import logging
import base64

from services.rekognition_service import RekognitionService

logger = logging.getLogger(__name__)

s3_client = aws_settings.s3()


class SyncService:
    @staticmethod
    def limpiar_metadata(texto):
        if texto is None:
            return ""
        # Convertir a string si no lo es
        texto = str(texto)
        # Descomponer caracteres con acentos/tilde y filtrar los diacríticos
        texto_normalizado = unicodedata.normalize('NFD', texto)
        texto_ascii = texto_normalizado.encode('ascii', 'ignore').decode('utf-8')
        return texto_ascii

    @classmethod
    def sincronizar_departamento(cls, coddepa: str) -> Dict:
        empleados = Empleados()
        datos = empleados.get_empleados_coddepa(coddepa)
        logger.info(f"Código Departamento {coddepa}: {len(datos)} empleados con foto")
        result = {
            "total": len(datos),
            "exitosos": 0,
            "fallidos": 0,
            "errores": []
        }
        for emp in datos:
            try:
                if cls._procesar_empleado(emp):
                    result["exitosos"] += 1
                else:
                    result["fallidos"] += 1
            except Exception as e:
                error_msg = f"Error con {emp['correlativo']}: {str(e)}"
                print(error_msg)
                logger.error(error_msg)
                result["errores"].append(error_msg)
        return result

    @classmethod
    def _procesar_empleado(cls, emp) -> bool:
        subido = False
        correlativo = emp["Correlativo"]
        coddepa = emp["Coddepa"]
        foto_base64 = emp["Foto"]  # Asumimos que es base64
        foto_bytes = base64.b64decode(foto_base64)

        # Guardar en S3: Bucket/coddepa/correlativo.jpg
        s3_ruta = f"{coddepa}/"
        s3_nombre = f"{correlativo}.jpg"
        try:
            s3_client.put_object(
                Bucket=aws_settings.bucket_name(),
                Key=f"{s3_ruta}{s3_nombre}",
                Body=foto_bytes,
                ContentType='image/jpeg',
                Metadata={
                    'Correlativo': correlativo,
                    'Nombre': cls.limpiar_metadata(emp["Nombre"]),
                    'Coddepa': coddepa,
                    'Departamento': cls.limpiar_metadata(emp["Departamento"])
                }
            )
        except Exception as e:
            logger.error(f"Error subiendo empleado {correlativo} a S3: {str(e)}")
            subido = False
        logger.info(f"Empleado {correlativo} subido a S3 en {s3_ruta}{s3_nombre}")
        RekognitionService.indexar_rostro(departamento_id=coddepa, image_bytes=foto_bytes, correlativo=correlativo)
        return subido
