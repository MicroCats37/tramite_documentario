"""
Shared fixtures index for tramites tests.

Fixtures organized into the fixtures/ subpackage.
This file re-exports them directly so pytest discovers them.

Factories (make_payload_*) are NOT re-exported — import directly:
    from modules.tramites.tests.factories import make_expediente_payload
"""
from modules.tramites.tests.fixtures.expediente_fixtures import (
    api_client,
    usuario_creador,
    auth_client,
    pdf_file,
    pdf_file_anexo,
    multiple_pdf_files,
    ExpedienteController,
    ExpedienteOrchestrator,
    ExpedienteCreacionFlujo,
)
