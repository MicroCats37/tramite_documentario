# Plain constants for the notificaciones module.
# No Django TextChoices — plain Python strings using StrEnum-like classes.
# Full modular registry with category/navigation is Batch 3.

# ── Ambito ────────────────────────────────────────────────────────────────────


class AmbitoNotificacion:
    """Ámbito/discriminador de dominio de la notificación."""

    SOLICITUD = "SOLICITUD"
    SISTEMA = "SISTEMA"

    @classmethod
    def values(cls):
        return [cls.SOLICITUD, cls.SISTEMA]


# ── Evento dentro del ámbito ──────────────────────────────────────────────────


class EventoNotificacion:
    """Código de evento dentro del ámbito."""

    # Solicitud
    ASIGNACION_CREADA = "ASIGNACION_CREADA"
    DEVOLUCION_CREADA = "DEVOLUCION_CREADA"
    RESPUESTA_CREADA = "RESPUESTA_CREADA"
    COMENTARIO_MENCION = "COMENTARIO_MENCION"
    COMENTARIO_CREADO = "COMENTARIO_CREADO"
    RECORDATORIO = "RECORDATORIO"
    RESPUESTA_FINAL = "RESPUESTA_FINAL"

    @classmethod
    def values(cls):
        return [
            cls.ASIGNACION_CREADA,
            cls.DEVOLUCION_CREADA,
            cls.RESPUESTA_CREADA,
            cls.COMENTARIO_MENCION,
            cls.COMENTARIO_CREADO,
            cls.RECORDATORIO,
            cls.RESPUESTA_FINAL,
        ]


# ── Prioridad ────────────────────────────────────────────────────────────────


class PrioridadNotificacion:
    """Prioridad de la notificación."""

    NORMAL = "NORMAL"
    ALTA = "ALTA"
    CRITICA = "CRITICA"

    @classmethod
    def values(cls):
        return [cls.NORMAL, cls.ALTA, cls.CRITICA]

    DEFAULT = NORMAL


# ── Categoría ───────────────────────────────────────────────────────────────


class CategoriaNotificacion:
    """
    Categoría de la notificación — determina el canal de entrega
    y el comportamiento de presentación.

    - INSTITUCIONAL: notificaciones de proceso/trámite (asignaciones, devoluciones,
      respuestas formales). Audiencia primaria: área.
    - MENSAJERIA: notificaciones de comunicación (menciones en comentarios).
      Audiencia primaria: usuario individual.
    - SISTEMA: notificaciones de estado del sistema (recordatorios, alertas).
      Audiencia: puede ser área o usuario según el evento.
    """

    INSTITUCIONAL = "INSTITUCIONAL"
    MENSAJERIA = "MENSAJERIA"
    SISTEMA = "SISTEMA"

    @classmethod
    def values(cls):
        return [cls.INSTITUCIONAL, cls.MENSAJERIA, cls.SISTEMA]
