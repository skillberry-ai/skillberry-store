"""The @requires decorator — declarative RBAC intent per endpoint.

Each REST endpoint must declare the ``(resource, verb)`` needed to
invoke it. The declaration replaces (r13) the earlier rule-table
mapping where verbs were derived from HTTP method and URL path. That
inference was convenient but had a fail-open failure mode: an endpoint
whose URL shape didn't match a rule silently fell through to a
default. Explicit `@requires` markers are fail-safe by construction —
`SBS.__init__` runs an audit at startup that refuses to boot when a
non-allowlisted route is missing the marker.

Usage:

    @requires("skills", "create")
    @app.post(
        "/skills/",
        tags=[tags],
        openapi_extra={"x-cli-name": "add-skill", "x-mcp-tool": True},
    )
    async def create_skill(...):
        ...

Ordering: `@app.<method>` runs FIRST (registers the route on the app
and returns the wrapped function unchanged), then `@requires` runs on
that function and stamps the marker attribute. A startup pass in
``SBS.__init__`` copies the marker onto the matching APIRoute's
``openapi_extra`` — that's what the mapper reads at request time, and
what the generated OpenAPI schema publishes to downstream consumers.

Do NOT apply `@requires` to routes that live in the unauth allow-list
(``/auth/*``, ``/health*``, ``/admin/metrics``): those never reach the
PDP, and the audit skips them.
"""

from __future__ import annotations

from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)

_MARKER_ATTR = "__rbac_requires__"


def requires(resource: str, verb: str) -> Callable[[F], F]:
    """Declare that this endpoint requires ``(resource, verb)`` to invoke.

    The marker is attached to the handler function as
    ``fn.__rbac_requires__ = (resource, verb)`` and stamped onto the
    route's ``openapi_extra`` at startup by
    ``stamp_rbac_markers(app)``.
    """
    if not isinstance(resource, str) or not resource:
        raise ValueError("@requires: 'resource' must be a non-empty string")
    if not isinstance(verb, str) or not verb:
        raise ValueError("@requires: 'verb' must be a non-empty string")

    def deco(fn: F) -> F:
        setattr(fn, _MARKER_ATTR, (resource, verb))
        return fn

    return deco


def get_marker(fn: Callable) -> tuple[str, str] | None:
    """Return ``(resource, verb)`` stamped by ``@requires``, or None."""
    marker = getattr(fn, _MARKER_ATTR, None)
    if isinstance(marker, tuple) and len(marker) == 2:
        return marker
    return None
