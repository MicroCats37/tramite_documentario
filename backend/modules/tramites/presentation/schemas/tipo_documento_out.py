"""
Esquemas HTTP response para TipoDocumento — Schema Ninja para API.
"""
import uuid

from ninja import Field

from core.types import BaseSchema


class TipoDocumentoOut(BaseSchema):
    """
    Respuesta HTTP para un tipo de documento del catálogo.
    """

    id: uuid.UUID = Field(..., description="ID único del tipo de documento")
    nombre: str = Field(..., description="Código único, ej. OFICIO, CARTA")
    descripcion: str = Field(..., description="Descripción legible, ej. Oficio, Carta")
