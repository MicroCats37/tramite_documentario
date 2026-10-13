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


@override_settings(FILE_PROXY_URL="/api/archivo/public/")
def test_expediente_archivo_presenter_returns_proxy_url_for_saaa_pointer():
    """
    GIVEN: an ExpedienteArchivo whose archivo.name is a SAAA pointer
    WHEN:  _map_archivo is called
    THEN:  it returns /api/archivo/public/{archivo_id} as the URL (default relative)
    """
    archivo = ExpedienteArchivo(
        id=uuid.uuid4(),
        tipo_archivo=TipoArchivo.PRINCIPAL,
        nombre_original="documento.pdf",
        archivo="saaa/semana-ingenieria-2026/abc12345/documento.pdf",
    )

    out = ExpedientePresenter._map_archivo(archivo)

    assert out.url == "/api/archivo/public/abc12345"
    assert out.nombre_original == "documento.pdf"
    assert out.tipo_archivo == TipoArchivo.PRINCIPAL


@override_settings(FILE_PROXY_URL="http://localhost:12001/api/archivo/public/")
def test_expediente_archivo_presenter_returns_absolute_proxy_url_when_file_proxy_url_set():
    """
    GIVEN: FILE_PROXY_URL is set to an absolute URL
    WHEN:  _map_archivo is called with a SAAA pointer
    THEN:  it returns the absolute proxy URL respecting FILE_PROXY_URL
    """
    archivo = ExpedienteArchivo(
        id=uuid.uuid4(),
        tipo_archivo=TipoArchivo.PRINCIPAL,
        nombre_original="documento.pdf",
        archivo="saaa/semana-ingenieria-2026/abc12345/documento.pdf",
    )

    out = ExpedientePresenter._map_archivo(archivo)

    assert out.url == "http://localhost:12001/api/archivo/public/abc12345"
    assert out.nombre_original == "documento.pdf"
    assert out.tipo_archivo == TipoArchivo.PRINCIPAL


@override_settings(FILE_PROXY_URL="/api/archivo/public/")
def test_expediente_archivo_presenter_handles_pointer_with_uuid_id():
    """
    GIVEN: an ExpedienteArchivo with a SAAA pointer containing a UUID-like id
    WHEN:  _map_archivo is called
    THEN:  the proxy URL contains the full archivo_id
    """
    archivo = ExpedienteArchivo(
        id=uuid.uuid4(),
        tipo_archivo=TipoArchivo.ANEXO,
        nombre_original="acta.pdf",
        archivo="saaa/semana-ingenieria-2026/4ab48d91-6ff8-48eb-9c6b-3cc9619c31b9/acta.pdf",
    )

    out = ExpedientePresenter._map_archivo(archivo)

    assert out.url == "/api/archivo/public/4ab48d91-6ff8-48eb-9c6b-3cc9619c31b9"
    assert out.tipo_archivo == TipoArchivo.ANEXO
