"""
PerfilIngenieroFactory — factory function for creating test PerfilIngeniero instances.

Minimal implementation consistent with the PerfilIngeniero model in domain/models/perfil_ingeniero.py.
"""
import factory
from factory.django import DjangoModelFactory

from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero


class PerfilIngenieroFactory(DjangoModelFactory):
    """Factory for creating PerfilIngeniero test instances."""

    class Meta:
        model = PerfilIngeniero

    nombres = factory.Faker("first_name")
    apellido_paterno = factory.Faker("last_name")
    apellido_materno = factory.Faker("last_name")
    cip = factory.Sequence(lambda n: f"{n:06d}")
    dni = factory.Sequence(lambda n: f"{n:08d}")
    correo_personal = factory.LazyAttribute(lambda obj: f"ingeniero{obj.dni}@example.com")
