"""
ConsultaPresenter — Transforma resultados de consulta externa a esquemas HTTP.
"""

from modules.consultas.domain.results import ConsultaDocumentoResult
from modules.consultas.presentation.schemas.consulta_schemas import DocumentoConsultaOut


class ConsultaPresenter:
    """
    Transforma objetos de resultado de consulta externa a esquemas de respuesta HTTP.
    """

    @staticmethod
    def present_documento(result: ConsultaDocumentoResult) -> DocumentoConsultaOut:
        """
        Transforma el resultado unificado de consulta a esquema HTTP minimal.

        Args:
            result: ConsultaDocumentoResult del orchestrator

        Returns:
            DocumentoConsultaOut schema para respuesta HTTP
        """
        return DocumentoConsultaOut(
            tipo_documento=result.tipo_documento,
            numero_documento=result.numero_documento,
            razon_social=result.razon_social,
        )
