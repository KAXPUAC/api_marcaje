from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.recognize import RecognizedUserAccount


class AttendanceResponse(BaseModel):
    marcado: bool
    abrir_puerta: bool
    codpers: Optional[str] = None
    tipo_usuario: Optional[str] = None
    departamento: Optional[str] = None
    laboratorio: Optional[str] = None
    retorno_funcion: Optional[str] = None
    mensaje: Optional[str] = None
    psqlcode: Optional[int] = None


class AdministrativeAttendanceResponse(BaseModel):
    """Resultado del marcaje administrativo y datos del usuario reconocido."""

    model_config = ConfigDict(populate_by_name=True)

    marcado: bool
    abrir_puerta: bool
    codpers: Optional[str] = None
    tipo_usuario: Optional[str] = None
    departamento: Optional[str] = None
    laboratorio: Optional[str] = None
    retorno_funcion: Optional[str] = None
    mensaje: Optional[str] = None
    psqlcode: Optional[int] = None

    usuario_codpers: Optional[str] = Field(default=None, alias="Codpers")
    usuario_nombre: Optional[str] = Field(default=None, alias="Usuario")
    gracad: Optional[str] = Field(default=None, alias="Gracad")
    nombres: Optional[str] = Field(default=None, alias="Nombres")
    apellidos: Optional[str] = Field(default=None, alias="Apellidos")
    email: Optional[str] = Field(default=None, alias="Email")
    gmail: Optional[str] = Field(default=None, alias="Gmail")
    gmail2: Optional[str] = Field(default=None, alias="Gmail2")
    usuario_correlativo: Optional[int] = Field(default=None, alias="Correlativo")
    usuario_coddepa: Optional[str] = Field(default=None, alias="Coddepa")
    usuario_departamento: Optional[str] = Field(default=None, alias="Departamento")
    usuario_tipo: Optional[str] = Field(default=None, alias="TipoUsuario")
    nombrepila: Optional[str] = Field(default=None, alias="Nombrepila")
    dpi: Optional[str] = Field(default=None, alias="Dpi")
    carnet: Optional[str] = Field(default=None, alias="Carnet")
    carnet1: Optional[str] = Field(default=None, alias="Carnet1")
    carnet2: Optional[str] = Field(default=None, alias="Carnet2")
    usuarios: list[RecognizedUserAccount] = Field(
        default_factory=list,
        alias="Usuarios",
    )


class AdministrativeLivenessRequest(BaseModel):
    session_id: str
    departamento: str


class TeacherLivenessRequest(BaseModel):
    session_id: str
    laboratorio: str


class PhotoBase64Response(BaseModel):
    correlativo: int
    foto_base64: str
