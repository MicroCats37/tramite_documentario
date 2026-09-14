"""
Domain exceptions for conversaciones module.
"""

from uuid import UUID


class ConversacionNotFoundError(Exception):
    """Raised when a Conversacion is not found."""

    def __init__(self, conversacion_id):
        self.conversacion_id = conversacion_id
        super().__init__(f"Conversacion '{conversacion_id}' not found")


class MensajeNotFoundError(Exception):
    """Raised when a Mensaje is not found."""

    def __init__(self, mensaje_id):
        self.mensaje_id = mensaje_id
        super().__init__(f"Mensaje '{mensaje_id}' not found")


class ConversacionCerradaError(Exception):
    """Raised when attempting to post to a closed Conversacion."""

    def __init__(self, conversacion_id):
        self.conversacion_id = conversacion_id
        super().__init__(f"Conversacion '{conversacion_id}' is closed and cannot accept new messages")


class UsuarioNotFoundError(Exception):
    """Raised when a Usuario is not found."""

    def __init__(self, usuario_id):
        self.usuario_id = usuario_id
        super().__init__(f"Usuario '{usuario_id}' not found")


class BridgeValidationError(Exception):
    """
    Raised when the SolicitudConversacion bridge validation fails.

    This occurs when a conversacion_id does not belong to the specified solicitud_id.
    Controllers should map this to HTTP 400 or 409 following existing patterns.
    """

    def __init__(self, solicitud_id: UUID, conversacion_id):
        self.solicitud_id = solicitud_id
        self.conversacion_id = conversacion_id
        super().__init__(
            f"La conversación '{conversacion_id}' no pertenece a la solicitud {solicitud_id}"
        )
