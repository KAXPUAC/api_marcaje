from aws.aws_settings import aws_settings
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self):
        self.s3_client = aws_settings.s3()

    def list_buckets(self):
        response = self.s3_client.list_buckets()
        print("Buckets disponibles:")
        for bucket in response['Buckets']:
            print(f"  - {bucket['Name']}")
