"""
Tests para SAAA Pointer helpers (saaa_pointer.py).

Valida:
- is_saaa_pointer(): detección correcta de punteros
- parse_saaa_pointer(): extracción de componentes
- build_saaa_pointer(): construcción de punteros
"""
import pytest

from modules.tramites.domain.services.saaa_pointer import (
    is_saaa_pointer,
    parse_saaa_pointer,
    build_saaa_pointer,
    SaaaPointer,
)


class TestIsSaaaPointer:
    """Tests para is_saaa_pointer()."""

    def test_returns_true_for_valid_saaa_pointer(self):
        assert is_saaa_pointer("saaa/semana-ingenieria-2026/abc12345/documento.pdf") is True

    def test_returns_true_for_pointer_with_slashes_in_name(self):
        assert is_saaa_pointer("saaa/app-id/uuid-archivo/archivo con espacios.pdf") is True

    def test_returns_false_for_local_file_path(self):
        assert is_saaa_pointer("tramites/expedientes/documento.pdf") is False

    def test_returns_false_for_empty_string(self):
        assert is_saaa_pointer("") is False

    def test_returns_false_for_none(self):
        assert is_saaa_pointer(None) is False

    def test_returns_false_for_local_path(self):
        # Un path local normal no es un puntero SAAA
        assert is_saaa_pointer("tramites/expedientes/documento.pdf") is False


class TestParseSaaaPointer:
    """Tests para parse_saaa_pointer()."""

    def test_parses_valid_pointer(self):
        pointer = parse_saaa_pointer("saaa/semana-ingenieria-2026/abc12345/documento.pdf")

        assert pointer is not None
        assert pointer.app_id == "semana-ingenieria-2026"
        assert pointer.archivo_id == "abc12345"
        assert pointer.nombre_original == "documento.pdf"

    def test_parses_pointer_with_simple_name(self):
        # Formato: saaa/{app_id}/{archivo_id}/{nombre_original}
        # donde archivo_id no contiene "/"
        pointer = parse_saaa_pointer("saaa/test-app/abc12345/documento.pdf")

        assert pointer is not None
        assert pointer.app_id == "test-app"
        assert pointer.archivo_id == "abc12345"
        assert pointer.nombre_original == "documento.pdf"

    def test_parses_pointer_with_path_in_name(self):
        # El nombre original puede contener "/" en versiones futuras
        pointer = parse_saaa_pointer("saaa/app/archivo-id/archivo.pdf")

        assert pointer is not None
        assert pointer.app_id == "app"
        assert pointer.archivo_id == "archivo-id"
        assert pointer.nombre_original == "archivo.pdf"

    def test_returns_none_for_local_path(self):
        result = parse_saaa_pointer("tramites/expedientes/documento.pdf")
        assert result is None

    def test_returns_none_for_empty(self):
        assert parse_saaa_pointer("") is None
        assert parse_saaa_pointer(None) is None

    def test_returns_none_for_incomplete_pointer(self):
        # Le faltan componentes: solo saaa/app
        assert parse_saaa_pointer("saaa/solo-app") is None

    def test_returns_none_for_saaa_prefix_without_parts(self):
        # "saaa/" solo sin componentes
        assert parse_saaa_pointer("saaa/") is None


class TestBuildSaaaPointer:
    """Tests para build_saaa_pointer()."""

    def test_builds_correct_pointer(self):
        result = build_saaa_pointer(
            app_id="semana-ingenieria-2026",
            archivo_id="abc12345",
            nombre_original="documento.pdf",
        )

        assert result == "saaa/semana-ingenieria-2026/abc12345/documento.pdf"

    def test_roundtrip_parse_build(self):
        original = "saaa/test-app/uuid-archivo/archivo con espacios.pdf"
        pointer = parse_saaa_pointer(original)

        assert pointer is not None
        rebuilt = build_saaa_pointer(
            app_id=pointer.app_id,
            archivo_id=pointer.archivo_id,
            nombre_original=pointer.nombre_original,
        )
        assert rebuilt == original
