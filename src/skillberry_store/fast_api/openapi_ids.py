"""OpenAPI ``operationId`` generation policy for the SBS FastAPI app.

Uses the route function name as the ``operationId``. That flows through to the
generated client SDK as short, stable method names (``client.tools_api.create_tool(...)``
instead of ``client.tools_api.create_tool_tools_post(...)``) — which is the whole
point.

Function names across all core-route modules must be globally unique. Plugin
routes are additionally namespaced by their plugin slug (extracted from the
mount path ``/plugins/<slug>/...``) because plugins are authored independently
and it is common for two plugins to name their handler e.g. ``scan_endpoint``.
A uniqueness test in the test suite locks this contract.
"""

from fastapi.routing import APIRoute

_PLUGIN_PATH_PREFIX = "/plugins/"


def custom_generate_unique_id(route: APIRoute) -> str:
    """Return a stable ``operationId`` derived from the route function name.

    For plugin routes (mounted under ``/plugins/<slug>/...``) the slug is
    prepended so cross-plugin function-name collisions don't produce duplicate
    operation IDs in the OpenAPI schema.
    """
    path = route.path or ""
    if path.startswith(_PLUGIN_PATH_PREFIX):
        # ``/plugins/<slug>/...`` — second segment is the plugin slug. Guard
        # against path-parameter segments like ``/plugins/{plugin_name}`` (the
        # meta endpoints in ``plugins_api`` that manage plugins themselves —
        # the segment is a variable, not a plugin slug).
        rest = path[len(_PLUGIN_PATH_PREFIX) :]
        slug = rest.split("/", 1)[0]
        if slug and not slug.startswith("{"):
            return f"{slug.replace('-', '_')}_{route.name}"
    return route.name
