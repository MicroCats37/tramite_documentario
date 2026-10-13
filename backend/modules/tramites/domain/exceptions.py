# Domain-specific exceptions for the tramites module.
from core.exceptions import BusinessError, NotFoundError


class SaaaConnectionError(BusinessError):
    """Error al conectar con el servicio SAAA."""

    def __init__(self, message="No se pudo conectar con el servicio SAAA"):
        super().__init__(message)


class SaaaNotFoundError(NotFoundError):
    """Archivo no encontrado en SAAA."""

    def __init__(self, archivo_id: str):
        super().__init__(f"Archivo {archivo_id} no encontrado en SAAA")
        self.archivo_id = archivo_id


class SaaaUploadError(BusinessError):
    """Error al subir archivo a SAAA."""

    def __init__(self, message="Error al subir archivo a SAAA"):
        super().__init__(message)
