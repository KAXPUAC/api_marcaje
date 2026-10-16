from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from oracleug.scripts.empleados import Empleados
from services.rekognition_service import RekognitionService
from schemas.recognize import RecognizeResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recognize", tags=["Reconocimiento Facial"])


@router.post("", response_model=RecognizeResponse)
async def recognize_face(file: UploadFile = File(..., description="Imagen JPG/PNG"),
                         departamento: str = Form(..., description="Código de departamento (CODDEPA)")):
    """
    Reconoce un rostro comparando contra la collection Rekognition del departamento.
    Retorna el correlativo del empleado (ExternalImageId) si hay coincidencia ≥ 90%.
    """
    # Validar tipo de archivo
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (JPG/PNG)")

    # Leer bytes
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    try:
        # Buscar en Rekognition
        match = RekognitionService.buscar_rostro_en_departamento(
            departamento_id=departamento,
            image_bytes=image_bytes,
            umbral=90.0
        )

        if not match:
            return RecognizeResponse(
                success=False,
                message=f"No se encontró coincidencia en el departamento {departamento}"
            )
        empleado = Empleados()
        datos = empleado.get_empleado_info(correlativo=match["external_image_id"])
        return RecognizeResponse(
            success=True,
            correlativo=match["external_image_id"],
            datos_info=datos,
            similarity=match["similarity"],
            face_id=match["face_id"],
            confidence=match["confidence"]
        )

    except Exception as e:
        logger.error(f"Error en reconocimiento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en reconocimiento: {str(e)}")
