from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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


class AdministrativeLivenessRequest(BaseModel):
    session_id: str
    departamento: str


class TeacherLivenessRequest(BaseModel):
    session_id: str
    laboratorio: str
