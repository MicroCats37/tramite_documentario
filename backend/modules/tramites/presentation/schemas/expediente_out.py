"""
Esquemas HTTP response para Expediente — Schema Ninja para API.
"""
import uuid
from datetime import datetime
from typing import Optional

from ninja import Field

from core.types import BaseSchema
from modules.tramites.domain.constants import TipoPersona, TipoArchivo
from modules.tramites.presentation.schemas.tipo_documento_out import TipoDocumentoOut


class ExpedienteArchivoOut(BaseSchema):
    """
    Respuesta HTTP para un archivo adjunto de expediente.
    """

    id: uuid.UUID = Field(..., description="ID único del archivo")
    tipo_archivo: TipoArchivo = Field(..., description="Tipo de archivo (PRINCIPAL o ANEXO)")
    nombre_original: str = Field(..., description="Nombre original del archivo")
    url: str = Field(..., description="URL to access the file")


class ExpedienteOut(BaseSchema):
    """
    Respuesta HTTP para un expediente registrado.

    Incluye todos los campos de la entidad más el identificador público calculado.
    """

    id: uuid.UUID = Field(..., description="ID único del expediente")
    numero: int = Field(..., description="Número de Expediente (auto-incremental por año)")
    id_publico: str = Field(..., description="Identificador público con formato LIMA-{año}-{número:04d}")
    tipo_persona: TipoPersona = Field(..., description="Tipo de persona")
    dni: Optional[str] = Field(None, description="DNI del ciudadano")
    ruc: Optional[str] = Field(None, description="RUC de la empresa")
    cip: Optional[str] = Field(None, description="CIP del profesional")
    razon_social: Optional[str] = Field(None, description="Razón social")
    nombres: Optional[str] = Field(None, description="Nombres del ciudadano")
    apellidos: Optional[str] = Field(None, description="Apellidos del ciudadano")
    correo: Optional[str] = Field(None, description="Correo electrónico")
    telefono: Optional[str] = Field(None, description="Teléfono de contacto")
    tipo_documento: TipoDocumentoOut = Field(..., description="Tipo de documento presentado")
    numero_documento: Optional[str] = Field(None, description="Número de documento")
    numero_folios: int = Field(..., description="Número de folios")
    asunto: str = Field(..., description="Asunto del trámite")
    observaciones: Optional[str] = Field(None, description="Observaciones")
    fecha_registro: datetime = Field(..., description="Fecha de registro del trámite")
    archivos: list[ExpedienteArchivoOut] = Field(default_factory=list, description="Archivos adjuntos al expediente")
