"""
UsuarioFactory — factory function for creating test Usuario instances.

Minimal implementation consistent with the Usuario model in domain/models/usuario.py.
The model uses username (8-digit DNI string) as the USERNAME_FIELD.
"""
import factory


def UsuarioFactory(**kwargs):
    """
    Create a Usuario test instance.

    Usage:
        user = UsuarioFactory()  # creates active user with random DNI/username
        user = UsuarioFactory(username="12345678", password="mypassword")

    Required fields not provided default to generated values.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    defaults = {
        "username": kwargs.pop("username", None),
        "dni": kwargs.pop("dni", None),
        "email": kwargs.pop("email", None),
        "password": kwargs.pop("password", "testpass123"),
        "nombres": kwargs.pop("nombres", "Test"),
        "apellidos": kwargs.pop("apellidos", "User"),
        "is_staff": kwargs.pop("is_staff", False),
        "is_superuser": kwargs.pop("is_superuser", False),
        "is_active": kwargs.pop("is_active", True),
    }

    # Remove None values so they get auto-generated
    for key in list(defaults.keys()):
        if defaults[key] is None:
            del defaults[key]

    # Add any extra kwargs
    defaults.update(kwargs)

    # Use sequence to generate unique values if not provided
    username_seq = defaults.get("username")
    if not username_seq:
        # Generate a unique 8-digit username
        counter = getattr(UsuarioFactory, "_counter", 10000000)
        UsuarioFactory._counter = counter + 1
        defaults["username"] = f"{counter:08d}"
        defaults["dni"] = defaults.get("dni") or f"{counter:08d}"
        defaults["email"] = defaults.get("email") or f"{defaults['username']}@cip.gob.pe"

    user = User(**defaults)
    user.set_password(defaults["password"])
    user.save()
    return user
