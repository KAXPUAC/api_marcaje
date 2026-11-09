from aws.aws_settings import aws_settings
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

rekognition = aws_settings.rekognition()


class RekognitionService:
    @classmethod
    def crear_sesion_liveness(cls) -> str:
        """Crea una sesión para Amazon Rekognition Face Liveness."""
        response = rekognition.create_face_liveness_session()
        return response["SessionId"]

    @classmethod
    def obtener_resultado_liveness(cls, session_id: str) -> dict:
        """Obtiene el resultado server-side de una sesión de Face Liveness."""
        response = rekognition.get_face_liveness_session_results(SessionId=session_id)
        reference_image = response.get("ReferenceImage") or {}
        return {
            "status": response.get("Status"),
            "confidence": response.get("Confidence"),
            "reference_image": reference_image.get("Bytes"),
        }

    @staticmethod
    def obtener_nombre_coleccion(departamento_id: str) -> str:
        return f"depto_{departamento_id.lower().strip()}"

    @classmethod
    def asegurar_collection_existe(cls, collection_id: str):
        """Crea la collection si no existe."""
        try:
            rekognition.describe_collection(CollectionId=collection_id)
            logger.debug(f"Collection {collection_id} ya existe")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                rekognition.create_collection(CollectionId=collection_id)
                logger.info(f"Collection {collection_id} creada")
            else:
                raise

    @classmethod
    def buscar_rostro_en_departamento(cls, departamento_id: str, image_bytes: bytes, umbral: float = 90.0):
        """
        Busca un rostro en la collection del departamento.
        Retorna dict con: external_image_id (correlativo), similarity, face_id
        """
        collection_id = cls.obtener_nombre_coleccion(departamento_id)
        cls.asegurar_collection_existe(collection_id)

        response = rekognition.search_faces_by_image(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            FaceMatchThreshold=umbral,
            MaxFaces=1
        )

        matches = response.get('FaceMatches', [])
        if not matches:
            return None

        match = matches[0]
        face = match['Face']

        return {
            "external_image_id": face['ExternalImageId'],  # ← EL CORRELATIVO
            "face_id": face['FaceId'],
            "similarity": match['Similarity'],
            "confidence": face['Confidence']
        }

    @classmethod
    def buscar_rostro_en_todos_departamentos(cls, image_bytes: bytes, umbral: float = 90.0):
        """Busca un rostro en todas las collections de departamentos existentes."""
        paginator = rekognition.get_paginator('list_collections')

        for page in paginator.paginate():
            for collection_id in page.get('CollectionIds', []):
                if not collection_id.startswith('depto_'):
                    continue

                departamento_id = collection_id[len('depto_'):]
                match = cls.buscar_rostro_en_departamento(
                    departamento_id=departamento_id,
                    image_bytes=image_bytes,
                    umbral=umbral
                )

                if match:
                    match['departamento'] = departamento_id
                    return match

        return None

    @classmethod
    def indexar_rostro(cls, departamento_id: str, image_bytes: bytes, correlativo: str) -> str:
        """Indexa una cara individual. Retorna FaceId."""
        collection_id = cls.obtener_nombre_coleccion(departamento_id)
        cls.asegurar_collection_existe(collection_id)

        response = rekognition.index_faces(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            ExternalImageId=correlativo,
            DetectionAttributes=['DEFAULT'],
            QualityFilter='AUTO'
        )

        face_records = response.get('FaceRecords', [])
        if not face_records:
            raise ValueError(f"No se detectó rostro en foto de {correlativo}")

        face_id = face_records[0]['Face']['FaceId']
        return face_id
