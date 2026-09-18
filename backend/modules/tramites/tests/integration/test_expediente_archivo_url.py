import uuid

from django.test import override_settings

from modules.tramites.domain.constants import TipoArchivo
from modules.tramites.domain.models import ExpedienteArchivo
from modules.tramites.presentation.presenters.expediente_presenter import (
    ExpedientePresenter,
)


@override_settings(MEDIA_URL="http://localhost:12001/media/")
def test_expediente_archivo_presenter_serializes_absolute_media_url():
    archivo = ExpedienteArchivo(
        id=uuid.uuid4(),
        tipo_archivo=TipoArchivo.PRINCIPAL,
        nombre_original="documento.png",
        archivo="tramites/expedientes/documento.png",
    )

    out = ExpedientePresenter._map_archivo(archivo)

    assert out.url == "http://localhost:12001/media/tramites/expedientes/documento.png"
