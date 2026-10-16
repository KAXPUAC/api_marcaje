from pydantic import BaseModel
from typing import Optional


class RecognizeResponse(BaseModel):
    success: bool
    correlativo: Optional[str] = None
    datos_info: Optional[list[dict]] = None
    similarity: Optional[float] = None
    message: Optional[str] = None
    face_id: Optional[str] = None
    confidence: Optional[float] = None
