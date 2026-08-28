# Choices (TextChoices), constants, and enumeration types for the tramites module.

from django.db import models


class TipoPersona(models.TextChoices):
    """Tipo de persona que presenta el trámite."""

    NATURAL = "NATURAL", "Natural"
    JURIDICA = "JURIDICA", "Jurídica"
    COLEGIADO = "COLEGIADO", "Colegiado"


class TipoDocumento(models.TextChoices):
    """Tipo de documento presentado junto al trámite."""

    OFICIO = "OFICIO", "Oficio"
    CARTA = "CARTA", "Carta"
    SOLICITUD = "SOLICITUD", "Solicitud"
    MEMORANDO = "MEMORANDO", "Memorando"
    INFORME = "INFORME", "Informe"
    EXPEDIENTE = "EXPEDIENTE", "Expediente"
    RECIBO = "RECIBO", "Recibo"
    CERTIFICADO = "CERTIFICADO", "Certificado"
    OTRO = "OTRO", "Otro"


class EstadoSolicitud(models.TextChoices):
    """Estado global de la solicitud/trámite."""

    REGISTRADA = "REGISTRADA", "Registrada"
    EN_GESTION = "EN_GESTION", "En Gestión"
    FINALIZADA = "FINALIZADA", "Finalizada"
    ANULADA = "ANULADA", "Anulada"


class EstadoCambio(models.TextChoices):
    """Estados utilizados en el historial de cambios de estado de solicitud.

    Alineado con el catálogo objetivo de Solicitud.estado:
    REGISTRADA, EN_GESTION, FINALIZADA, ANULADA.
    """

    REGISTRADA = "REGISTRADA", "Registrada"
    EN_GESTION = "EN_GESTION", "En Gestión"
    FINALIZADA = "FINALIZADA", "Finalizada"
    ANULADA = "ANULADA", "Anulada"


class Prioridad(models.TextChoices):
    """Nivel de prioridad del trámite."""

    BAJA = "BAJA", "Baja"
    MEDIA = "MEDIA", "Media"
    ALTA = "ALTA", "Alta"
    URGENTE = "URGENTE", "Urgente"


class TipoArchivo(models.TextChoices):
    """Tipo de archivo adjunto al expediente."""

    PRINCIPAL = "PRINCIPAL", "Principal"
    ANEXO = "ANEXO", "Anexo"



