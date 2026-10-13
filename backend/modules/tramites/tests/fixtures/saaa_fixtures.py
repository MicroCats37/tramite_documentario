"""
SAAA fixtures — client injectable para tests de integración.

Provee:
- saaa_client: implementación fake en memoria (default)
- RealSaaaClient: cliente real (para tests de integración real)

Uso en tests:
    def test_something(saaa_client, ...):
        result = saaa_client.subir_archivo(...)

El fake permite tests sin conexión real a SAAA, siguiendo la regla
de no usar unittest.mock.patch del TEST_ARCHITECTURE_CONTRACT.
"""
import pytest

from modules.tramites.infrastructure.saaa_client import (
    FakeSaaaClient,
    RealSaaaClient,
)


@pytest.fixture
def saaa_client():
    """
    Cliente SAAA injectable para tests.

    Por defecto retorna FakeSaaaClient (en memoria).
    Para tests de integración real contra SAAA, sobreescribir con:
        RealSaaaClient()
    """
    return FakeSaaaClient()


@pytest.fixture
def real_saaa_client():
    """
    Cliente SAAA real (conecta con el servicio externo).

    Solo usar en tests de integración que requieren el servicio real.
    """
    return RealSaaaClient()
