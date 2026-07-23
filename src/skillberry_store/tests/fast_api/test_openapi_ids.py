"""Contract tests for OpenAPI ``operationId`` generation.

Route function names flow into the generated client SDK as method names via
``custom_generate_unique_id`` (see :mod:`skillberry_store.fast_api.openapi_ids`).
That makes ``operationId`` uniqueness part of the public API contract:

- if two routes ever collide, the generated SDK silently drops one — callers
  see a missing method with no server-side error;
- if a route function is renamed, existing SDK users break.

The tests here lock both invariants.
"""

import pytest

from fastapi.testclient import TestClient

from skillberry_store.fast_api.server import SBS
from skillberry_store.tests.utils import clean_test_tmp_dir


@pytest.fixture
def sbs_app():
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry

    clean_test_tmp_dir()
    object_handler.clear_object_handlers()
    registry.clear_services()
    app = SBS()
    yield app
    object_handler.clear_object_handlers()
    registry.clear_services()


def _collect_operation_ids(schema: dict) -> list[str]:
    operation_ids: list[str] = []
    for path_item in schema.get("paths", {}).values():
        for method_spec in path_item.values():
            if isinstance(method_spec, dict) and "operationId" in method_spec:
                operation_ids.append(method_spec["operationId"])
    return operation_ids


def test_openapi_operation_ids_are_unique(sbs_app):
    """Every OpenAPI operation must have a globally-unique ``operationId``.

    Collisions would silently drop routes from the generated SDK.
    """
    schema = sbs_app.openapi()
    ids = _collect_operation_ids(schema)
    assert ids, "no operationIds found in the OpenAPI schema"
    duplicates = {op for op in ids if ids.count(op) > 1}
    assert not duplicates, f"duplicate operationIds: {sorted(duplicates)}"


def test_openapi_operation_ids_are_valid_python_identifiers(sbs_app):
    """SDK method names are derived from ``operationId`` — they must be valid Python identifiers.

    Path-parameter segments (e.g. ``{plugin_name}``) leaking into the ID would
    break code generation.
    """
    schema = sbs_app.openapi()
    ids = _collect_operation_ids(schema)
    bad = [op for op in ids if not op.isidentifier()]
    assert not bad, f"non-identifier operationIds: {bad}"


def test_core_routes_use_bare_function_names(sbs_app):
    """Sanity-check the naming policy end-to-end for a few core routes.

    If this fails, the SDK method names have drifted from the server function
    names — every SDK user has to update their call-sites.
    """
    schema = sbs_app.openapi()
    ids = set(_collect_operation_ids(schema))
    for expected in (
        "create_tool",
        "list_tools",
        "get_tool",
        "delete_tool",
        "execute_tool",
        "tool_facets",
        "create_skill",
        "list_snippets",
        "create_vmcp_server",
        "create_vnfs_server",
    ):
        assert expected in ids, f"expected operationId {expected!r} missing"


def test_client_smoke(sbs_app):
    """A live TestClient hit sanity-checks that FastAPI is actually serving routes."""
    client = TestClient(sbs_app)
    resp = client.get("/health")
    assert resp.status_code == 200
