"""
conftest.py for tramites integration tests.

Loads fixtures from the fixtures/ subpackage so pytest can discover them.
This conftest.py is in tests/integration/ which is a proper conftest discovery path.

Usage:
    All fixtures from fixtures/* are automatically available.
    For factories, import directly:
        from modules.tramites.tests.factories import make_expediente_payload
"""
# Import all fixture modules to register their @pytest.fixture definitions with pytest.
# pytest discovers fixtures defined in conftest.py and its imported modules.
from modules.tramites.tests.fixtures import (
    expediente_fixtures,
)
