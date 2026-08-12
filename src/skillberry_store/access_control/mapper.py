"""Route → (resource, verb) mapping. See §6 of the design doc.

Every REST endpoint declares its ``(resource, verb)`` explicitly via
``@requires(...)`` (see ``decorator.py``). ``SBS.__init__`` stamps
that marker onto the matched ``APIRoute.openapi_extra`` at startup;
this module reads those keys back at request time. There is no
method/path→verb rule table and no tag→resource fallback — a route
that reaches the enforce dependency without markers is a bug, and
``audit_rbac_coverage`` refuses to boot when any non-allowlisted route
is unmarked.
"""

from __future__ import annotations

from typing import Optional, Tuple

from fastapi import Request
from fastapi.routing import APIRoute
from starlette.routing import Match


class UnmappedRouteError(Exception):
    """Raised when no FastAPI route matches the inbound request."""


class UnmarkedRouteError(Exception):
    """Raised when the matched route has no @requires marker.

    Should never fire in production — the startup audit prevents it.
    Kept as a defensive backstop for cases where a route is added after
    startup (e.g. a runtime plugin mount) without the audit re-running.
    """


def resolve_route(request: Request) -> APIRoute:
    """Walk the app's route table and return the first FULL match."""
    for route in request.app.routes:
        try:
            match, _ = route.matches(request.scope)
        except Exception:
            continue
        if match == Match.FULL:
            if isinstance(route, APIRoute):
                return route
    raise UnmappedRouteError(request.url.path)


def resource_for(route: APIRoute) -> str:
    """Return the RBAC resource declared on ``route`` via @requires.

    Raises ``UnmarkedRouteError`` if the marker is missing.
    """
    extra = route.openapi_extra or {}
    resource = extra.get("x-rbac-resource")
    if not isinstance(resource, str) or not resource:
        raise UnmarkedRouteError(
            f"{route.path}: missing x-rbac-resource "
            f"(apply @requires above @app.<method>)"
        )
    return resource


def verb_for_route(route: APIRoute) -> str:
    """Return the RBAC verb declared on ``route`` via @requires.

    Raises ``UnmarkedRouteError`` if the marker is missing.
    """
    extra = route.openapi_extra or {}
    verb = extra.get("x-rbac-verb")
    if not isinstance(verb, str) or not verb:
        raise UnmarkedRouteError(
            f"{route.path}: missing x-rbac-verb "
            f"(apply @requires above @app.<method>)"
        )
    return verb


def map_request(request: Request) -> Tuple[str, str, APIRoute]:
    """Resolve the matched route and return ``(resource, verb, route)``.

    Prefers ``request.scope["route"]`` when it is a live ``APIRoute`` —
    which is the case on the production request path, because the
    enforce dependency runs after Starlette routing has stamped the
    matched route onto the scope. Falls back to walking
    ``request.app.routes`` for callers that construct synthetic
    ``Request`` objects and never invoke routing (``test_mapper.py``).
    """
    route = request.scope.get("route")
    if not isinstance(route, APIRoute):
        route = resolve_route(request)
    return resource_for(route), verb_for_route(route), route


def try_map_request(request: Request) -> Optional[Tuple[str, str, APIRoute]]:
    """Return ``map_request`` result or ``None`` for unmapped routes."""
    try:
        return map_request(request)
    except UnmappedRouteError:
        return None
