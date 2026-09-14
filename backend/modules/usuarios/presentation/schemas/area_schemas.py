"""
Esquemas HTTP response para Area — Schema Ninja para API.
"""
import uuid
from datetime import timedelta

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
    tiempo_respuesta: timedelta | None = Field(
        None,
        description="Duración máxima para atender un trámite (ej. 72 horas como timedelta)"
    )
    tiempo_respuesta_dias: int | None = Field(
        None,
        description="Parte entera de días de tiempo_respuesta (ej. 3 para 72h)"
    )
    tiempo_respuesta_horas: int | None = Field(
        None,
        description="Parte restante de horas dentro del día de tiempo_respuesta (ej. 0 para 72h)"
    )
