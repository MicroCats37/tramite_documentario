"""
conftest.py — Fixtures globales para tests de CAM.

Inspirado en: centro-de-esparcimiento/backend/conftest.py
"""
import os

os.environ.setdefault("NINJA_SKIP_REGISTRY", "1")

# Force CIP simulator in tests to avoid real HTTP calls to external CIP API.
# This overrides development.py's CIP_USE_SIMULATOR = False so that
# test_ingeniero_habilitado_integration.py and other tests using the
# ICipClient dependency get CipClientSimulator instead of RealCipClient.
os.environ["CIP_USE_SIMULATOR"] = "True"

import pytest
from pathlib import Path


def _patch_ninja_extra_test_client():
    """Make ninja_extra's sync TestClient execute async endpoints in tests."""
    import inspect
    from urllib.parse import urlencode

    from asgiref.sync import async_to_sync
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.utils.datastructures import MultiValueDict
    import ninja_extra.testing as testing
    import ninja_extra.testing.client as testing_client
    from ninja.testing.client import NinjaResponse

    def _clone_file(file_obj):
        file_obj.seek(0)
        return SimpleUploadedFile(
            name=file_obj.name,
            content=file_obj.read(),
            content_type=getattr(file_obj, "content_type", None),
        )

    def _as_file_list(files):
        if isinstance(files, dict):
            files = list(files.values())
        elif not isinstance(files, list):
            files = [files]
        return [
            _clone_file(file_obj[1] if isinstance(file_obj, tuple) else file_obj)
            for file_obj in files
        ]

    class AsyncAwareTestClient(testing_client.NinjaExtraClientBase):
        def request(self, method, path, data=None, json=None, **request_params):
            if method.upper() == "GET" and isinstance(data, dict) and data:
                separator = "&" if "?" in path else "?"
                path = f"{path}{separator}{urlencode(data)}"
                data = None
            elif isinstance(data, dict) and "files" in data:
                data = data.copy()
                request_params["FILES"] = MultiValueDict({
                    "files": _as_file_list(data.pop("files")),
                })
            elif "files" in request_params:
                request_params["FILES"] = MultiValueDict({
                    "files": _as_file_list(request_params.pop("files")),
                })
            return super().request(method, path, data, json, **request_params)

        def _call(self, func, request, kwargs):
            response = func(request, **kwargs)
            if inspect.isawaitable(response):
                async def _await_response():
                    return await response

                response = async_to_sync(_await_response)()
            return NinjaResponse(response)

    testing.TestClient = AsyncAwareTestClient
    testing_client.TestClient = AsyncAwareTestClient


_patch_ninja_extra_test_client()


# ── Test database cleanup ───────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    """Remove stale test_db.sqlite3 before the test session to avoid stale row collisions."""
    test_db = Path(__file__).resolve().parent.parent / "test_db.sqlite3"
    if test_db.exists():
        os.remove(test_db)
    yield
    # No post-run cleanup — keep it for debugging if tests fail


# ── Django test client (sync) ───────────────────────────────────────

@pytest.fixture
def client(db):
    """Django test client (sync) — usa Django's test Client, no Ninja TestClient.

    Para tests de integración que usan Django test Client (no NinjaExtra).
    El db fixture asegura que la base SQLite en memoria esté lista.
    """
    from django.test import Client
    return Client()


# ── Ninja-style TestClient fixtures (opcional para tests más controlados) ──

def _get_ninja_api():
    """Obtiene la instancia de NinjaExtraAPI para usar en tests."""
    from config.api import api
    return api


def _get_override_dict():
    """Resolve dependency_overrides dict for NinjaExtraAPI."""
    ninja_api = _get_ninja_api()
    if hasattr(ninja_api, 'dependency_overrides'):
        return ninja_api.dependency_overrides
    app = getattr(ninja_api, 'app', None)
    if app is not None and hasattr(app, 'dependency_overrides'):
        return app.dependency_overrides
    return {}


@pytest.fixture
def test_sync_client(db):
    """Ninja TestClient sin autenticación.

    Útil para tests que quieren el cliente de Ninja (no Django test Client).
    """
    from ninja.testing import TestClient
    api = _get_ninja_api()
    return TestClient(api)


@pytest.fixture
def api():
    """NinjaExtraAPI instance from config/api.py."""
    return _get_ninja_api()


@pytest.fixture
def test_async_client(db):
    """Ninja TestAsyncClient sin autenticación.

    Para tests async del módulo finanzas.
    """
    from ninja.testing import TestAsyncClient
    api = _get_ninja_api()
    return TestAsyncClient(api)
