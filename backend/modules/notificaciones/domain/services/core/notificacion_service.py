"""
NotificacionService — generación de notificaciones al área.

Servicio core síncrono para crear notificaciones y sus contextos asociados.

NO usa transaction.atomic() internamente — el flujo (flujo) provee la
transacción atómica cuando necesita crear notificaciones junto con otros objetos.

Patrón:
    El flujo provee @transaction.atomic() y llama a los métodos sync del servicio.
    El servicio no abre transacciones internamente.

Validación de eventos (Batch 3):
    Cada creación valida (ambito, evento) contra el registry de notificaciones.
    Los eventos no registrados son rechazados con NotificacionEventoNoRegistradoError.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from modules.notificaciones.domain.registry import (
    get_event_config,
    is_registered_event,
)

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    from modules.asignaciones.domain.models import (
        SolicitudAsignacion,
        SolicitudAsignacionPeriodo,
    )
    from modules.tramites.domain.models import Solicitud
    from modules.usuarios.domain.models import Area


class NotificacionService:
    """
    Operaciones de generación de notificaciones.

    Crea notificaciones para audiencias de tipo ÁREA, materializando:
    - Notificacion (el evento central)
    - NotificacionArea (contexto de audiencia institucional)
    - NotificacionSolicitud (contexto de solicitud, si se provee)
    - NotificacionAsignacion (contexto de asignación, si se provee)
    - NotificacionPeriodo (contexto de período, si se provee)
    - NotificacionUsuario (para cada usuario elegible del área)
    """

    def crear_notificacion_area(
        self,
        area: "Area",
        titulo: str,
        mensaje: str | None,
        ambito: str,
        evento: str,
        prioridad: str,
        generada_por_id: "UUID",
        ocurrido_en: datetime,
        solicitud: "Solicitud | None" = None,
        asignacion: "SolicitudAsignacion | None" = None,
        periodo: "SolicitudAsignacionPeriodo | None" = None,
        conversacion_id: "UUID | None" = None,
        mensaje_id: "UUID | None" = None,
    ) -> "Notificacion":
        """
        Crea una notificación de audiencia ÁREA con todos sus contextos.

        El llamador debe proveer @transaction.atomic() si se necesita atomicidad
        con otros objetos (asignaciones, solicitudes, etc.).

        Args:
            area: Instancia de Area destinataria.
            titulo: Título de la notificación.
            mensaje: Mensaje/detalle de la notificación.
            ambito: Ámbito/discriminador (ej. SOLICITUD, SISTEMA).
            evento: Código de evento dentro del ámbito.
            prioridad: Prioridad (NORMAL, ALTA, CRITICA).
            generada_por_id: ID del usuario que genera la notificación.
            ocurrido_en: Fecha y hora del evento que dispara la notificación.
            solicitud: Instancia de Solicitud opcional.
            asignacion: Instancia de SolicitudAsignacion opcional.
            periodo: Instancia de SolicitudAsignacionPeriodo opcional.
            conversacion_id: ID de Conversacion opcional (para menciones).
            mensaje_id: ID de Mensaje opcional (para menciones).

        Returns:
            Instancia de Notificacion creada con todos sus contextos.

        Raises:
            NotificacionEventoNoRegistradoError: si (ambito, evento) no está registrado.
        """
        # Importaciones locales para evitar circular imports
        from django.contrib.auth import get_user_model

        from modules.notificaciones.domain.models import (
            Notificacion,
            NotificacionArea,
            NotificacionAsignacion,
            NotificacionPeriodo,
            NotificacionSolicitud,
            NotificacionUsuario,
        )

        # 1. Validar que el evento esté registrado
        if not is_registered_event(ambito, evento):
            from modules.notificaciones.domain.exceptions import (
                NotificacionEventoNoRegistradoError,
            )
            raise NotificacionEventoNoRegistradoError(ambito, evento)

        # 2. Crear la Notificacion central
        # (área se representa via NotificacionArea, no FK directo)
        notificacion = Notificacion.objects.create(
            ambito=ambito,
            evento=evento,
            prioridad=prioridad,
            titulo=titulo,
            mensaje=mensaje,
            generada_por_id=generada_por_id,
            ocurrido_en=ocurrido_en,
        )

        # 3. Crear contexto NotificacionArea (evita duplicados por UniqueConstraint)
        NotificacionArea.objects.get_or_create(
            notificacion=notificacion,
            area=area,
        )

        # 4. Crear contexto NotificacionSolicitud si hay solicitud
        if solicitud is not None:
            from modules.conversaciones.domain.models import Conversacion, Mensaje
            conversacion = None
            if conversacion_id is not None:
                conversacion = Conversacion.objects.filter(id=conversacion_id).first()
            mensaje_obj = None
            if mensaje_id is not None:
                mensaje_obj = Mensaje.objects.filter(id=mensaje_id).first()
            NotificacionSolicitud.objects.get_or_create(
                notificacion=notificacion,
                defaults={
                    "solicitud": solicitud,
                    "asignacion": asignacion,
                    "periodo": periodo,
                    "conversacion": conversacion,
                    "mensaje": mensaje_obj,
                },
            )

        # 5. Crear contexto NotificacionAsignacion si hay asignacion
        # (legacy — se elimina en Batch 7, por ahora se mantiene para compat)
        if asignacion is not None:
            NotificacionAsignacion.objects.get_or_create(
                notificacion=notificacion,
                defaults={
                    "asignacion": asignacion,
                },
            )

        # 6. Crear contexto NotificacionPeriodo si hay periodo
        # (legacy — se elimina en Batch 7, por ahora se mantiene para compat)
        if periodo is not None:
            NotificacionPeriodo.objects.get_or_create(
                notificacion=notificacion,
                defaults={
                    "periodo": periodo,
                },
            )

        # 7. Materializar NotificacionUsuario para cada usuario elegible del área
        # Elegibilidad: usuarios con AsignacionUsuario activa para el área
        # (periodo_fin is null, is_active=True)
        User = get_user_model()
        usuarios_elegibles = User.objects.filter(
            asignaciones__area=area,
            asignaciones__periodo_fin__isnull=True,
            is_active=True,
        ).distinct()

        for usuario in usuarios_elegibles:
            NotificacionUsuario.objects.get_or_create(
                notificacion=notificacion,
                usuario=usuario,
            )

        return notificacion

    def crear_notificacion_usuario(
        self,
        usuario_id: "UUID",
        titulo: str,
        mensaje: str | None,
        ambito: str,
        evento: str,
        prioridad: str,
        generada_por_id: "UUID",
        ocurrido_en: datetime,
        solicitud: "Solicitud | None" = None,
        asignacion: "SolicitudAsignacion | None" = None,
        periodo: "SolicitudAsignacionPeriodo | None" = None,
        conversacion_id: "UUID | None" = None,
        mensaje_id: "UUID | None" = None,
    ) -> "Notificacion":
        """
        Crea una notificación dirigida a un usuario específico (audiencia USUARIO).

        Crea:
        - Notificacion (sin area FK)
        - NotificacionUsuario para el usuario destinatario

        NO crea NotificacionArea — es directa al usuario.

        Args:
            usuario_id: ID del usuario destinatario.
            titulo: Título de la notificación.
            mensaje: Mensaje/detalle de la notificación.
            ambito: Ámbito/discriminador.
            evento: Código de evento dentro del ámbito.
            prioridad: Prioridad (NORMAL, ALTA, CRITICA).
            generada_por_id: ID del usuario que genera la notificación.
            ocurrido_en: Fecha y hora del evento.
            solicitud: Instancia de Solicitud opcional.
            asignacion: Instancia de SolicitudAsignacion opcional.
            periodo: Instancia de SolicitudAsignacionPeriodo opcional.
            conversacion_id: ID de Conversacion opcional (para menciones en comentarios).
            mensaje_id: ID de Mensaje opcional (para menciones en comentarios).

        Returns:
            Instancia de Notificacion creada.

        Raises:
            NotificacionEventoNoRegistradoError: si (ambito, evento) no está registrado.
        """
        from django.contrib.auth import get_user_model

        from modules.notificaciones.domain.models import (
            Notificacion,
            NotificacionSolicitud,
            NotificacionUsuario,
        )

        # 1. Validar que el evento esté registrado
        if not is_registered_event(ambito, evento):
            from modules.notificaciones.domain.exceptions import (
                NotificacionEventoNoRegistradoError,
            )
            raise NotificacionEventoNoRegistradoError(ambito, evento)

        User = get_user_model()

        # 2. Crear la Notificacion central
        notificacion = Notificacion.objects.create(
            ambito=ambito,
            evento=evento,
            prioridad=prioridad,
            titulo=titulo,
            mensaje=mensaje,
            generada_por_id=generada_por_id,
            ocurrido_en=ocurrido_en,
        )

        # 3. Crear contexto NotificacionSolicitud si hay solicitud
        if solicitud is not None:
            from modules.conversaciones.domain.models import Conversacion, Mensaje
            conversacion = None
            if conversacion_id is not None:
                conversacion = Conversacion.objects.filter(id=conversacion_id).first()
            mensaje_obj = None
            if mensaje_id is not None:
                mensaje_obj = Mensaje.objects.filter(id=mensaje_id).first()
            NotificacionSolicitud.objects.get_or_create(
                notificacion=notificacion,
                defaults={
                    "solicitud": solicitud,
                    "asignacion": asignacion,
                    "periodo": periodo,
                    "conversacion": conversacion,
                    "mensaje": mensaje_obj,
                },
            )

        # 4. Crear NotificacionUsuario para el usuario destinatario
        NotificacionUsuario.objects.get_or_create(
            notificacion=notificacion,
            usuario_id=usuario_id,
        )

        return notificacion
