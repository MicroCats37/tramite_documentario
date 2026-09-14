"""
Esquemas HTTP request para Expediente — Schema Ninja para API.

Maneja el patrón de dual payload (FormData + archivos) via parse_form_json.
"""
import uuid
from datetime import datetime
from typing import Optional

from ninja import Field
from django.core.files.uploadedfile import UploadedFile

from core.types import BaseSchema
from modules.tramites.domain.constants import TipoPersona, TipoArchivo


class ExpedienteArchivoCreateIn(BaseSchema):
    """
    Schema para un archivo individual asociado a un expediente.

    Se usa dentro del dict `archivos` en ExpedienteCreateIn.
    El campo `archivo` es un UploadedFile que se hydratar via token.
    """

    tipo_archivo: TipoArchivo = Field(..., description="Tipo de archivo: PRINCIPAL o ANEXO")
    nombre_original: str = Field(..., min_length=1, max_length=255, description="Nombre original del archivo")
    descripcion: Optional[str] = Field(None, description="Descripción opcional del archivo")
    archivo: UploadedFile = Field(..., description="Archivo upload (token en FormData)")


class ArchivosAgrupadosIn(BaseSchema):
    """
    Agrupación de archivos por tipo.

    El dict `archivos` en ExpedienteCreateIn tiene la estructura:
        {"principal": [ExpedienteArchivoCreateIn, ...], "anexo": [...]}
    """

    principal: list[ExpedienteArchivoCreateIn] = Field(
        default_factory=list,
        description="Archivos principales (documento principal)",
    )
    anexo: list[ExpedienteArchivoCreateIn] = Field(
        default_factory=list,
        description="Archivos anexos",
    )


class ExpedienteCreateIn(BaseSchema):
    """
    Payload para crear un nuevo expediente.

    Contiene los datos del ciudadano (razón social, nombres, apellidos, contacto)
    y los datos del documento (tipo, número, folios, asunto), más los archivos
    agrupados por tipo.

    Se recibe via FormData con el patrón dual payload:
        data: JSON string con este schema
        files: lista de UploadedFile con nombres "token___nombre_real.ext"
    """

    # ── Datos del ciudadano ────────────────────────────────────────────────────
    tipo_persona: TipoPersona = Field(..., description="Tipo de persona: NATURAL, JURIDICA o COLEGIADO")
    dni: Optional[str] = Field(
        None,
        min_length=8,
        max_length=8,
        description="DNI (8 dígitos) — requerido para persona natural",
    )
    ruc: Optional[str] = Field(
        None,
        min_length=11,
        max_length=11,
        description="RUC (11 dígitos) — requerido para persona jurídica",
    )
    cip: Optional[str] = Field(
        None,
        max_length=20,
        description="CIP del profesional COI",
    )
    razon_social: Optional[str] = Field(
        None,
        max_length=255,
        description="Razón social — requerido para persona jurídica",
    )
    nombres: Optional[str] = Field(
        None,
        max_length=150,
        description="Nombres — requerido para persona natural",
    )
    apellidos: Optional[str] = Field(
        None,
        max_length=150,
        description="Apellidos — requerido para persona natural",
    )
    correo: Optional[str] = Field(
        None,
        description="Correo electrónico de contacto",
    )
    telefono: Optional[str] = Field(
        None,
        max_length=20,
        description="Teléfono de contacto",
    )

    # ── Datos del documento ────────────────────────────────────────────────────
    tipo_documento_id: uuid.UUID = Field(..., description="UUID del tipo de documento presentado")
    numero_documento: Optional[str] = Field(
        None,
        max_length=50,
        description="Número de documento (oficio, carta, etc.)",
    )
    numero_folios: int = Field(
        default=0,
        ge=0,
        description="Número de folios del documento",
    )
    asunto: str = Field(..., min_length=1, description="Asunto o descripción del trámite")
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales")

    # ── Archivos ──────────────────────────────────────────────────────────────
    archivos: ArchivosAgrupadosIn = Field(
        ...,
        description="Archivos agrupados por tipo (PRINCIPAL / ANEXO)",
    )
