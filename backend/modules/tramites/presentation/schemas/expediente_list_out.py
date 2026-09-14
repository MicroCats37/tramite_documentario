"""
Esquemas HTTP response extendidos para Expediente — Schema Ninja para API.

Incluye:
- ExpedienteItemOut: item resumido para listado paginado
- ExpedienteDetailOut: detalle completo con archivos, antecedentes, creado_por y solicitud
"""
import uuid
from datetime import datetime
from typing import Optional

from ninja import Field

from core.types import BaseSchema
from modules.tramites.domain.constants import TipoPersona
from modules.tramites.presentation.schemas.expediente_out import ExpedienteArchivoOut
from modules.tramites.presentation.schemas.tipo_documento_out import TipoDocumentoOut


class ExpedienteItemOut(BaseSchema):
    """
    Item resumido de expediente para listado paginado y respuesta de creación.

    Incluye archivos con URL para que el frontend pueda usar directamente
    sin transformación adicional. Contiene todos los campos de expediente
    necesarios para que el frontend pueda funcionar sin datos adicionales.
    """

    id: uuid.UUID = Field(..., description="ID único del expediente")
    id_publico: str = Field(..., description="Identificador público LIMA-{año}-{número:04d}")
    numero: int = Field(..., description="Número de Expediente")
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


class ExpedienteAntecedenteOut(BaseSchema):
    """
    Antecedente vinculado a un expediente.
    """

    id_publico: str = Field(..., description="Identificador público del antecedente")
    categoria: Optional[str] = Field(None, description="Categoría del vínculo")
    observaciones: Optional[str] = Field(None, description="Observaciones")


class ExpedienteDetailOut(BaseSchema):
    """
    Detalle completo de expediente para GET /expedientes/{id}.
    """

    id: uuid.UUID = Field(..., description="ID único del expediente")
    numero: int = Field(..., description="Número de Expediente")
    id_publico: str = Field(..., description="Identificador público LIMA-{año}-{número:04d}")
    tipo_persona: TipoPersona = Field(..., description="Tipo de persona")
    dni: Optional[str] = Field(None, description="DNI del ciudadano")
    ruc: Optional[str] = Field(None, description="RUC de la empresa")
    cip: Optional[str] = Field(None, description="CIP del profesional")
    razon_social: Optional[str] = Field(None, description="Razón social")
    nombres: Optional[str] = Field(None, description="Nombres del ciudadano")
    apellidos: Optional[str] = Field(None, description="Apellidos del ciudadano")
    correo: Optional[str] = Field(None, description="Correo electrónico")
    telefono: Optional[str] = Field(None, description="Teléfono de contacto")
    tipo_documento: TipoDocumentoOut = Field(..., description="Tipo de documento")
    numero_documento: Optional[str] = Field(None, description="Número de documento")
    numero_folios: int = Field(..., description="Número de folios")
    asunto: str = Field(..., description="Asunto del trámite")
    observaciones: Optional[str] = Field(None, description="Observaciones")
    fecha_registro: datetime = Field(..., description="Fecha de registro")
    archivos: list[ExpedienteArchivoOut] = Field(default_factory=list, description="Archivos adjuntos")
    antecedentes: list[ExpedienteAntecedenteOut] = Field(default_factory=list, description="Antecedentes")
    creado_por_nombres: Optional[str] = Field(None, description="Nombres de quien creó")
    solicitud_id: Optional[uuid.UUID] = Field(None, description="ID de la solicitud asociada")
    solicitud_estado: Optional[str] = Field(None, description="Estado de la solicitud")
    solicitud_prioridad: Optional[str] = Field(None, description="Prioridad de la solicitud")
