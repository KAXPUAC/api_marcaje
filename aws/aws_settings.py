import os
import re
from pathlib import Path

from dotenv import load_dotenv
import boto3

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=False)

_IDENTITY_POOL_ID_PATTERN = re.compile(
    r"^[a-z]{2}(?:-[a-z0-9]+)+-\d:[0-9a-fA-F]{8}"
    r"-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$"
)


class AWSSettings:
    def __init__(self):
        try:
            self.__region: str = os.getenv("AWS_REGION", "us-east-1")
            self.__access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
            self.__secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
            self.__bucket_name: str = os.getenv("AWS_S3_BUCKET_NAME", "")
            self.__face_liveness_confidence_threshold: float = float(
                os.getenv("FACE_LIVENESS_CONFIDENCE_THRESHOLD", "90")
            )
            self.__face_liveness_session_ttl_seconds: int = int(
                os.getenv("FACE_LIVENESS_SESSION_TTL_SECONDS", "180")
            )
            self.__identity_pool_id: str = os.getenv("COGNITO_IDENTITY_POOL_ID", "").strip()
            if not self.__identity_pool_id:
                raise ValueError(
                    "La variable COGNITO_IDENTITY_POOL_ID es obligatoria para Face Liveness"
                )
            if not _IDENTITY_POOL_ID_PATTERN.fullmatch(self.__identity_pool_id):
                raise ValueError(
                    "COGNITO_IDENTITY_POOL_ID debe tener el formato region:uuid "
                    "(por ejemplo, us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
                )
        except Exception as e:
            raise Exception(f"Error al cargar las configuraciones de AWS: {e}")

    def rekognition(self):
        return boto3.client(
            'rekognition',
            region_name=self.__region,
            aws_access_key_id=self.__access_key_id,
            aws_secret_access_key=self.__secret_access_key)

    def s3(self):
        return boto3.client(
            's3',
            region_name=self.__region,
            aws_access_key_id=self.__access_key_id,
            aws_secret_access_key=self.__secret_access_key)

    def bucket_name(self):
        return self.__bucket_name

    def region(self) -> str:
        return self.__region

    def face_liveness_confidence_threshold(self) -> float:
        return self.__face_liveness_confidence_threshold

    def face_liveness_session_ttl_seconds(self) -> int:
        return self.__face_liveness_session_ttl_seconds

    def identity_pool_id(self) -> str:
        return self.__identity_pool_id


aws_settings = AWSSettings()
