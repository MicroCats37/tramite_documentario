"""
ExpedienteCoreService — operaciones ORM síncronas para Expediente.

NO usa transaction.atomic() internamente — el flujo (flujo) provee la
transacción atómica cuando necesita crear el expediente junto con sus archivos.
"""
from datetime import datetime

from django.db.models import Max
from django.db import IntegrityError

from injector import inject

from modules.tramites.domain.models import Expediente
from modules.tramites.presentation.schemas.expediente_in import ExpedienteCreateIn


class ExpedienteCoreService:
    """
    Operaciones síncronas para Expediente.

    Toda operación es sync y no abre transaction.atomic() internamente.
    El flujo que la调用 provee la atomicidad si es necesaria.
    """

    def _obtener_siguiente_numero(self, año: int) -> int:
        """
        Obtiene el siguiente número de expediente para el año dado.

        Usa select_for_update() para bloquear las filas del año durante
        el cálculo y evitar duplicados bajo concurrencia.

        Sync — para uso dentro de transaction.atomic.

        Returns:
            Siguiente número disponible para el año.

        Raises:
            IntegrityError: Si hay冲突 de uniqueness después del INSERT.
        """
        # Bloquear las filas del año para evitar race conditions en MAX+1
        qs = Expediente.objects.filter(
            fecha_registro__year=año
        ).select_for_update()

        maximo = qs.aggregate(Max("numero"))["numero__max"]
        return (maximo or 0) + 1

    def _crear_expediente(
        self,
        data: ExpedienteCreateIn,
        creado_por_id: int,
    ) -> Expediente:
        """
        Crea un nuevo Expediente en la base de datos.

        Usa select_for_update en _obtener_siguiente_numero para proteger contra
        concurrencia. Reintenta una vez si hay UniqueViolation inesperado.

        Sync — para uso dentro de transaction.atomic.

        Args:
            data: Schema ExpedienteCreateIn con los datos del expediente.
            creado_por_id: ID del usuario que crea el expediente.

        Returns:
            Instancia de Expediente creada.
        """
        año_actual = datetime.now().year
        numero = self._obtener_siguiente_numero(año_actual)

        try:
            expediente = Expediente.objects.create(
                numero=numero,
                tipo_persona=data.tipo_persona,
                dni=data.dni,
                ruc=data.ruc,
                cip=data.cip,
                razon_social=data.razon_social,
                nombres=data.nombres,
                apellidos=data.apellidos,
                correo=data.correo,
                telefono=data.telefono,
                tipo_documento=data.tipo_documento,
                numero_documento=data.numero_documento,
                numero_folios=data.numero_folios,
                asunto=data.asunto,
                observaciones=data.observaciones,
                fecha_registro=datetime.now(),
                creado_por_id=creado_por_id,
            )
        except IntegrityError:
            # Reintento: otra transacción insertó entre el SELECT y el INSERT.
            # Recalcular y reintentar una sola vez.
            numero = self._obtener_siguiente_numero(año_actual)
            expediente = Expediente.objects.create(
                numero=numero,
                tipo_persona=data.tipo_persona,
                dni=data.dni,
                ruc=data.ruc,
                cip=data.cip,
                razon_social=data.razon_social,
                nombres=data.nombres,
                apellidos=data.apellidos,
                correo=data.correo,
                telefono=data.telefono,
                tipo_documento=data.tipo_documento,
                numero_documento=data.numero_documento,
                numero_folios=data.numero_folios,
                asunto=data.asunto,
                observaciones=data.observaciones,
                fecha_registro=datetime.now(),
                creado_por_id=creado_por_id,
            )
        return expediente

    def _obtener_expediente_por_id(self, expediente_id: int) -> Expediente | None:
        """
        Obtiene un Expediente por su ID.

        Sync — para uso dentro de transaction.atomic.
        """
        try:
            return Expediente.objects.get(id=expediente_id)
        except Expediente.DoesNotExist:
            return None
