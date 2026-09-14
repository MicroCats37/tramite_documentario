"""
ExpedienteOrchestrator — fachada asíncrona ligera para controladores de Expediente.

Delegación de creación a ExpedienteCreacionFlujo, y consultas directas para lectura.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
import math
from uuid import UUID

from asgiref.sync import sync_to_async
from injector import inject

from modules.tramites.domain.models import Expediente
from modules.tramites.presentation.schemas.expediente_in import ExpedienteCreateIn
from modules.tramites.domain.services.flujos.expediente_flujo import (
    ExpedienteCreacionFlujo,
)


class ExpedienteOrchestrator:
    """
    Fachada asíncrona ligera — delega creación a ExpedienteCreacionFlujo,
    y consultas directas para lectura.
    """

    @inject
    def __init__(self, flujo: ExpedienteCreacionFlujo):
        self.flujo = flujo

    async def crear_expediente(
        self,
        payload: ExpedienteCreateIn,
        usuario_id: int,
    ) -> Expediente:
        """
        Crea un nuevo expediente con sus archivos adjuntos.

        Args:
            payload: Schema ExpedienteCreateIn con los datos del expediente.
            usuario_id: ID del usuario que realiza el registro.

        Returns:
            Instancia de Expediente creada.
        """
        return await self.flujo._proceso_crear_expediente(payload, usuario_id)

    async def listar_expedientes(
        self,
        page: int = 1,
        page_size: int = 10,
        busqueda: str | None = None,
        año: int | None = None,
    ) -> tuple:
        """
        Lista expedientes con filtros y paginación.

        Args:
            page: Número de página (1-indexed)
            page_size: Tamaño de página (max 100)
            busqueda: Texto a buscar en id_publico, numero_documento, dni, ruc, nombres, razon_social, asunto
            año: Filtrar por año de fecha_registro

        Returns:
            Tupla (items, total, page, page_size, total_pages)
        """
        def _query():
            from django.db.models import Q

            qs = (
                Expediente.objects
                .select_related("creado_por", "tipo_documento")
                .prefetch_related("archivos")
                .order_by("-fecha_registro", "-numero")
            )

            if año is not None:
                qs = qs.filter(fecha_registro__year=año)

            if busqueda:
                qs = qs.filter(
                    Q(numero_documento__icontains=busqueda)
                    | Q(dni__icontains=busqueda)
                    | Q(ruc__icontains=busqueda)
                    | Q(nombres__icontains=busqueda)
                    | Q(razon_social__icontains=busqueda)
                    | Q(asunto__icontains=busqueda)
                )

            total = qs.count()
            total_pages = math.ceil(total / page_size) if total > 0 else 1
            offset = (page - 1) * page_size
            items = list(qs[offset:offset + page_size])

            return items, total, page, page_size, total_pages

        return await sync_to_async(_query, thread_sensitive=True)()

    async def obtener_expediente(self, expediente_id: UUID) -> Expediente | None:
        """
        Obtiene un expediente por ID con archivos, antecedentes y datos relacionados.

        Args:
            expediente_id: UUID del expediente

        Returns:
            Expediente con relaciones cargadas o None si no existe
        """
        def _query():
            try:
                return (
                    Expediente.objects
                    .select_related("creado_por", "solicitud", "tipo_documento")
                    .prefetch_related("archivos", "antecedentes_vinculados__antecedente")
                    .get(id=expediente_id)
                )
            except Expediente.DoesNotExist:
                return None

        return await sync_to_async(_query, thread_sensitive=True)()
