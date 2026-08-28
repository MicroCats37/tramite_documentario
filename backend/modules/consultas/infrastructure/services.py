"""
Infrastructure Services — Implementaciones de IConsultaClient para servicios externos.
"""

import hashlib
import os
import random
from datetime import date

import httpx

from modules.consultas.domain.ports import IConsultaClient
from modules.consultas.domain.results import ConsultaDocumentoResult
from modules.consultas.domain.exceptions import SunatNotFoundError, ReniecNotFoundError


class ConsultaSimulator(IConsultaClient):
    """
    Simulador del cliente consulta externa con datos mock para desarrollo.

    Proporciona datos determinísticos para probar el flujo completo
    sin depender de las APIs reales de RENIEC/SUNAT.

    - DNIs hardcoded tienen datos mock determinísticos existentes.
    - RUCs hardcoded tienen datos mock determinísticos existentes.
    - Cualquier otro documento válido genera datos mock determinísticos
      basados en el número (mismo número siempre devuelve los mismos datos).

    Comportamiento:
      - documento length 11 → trata como RUC (SUNAT)
      - documento length 8 → trata como DNI (RENIEC)
      - otro length → tipo_documento="DESCONOCIDO"
    """

    # ── SUNAT MOCK DATA ─────────────────────────────────────────────────────────

    _SUNAT_SIMULADOS = {
        "20492913151": {
            "ruc": "20492913151",
            "razon_social": "MUNICIPALIDAD PROVINCIAL DE LIMA",
        },
        "20131312957": {
            "ruc": "20131312957",
            "razon_social": "COLEGIO DE INGENIEROS DEL PERU",
        },
        "20600099773": {
            "ruc": "20600099773",
            "razon_social": "CONSORCIO CAM LIMA NORTE",
        },
    }

    _SUNAT_RAZONES_SOCIALES = [
        "EMPRESA CONSTRUCTORA",
        "SERVICIOS GENERALES",
        "INDUSTRIA MANUFACTURERA",
        "COMERCIO AL POR MAYOR",
        "COMERCIO AL POR MENOR",
        "TRANSPORTES Y LOGISTICA",
        "SERVICIOS PROFESIONALES",
        "AGRICULTURA Y GANADERIA",
        "PESCA Y ACUICULTURA",
        "MINERIA Y CANTERAS",
        "ENERGIA Y AGUA",
        "CONSTRUCCION",
        "HOSTELERIA Y RESTAURACION",
        "ACTIVIDADES INMOBILIARIAS",
        "EDUCACION",
        "SALUD",
        "ENTRETENIMIENTO",
        "ADMINISTRACION PUBLICA",
    ]

    # ── RENIEC MOCK DATA ─────────────────────────────────────────────────────────

    _RENIEC_SIMULADOS = {
        "45406196": {
            "dni": "45406196",
            "nombres": "DENNIS JOEL",
            "apellidos": "ZARATE TORRES",
            "nombre_completo": "ZARATE TORRES, DENNIS JOEL",
        },
        "12345678": {
            "dni": "12345678",
            "nombres": "CARLOS MANUEL",
            "apellidos": "PEREZ GOMEZ",
            "nombre_completo": "PEREZ GOMEZ, CARLOS MANUEL",
        },
        "87654321": {
            "dni": "87654321",
            "nombres": "MARIA ELENA",
            "apellidos": "LOPEZ SANCHEZ",
            "nombre_completo": "LOPEZ SANCHEZ, MARIA ELENA",
        },
    }

    _RENIEC_NOMBRES = [
        "JUAN", "CARLOS", "MIGUEL", "LUIS", "JOSE",
        "MARIA", "ELENA", "ANA", "PATRICIA", "LORENA",
        "FERNANDO", "RODRIGO", "VERONICA", "CARMEN", "FRANCISCO",
    ]

    _RENIEC_APELLIDOS = [
        "GARCIA", "PEREZ", "LOPEZ", "SANCHEZ", "RODRIGUEZ",
        "MARTINEZ", "TORRES", "RAMIREZ", "FLORES", "VARGAS",
        "HUAMAN", "QUISPE", "MENDOZA", "CASTILLO", "JIMENEZ",
    ]

    # ── Main dispatch method ─────────────────────────────────────────────────────

    async def consultar_documento(self, documento: str) -> ConsultaDocumentoResult:
        """
        Consulta documento unificada: auto-detecta DNI (8) vs RUC (11).
        """
        length = len(documento)

        if length == 11:
            return await self._consultar_ruc(documento)
        elif length == 8:
            return await self._consultar_dni(documento)
        else:
            return ConsultaDocumentoResult(
                tipo_documento="DESCONOCIDO",
                numero_documento=documento,
                razon_social="",
            )

    # ── Internal helpers ─────────────────────────────────────────────────────────

    async def _consultar_ruc(self, ruc: str) -> ConsultaDocumentoResult:
        """Consulta RUC (SUNAT)."""
        data = self._SUNAT_SIMULADOS.get(ruc)
        if data:
            return ConsultaDocumentoResult(
                tipo_documento="RUC",
                numero_documento=ruc,
                razon_social=data["razon_social"],
            )
        return self._generar_ruc_determinista(ruc)

    async def _consultar_dni(self, dni: str) -> ConsultaDocumentoResult:
        """Consulta DNI (RENIEC)."""
        data = self._RENIEC_SIMULADOS.get(dni)
        if data:
            return ConsultaDocumentoResult(
                tipo_documento="DNI",
                numero_documento=dni,
                razon_social=data["nombre_completo"],
            )
        return self._generar_dni_determinista(dni)

    def _generar_ruc_determinista(self, ruc: str) -> ConsultaDocumentoResult:
        """Genera datos mock determinísticos para RUCs no hardcoded."""
        seed = int(hashlib.md5(ruc.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        razon_social = f"{rng.choice(self._SUNAT_RAZONES_SOCIALES)} S.A.C."
        return ConsultaDocumentoResult(
            tipo_documento="RUC",
            numero_documento=ruc,
            razon_social=razon_social,
        )

    def _generar_dni_determinista(self, dni: str) -> ConsultaDocumentoResult:
        """Genera datos mock determinísticos para DNIs no hardcoded."""
        seed = int(hashlib.md5(dni.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        nombres = f"{rng.choice(self._RENIEC_NOMBRES)} {rng.choice(self._RENIEC_NOMBRES)}"
        apellido_paterno = rng.choice(self._RENIEC_APELLIDOS)
        apellido_materno = rng.choice(self._RENIEC_APELLIDOS)
        apellidos = f"{apellido_paterno} {apellido_materno}"
        nombre_completo = f"{apellidos}, {nombres}"
        return ConsultaDocumentoResult(
            tipo_documento="DNI",
            numero_documento=dni,
            razon_social=nombre_completo,
        )


class RealConsultaClient(IConsultaClient):
    """
    Cliente real que consulta el microservicio scraper de documentos.

    El scraper corre en worker/scraper/ y expone:
      GET {SCRAPER_URL}/consultar/{documento}

    Códigos HTTP del scraper:
      200 → dato encontrado
      404 → RUC/DNI no existe
      422 → documento inválido (longitud o formato)
      502 → formato del portal cambió (ScraperFormatError)
      503 → portal no disponible / sin conectividad
      504 → timeout esperando al portal
    """

    def __init__(self):
        self._base_url = os.environ.get("SCRAPER_URL", "http://scraper:8001")
        self._timeout = httpx.Timeout(
            connect=10.0,
            read=300.0,
            write=10.0,
            pool=5.0,
        )

    async def consultar_documento(self, documento: str) -> ConsultaDocumentoResult:
        """
        Consulta el microservicio scraper por DNI (8 dígitos) o RUC (11 dígitos).
        """
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
            ) as client:
                response = await client.get(f"/consultar/{documento}")
        except httpx.ConnectTimeout:
            from core.exceptions import HttpError
            raise HttpError(503, "No se pudo conectar al scraper de documentos")
        except httpx.ReadTimeout:
            from core.exceptions import HttpError
            raise HttpError(504, "Timeout esperando respuesta del scraper")
        except httpx.ConnectError:
            from core.exceptions import HttpError
            raise HttpError(503, "Scraper de documentos no disponible — verifique que el servicio esté corriendo")
        except httpx.HTTPError as e:
            from core.exceptions import HttpError
            raise HttpError(503, f"Error de red con el scraper: {e}")

        if response.status_code == 200:
            data = response.json()
            return ConsultaDocumentoResult(
                tipo_documento=data["tipo_documento"],
                numero_documento=data["numero_documento"],
                razon_social=data["razon_social"],
            )

        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        detail = body.get("detail", "Sin detalle")
        error_code = body.get("error", "UNKNOWN")

        if response.status_code == 404:
            if len(documento) == 8:
                raise ReniecNotFoundError(documento)
            raise SunatNotFoundError(documento)

        if response.status_code == 422:
            from core.exceptions import HttpError
            raise HttpError(422, f"Documento inválido: {detail}")

        if response.status_code == 504:
            from core.exceptions import HttpError
            raise HttpError(504, f"Portal de documentos no respondió a tiempo: {detail}")

        if response.status_code == 502:
            from core.exceptions import HttpError
            raise HttpError(502, f"Formato del portal cambió [{error_code}]: {detail}")

        if response.status_code == 503:
            from core.exceptions import HttpError
            raise HttpError(503, f"Portal de documentos no disponible [{error_code}]: {detail}")

        from core.exceptions import HttpError
        raise HttpError(response.status_code, f"Error inesperado del scraper: {detail}")
