import os
from dotenv import load_dotenv
import boto3

load_dotenv(override=True)
from pathlib import Path

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class AWSSettings:
    def __init__(self):
        if not os.path.exists(env_path):
            raise Exception("No se encontró el archivo de entorno")
        try:
            self.region: str = os.getenv("AWS_REGION", "us-east-1")
            self.access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
            self.secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
            self.bucket_name: str = os.getenv("AWS_S3_BUCKET_NAME", "")
        except Exception as e:
            raise Exception(f"Error al cargar las configuraciones de AWS: {e}")

    def rekognition(self):
        return boto3.client(
            'rekognition',
            region_name=self.region,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key)

    def s3(self):
        return boto3.client(
            's3',
            region_name=self.region,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key)

aws_settings = AWSSettings()