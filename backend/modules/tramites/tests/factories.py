"""
Factories — helper functions to build valid API payloads for Expediente.

These are NOT fixtures (no db dependency), just pure functions that return dicts.
Use them inside tests or fixtures to avoid hardcoded payload literals.

Payload structures match the ExpedienteCreateIn schema with the dual-payload
FormData pattern: JSON in `data` field + files with "token___nombre.ext" naming.
"""

import json
import uuid
from typing import Optional


def make_expediente_payload(
    *,
    tipo_persona: str = "NATURAL",
    dni: Optional[str] = "12345678",
    ruc: Optional[str] = None,
    cip: Optional[str] = None,
    razon_social: Optional[str] = None,
    nombres: str = "Juan",
    apellidos: str = "Perez",
    correo: str = "juan.perez@example.com",
    telefono: str = "999888777",
    tipo_documento: str = "SOLICITUD",
    numero_documento: str = "DOC-2026-001",
    numero_folios: int = 5,
    asunto: str = "Solicitud de trámite de prueba",
    observaciones: Optional[str] = None,
    archivos: Optional[dict] = None,
) -> dict:
    """
    Build a complete ExpedienteCreateIn payload dict for the crear_expediente endpoint.

    This payload should be JSON-serialized and sent as the `data` FormData field.

    The archivos dict follows ArchivosAgrupadosIn structure:
        {"principal": [...], "anexo": [...]}

    Each archivo entry within the lists uses file tokens (not real files) since
    file hydration is done via the files parameter in FormData.

    Args:
        tipo_persona: NATURAL, JURIDICA, or COLEGIADO
        dni: 8-digit DNI (required for NATURAL)
        ruc: 11-digit RUC (required for JURIDICA)
        cip: CIP del profesional COI (for COLEGIADO)
        razon_social: Required for JURIDICA
        nombres: Required for NATURAL
        apellidos: Required for NATURAL
        correo: Email de contacto
        telefono: Teléfono de contacto
        tipo_documento: OFICIO, CARTA, SOLICITUD, MEMORANDO, INFORME, EXPEDIENTE, RECIBO, CERTIFICADO, OTRO
        numero_documento: Número del documento presentado
        numero_folios: Cantidad de folios
        asunto: Descripción del trámite
        observaciones: Observaciones adicionales (optional)
        archivos: Dict with PRINCIPAL and ANEXO lists containing archivo dicts

    Returns:
        dict matching ExpedienteCreateIn schema
    """
    if archivos is None:
        # Default: one principal document with a token reference
        archivos = {
            "principal": [
                {
                    "tipo_archivo": "PRINCIPAL",
                    "nombre_original": "documento_principal.pdf",
                    "descripcion": "Documento principal del trámite",
                    "archivo": "token_principal_pdf",
                }
            ],
            "anexo": [],
        }

    return {
        "tipo_persona": tipo_persona,
        "dni": dni,
        "ruc": ruc,
        "cip": cip,
        "razon_social": razon_social,
        "nombres": nombres,
        "apellidos": apellidos,
        "correo": correo,
        "telefono": telefono,
        "tipo_documento": tipo_documento,
        "numero_documento": numero_documento,
        "numero_folios": numero_folios,
        "asunto": asunto,
        "observaciones": observaciones,
        "archivos": archivos,
    }


def make_expediente_payload_json(
    **kwargs,
) -> str:
    """
    Build and serialize an Expediente payload to a JSON string.

    This is the format expected by the FormData `data` field.

    Args:
        **kwargs: Passed to make_expediente_payload()

    Returns:
        JSON string suitable for FormData `data` field
    """
    payload = make_expediente_payload(**kwargs)
    return json.dumps(payload)


def make_payload_expediente_natural(
    *,
    dni: str = "12345678",
    nombres: str = "Juan",
    apellidos: str = "Perez",
    correo: str = "juan.perez@example.com",
    telefono: str = "999888777",
    tipo_documento: str = "SOLICITUD",
    numero_documento: str = "DOC-2026-001",
    numero_folios: int = 5,
    asunto: str = "Solicitud de trámite de prueba",
    observaciones: Optional[str] = None,
    archivos: Optional[dict] = None,
) -> dict:
    """
    Build an Expediente payload for a NATURAL person.

    Convenience wrapper around make_expediente_payload with sensible defaults for
    persona natural.
    """
    return make_expediente_payload(
        tipo_persona="NATURAL",
        dni=dni,
        ruc=None,
        cip=None,
        razon_social=None,
        nombres=nombres,
        apellidos=apellidos,
        correo=correo,
        telefono=telefono,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        numero_folios=numero_folios,
        asunto=asunto,
        observaciones=observaciones,
        archivos=archivos,
    )


def make_payload_expediente_juridica(
    *,
    ruc: str = "20456789012",
    razon_social: str = "Empresa Test SAC",
    correo: str = "empresa@test.com",
    telefono: str = "012345678",
    tipo_documento: str = "OFICIO",
    numero_documento: str = "OFICIO-2026-001",
    numero_folios: int = 10,
    asunto: str = "Oficio de empresa",
    observaciones: Optional[str] = None,
    archivos: Optional[dict] = None,
) -> dict:
    """
    Build an Expediente payload for a JURIDICA (company) person.

    Convenience wrapper around make_expediente_payload with sensible defaults for
    persona jurídica.
    """
    return make_expediente_payload(
        tipo_persona="JURIDICA",
        dni=None,
        ruc=ruc,
        cip=None,
        razon_social=razon_social,
        nombres=None,
        apellidos=None,
        correo=correo,
        telefono=telefono,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        numero_folios=numero_folios,
        asunto=asunto,
        observaciones=observaciones,
        archivos=archivos,
    )
