"""Compute the per-tenant MCP tool surface at startup.

Option 2 from docs/design/access-control.md §16.6: mount N FastApiMCP
instances, one per user, each exposing only the operations that user is
authorized to invoke under RBAC. Tool-execution is still gated by the
middleware on every call — this module answers the narrower question of
"which operations should this user's MCP surface *list*."
"""

from __future__ import annotations

import logging
from typing import Iterable, List

from fastapi import FastAPI
from fastapi.routing import APIRoute

from skillberry_store.access_control.config import AccessControlConfig, User
from skillberry_store.access_control.mapper import (
    resource_for,
    verb_for_method_path,
)
from skillberry_store.access_control.pdp import Subject, authorize

logger = logging.getLogger(__name__)


def _mcp_marked_routes(app: FastAPI) -> Iterable[APIRoute]:
    """Yield every APIRoute the store exposes on the Control MCP."""
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        extra = route.openapi_extra or {}
        if not extra.get("x-mcp-tool"):
            continue
        if not route.name:
            continue
        yield route


def _route_operation_id(route: APIRoute) -> str:
    """The ``operationId`` FastApiMCP consumes for a given route.

    With ``custom_generate_unique_id`` in effect on the app the
    operationId equals the route function name — which is
    ``route.name``. Falls back to ``operation_id`` when explicitly set.
    """
    return getattr(route, "operation_id", None) or route.name


def operations_for_subject(app: FastAPI, subject: Subject, cfg: AccessControlConfig) -> List[str]:
    """Return the sorted list of MCP operationIds allowed for ``subject``.

    An operation is included when the PDP grants at least one of the
    HTTP methods declared on its route. This matches how tool invocation
    is later gated: the client picks a single method per call, and the
    middleware authorizes that specific ``(resource, verb)`` pair.
    """
    allowed: List[str] = []
    for route in _mcp_marked_routes(app):
        resource = resource_for(route)
        methods = route.methods or {"GET"}
        for method in methods:
            verb = verb_for_method_path(method, route.path, route)
            if authorize(subject, resource, verb, cfg).allowed:
                allowed.append(_route_operation_id(route))
                break
    return sorted(allowed)


def operations_for_user(app: FastAPI, user: User, cfg: AccessControlConfig) -> List[str]:
    """Convenience: build a Subject from a config User and delegate."""
    subject = Subject(tenant_id=user.tenant_id, groups=list(user.groups or []))
    return operations_for_subject(app, subject, cfg)
