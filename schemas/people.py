from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MarkingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    retorno_funcion: Optional[str] = Field(default=None, alias="RETORNO_FUNCION")
    pmensaje: Optional[str] = Field(default=None, alias="PMENSAJE")
    psqlcode: Optional[int] = Field(default=None, alias="PSQLCODE")
