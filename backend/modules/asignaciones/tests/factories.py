# Factories — helper functions to build valid payloads for asignaciones tests.
#
# These are NOT fixtures (no db dependency), just pure functions that return dicts.
# Use them inside tests to avoid hardcoded payload literals.
#
# Follows TEST_ARCHITECTURE_CONTRACT: factories.py are pure Python functions
# returning dicts, NOT factory_boy factories.
