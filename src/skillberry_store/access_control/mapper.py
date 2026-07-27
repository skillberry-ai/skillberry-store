"""Route → (resource, verb) mapping. See §6 of the design doc."""

from __future__ import annotations

from typing import Optional, Tuple

from fastapi import Request
from fastapi.routing import APIRoute
from starlette.routing import Match


class UnmappedRouteError(Exception):
    """Raised when no FastAPI route matches the inbound request."""


_TAG_TO_RESOURCE = {
    "skills": "skills",
    "tools": "tools",
    "snippets": "snippets",
    "vmcp_servers": "vmcp_servers",
    "vnfs_servers": "vnfs_servers",
    "admin": "admin",
    "plugins": "plugins",
}


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
    extra = route.openapi_extra or {}
    if "x-rbac-resource" in extra:
        return str(extra["x-rbac-resource"])
    for tag in route.tags or []:
        if tag in _TAG_TO_RESOURCE:
            return _TAG_TO_RESOURCE[tag]
    return "plugins"


def verb_for(request: Request, route: APIRoute) -> str:
    extra = route.openapi_extra or {}
    if "x-rbac-verb" in extra:
        return str(extra["x-rbac-verb"])
    method = request.method.upper()
    path = request.url.path
    tags = set(route.tags or [])

    if "admin" in tags:
        admin_super_paths = ("/admin/backup", "/admin/restore", "/admin/purge-all")
        if any(path.rstrip("/").startswith(p) for p in admin_super_paths):
            return "admin"

    if method == "GET":
        if "/search/" in path or path.startswith("/search"):
            return "search"
        if "export-" in path:
            return "get"
        if _has_path_param(route):
            return "get"
        return "list"

    if method == "POST":
        if path.endswith("/execute") or path.endswith("/start") or path.endswith("/stop"):
            return "execute"
        return "create"

    if method in ("PUT", "PATCH"):
        return "update"

    if method == "DELETE":
        return "delete"

    return "get"


def _has_path_param(route: APIRoute) -> bool:
    return "{" in route.path


def map_request(request: Request) -> Tuple[str, str, APIRoute]:
    """Resolve the matched route and return ``(resource, verb, route)``."""
    route = resolve_route(request)
    resource = resource_for(route)
    verb = verb_for(request, route)
    return resource, verb, route


def try_map_request(request: Request) -> Optional[Tuple[str, str, APIRoute]]:
    try:
        return map_request(request)
    except UnmappedRouteError:
        return None
