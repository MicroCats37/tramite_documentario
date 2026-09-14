"""Domain exceptions for notificaciones module."""


class NotificacionEventoNoRegistradoError(Exception):
    """
    Raised when a notification event (ambito, evento) is not found in the registry.

    This is a domain exception that controllers should map to HTTP 400/422
    following the existing error handling patterns.
    """

    def __init__(self, ambito: str, evento: str):
        self.ambito = ambito
        self.evento = evento
        super().__init__(
            f"Evento no registrado: ambito={ambito!r}, evento={evento!r}. "
            f"Usa get_event_config() para consultar eventos válidos."
        )
