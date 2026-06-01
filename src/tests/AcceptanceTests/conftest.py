"""
Shared fixtures for the Acceptance-Test suite.

This suite maps one-to-one onto the Use-Case "Acceptance Tests" tables in the
Application Design Document (ADD), Chapter 1.2.  Each test exercises a complete
user-facing flow through the real FastAPI stack
(request -> controller -> service -> repo -> in-memory SQLite).

Rather than duplicate the wiring, we re-use the fully-wired application and the
high-level workflow helpers already defined for the system-test suite.  Importing
the fixtures into this conftest re-registers them for every test collected under
``src/tests/AcceptanceTests/``.
"""
# Fixtures (re-registered for this package by being present in the namespace)
from tests.SystemTests.conftest import (  # noqa: F401
    conn,
    app,
    client,
)

# Workflow + auth helpers used by the acceptance tests
from tests.SystemTests.conftest import (  # noqa: F401
    register_user,
    register_and_login,
    auth_header,
    make_creator,
    make_admin,
    get_user_xp,
    get_user_info,
    create_puzzle,
    add_blackbox_test_case,
    validate_solution,
    create_and_publish_puzzle,
    _and_solution,
)
