from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RecognizeResponse(BaseModel):
    success: bool
    departamento: Optional[str] = None
    correlativo: Optional[str] = None
    datos_info: Optional[list[dict]] = None
    similarity: Optional[float] = None
    message: Optional[str] = None
    face_id: Optional[str] = None
    confidence: Optional[float] = None


class RecognizedUserResponse(BaseModel):
    """Datos completos del usuario asociado al rostro reconocido."""

    model_config = ConfigDict(populate_by_name=True)

    codpers: Optional[str] = Field(default=None, alias="Codpers")
    usuario: Optional[str] = Field(default=None, alias="Usuario")
    gracad: Optional[str] = Field(default=None, alias="Gracad")
    nombres: Optional[str] = Field(default=None, alias="Nombres")
    apellidos: Optional[str] = Field(default=None, alias="Apellidos")
    email: Optional[str] = Field(default=None, alias="Email")
    gmail: Optional[str] = Field(default=None, alias="Gmail")
    gmail2: Optional[str] = Field(default=None, alias="Gmail2")
    correlativo: Optional[int] = Field(default=None, alias="Correlativo")
    coddepa: Optional[str] = Field(default=None, alias="Coddepa")
    departamento: Optional[str] = Field(default=None, alias="Departamento")
    nombrepila: Optional[str] = Field(default=None, alias="Nombrepila")
    dpi: Optional[str] = Field(default=None, alias="Dpi")
    carnet: Optional[str] = Field(default=None, alias="Carnet")
    carnet1: Optional[str] = Field(default=None, alias="Carnet1")
    carnet2: Optional[str] = Field(default=None, alias="Carnet2")
