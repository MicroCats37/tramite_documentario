"""
conftest.py for tramites e2e tests.

Re-exports fixtures from the parent fixtures/ package so pytest discovers them.
"""
# Import all fixture modules to register their @pytest.fixture definitions with pytest.
from modules.tramites.tests.fixtures import (
    expediente_fixtures,
)
