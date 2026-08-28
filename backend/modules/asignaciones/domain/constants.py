# Choices (TextChoices), constants, and enumeration types for the asignaciones module.

from django.db import models


class TipoParticipacion(models.TextChoices):
    """Tipo de participación del área en una solicitud."""

    PRINCIPAL = "PRINCIPAL", "Principal"
    ADJUNTA = "ADJUNTA", "Adjunta"


class EstadoPeriodo(models.TextChoices):
    """Estado operativo del período de asignación.

    Estados institucionales: PENDIENTE (sin iniciar), EN_GESTION (en curso),
    CERRADO (finalizado).
    """

    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_GESTION = "EN_GESTION", "En Gestión"
    CERRADO = "CERRADO", "Cerrado"


class TipoCierre(models.TextChoices):
    """Cómo terminó un período de asignación."""

    FINALIZADO = "FINALIZADO", "Finalizado"
    DERIVADO = "DERIVADO", "Derivado"
    RETIRADO = "RETIRADO", "Retirado"
    RECHAZADO = "RECHAZADO", "Rechazado"
    ANULADO = "ANULADO", "Anulado"
    ASIGNACION_ERRONEA = "ASIGNACION_ERRONEA", "Asignación Errónea"
    CAMBIO_PARTICIPACION = "CAMBIO_PARTICIPACION", "Cambio de Participación"


class EstadoPeriodoOperativo(models.TextChoices):
    """
    Estado operativo explícito del período de asignación.

    Este estado es independiente de participantes y respuestas.
    Se usa para métricas de tiempo por estado y para consultas rápidas.
    """

    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_GESTION = "EN_GESTION", "En Gestión"
    CERRADO = "CERRADO", "Cerrado"


class OrigenEstadoPeriodo(models.TextChoices):
    """
    Origen o motivo de una transición de estado operativo.

    Indica qué acción o evento disparó el cambio de estado.
    """

    CREACION = "CREACION", "Creación"
    AUTOASIGNACION = "AUTOASIGNACION", "Autoasignación"
    CIERRE = "CIERRE", "Cierre"
    CAMBIO_PARTICIPACION = "CAMBIO_PARTICIPACION", "Cambio de Participación"
    ASIGNACION_ERRONEA = "ASIGNACION_ERRONEA", "Asignación Errónea"


class TipoDerivacion(models.TextChoices):
    """Tipo de derivación entre períodos."""

    DERIVACION = "DERIVACION", "Derivación"
    DEVOLUCION = "DEVOLUCION", "Devolución"


class TipoRespuesta(models.TextChoices):
    """Tipo de respuesta formal del área."""

    INFORME = "INFORME", "Informe"
    OBSERVACION = "OBSERVACION", "Observación"
    CONFORMIDAD = "CONFORMIDAD", "Conformidad"
    DESCARGO = "DESCARGO", "Descargo"
    OTRO = "OTRO", "Otro"


class EstadoRespuesta(models.TextChoices):
    """Estado de la respuesta formal."""

    BORRADOR = "BORRADOR", "Borrador"
    EMITIDA = "EMITIDA", "Emitida"
    ANULADA = "ANULADA", "Anulada"
    RECTIFICADA = "RECTIFICADA", "Rectificada"


class TipoNotificacion(models.TextChoices):
    """Tipo de notificación al área."""

    NUEVA_ASIGNACION = "NUEVA_ASIGNACION", "Nueva Asignación"
    DEVOLUCION = "DEVOLUCION", "Devolución"
    COMENTARIO = "COMENTARIO", "Comentario"
    RESPUESTA = "RESPUESTA", "Respuesta"
    RECORDATORIO = "RECORDATORIO", "Recordatorio"
    URGENTE = "URGENTE", "Urgente"


class EstadoNotificacion(models.TextChoices):
    """Estado de la notificación."""

    PENDIENTE = "PENDIENTE", "Pendiente"
    ENVIADA = "ENVIADA", "Enviada"
    LEIDA = "LEIDA", "Leída"
    DESCARTADA = "DESCARTADA", "Descartada"
