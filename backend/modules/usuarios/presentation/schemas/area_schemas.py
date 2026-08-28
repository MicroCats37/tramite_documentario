"""
Esquemas HTTP response para Area — Schema Ninja para API.
"""
import uuid

from ninja import Field

from core.types import BaseSchema


class AreaOut(BaseSchema):
    """
    Respuesta HTTP para un área activa.
    """

    id: uuid.UUID = Field(..., description="ID único del área")
    nombre: str = Field(..., description="Nombre del área")
    descripcion: str | None = Field(None, description="Descripción del área")
    activo: bool = Field(..., description="¿Está activa?")
