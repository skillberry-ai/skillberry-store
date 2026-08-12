"""Startup helpers for the @requires marker system.

Two functions, run in order from ``SBS.__init__`` after every route
(including plugin sub-routers) has been registered:

1. ``stamp_rbac_markers(app)`` — walks ``app.routes`` and copies each
   handler's ``__rbac_requires__`` attribute (set by the @requires
   decorator) onto that route's ``openapi_extra`` under the
   ``x-rbac-resource`` / ``x-rbac-verb`` keys. This is what the mapper
   reads at request time, and what the generated OpenAPI schema
   publishes to downstream consumers (Swagger UI, generated SDKs).

2. ``audit_rbac_coverage(app, cfg)`` — verifies every non-allowlisted
   ``APIRoute`` on the app carries the ``x-rbac-*`` markers. Any missing
   marker raises ``AccessControlConfigError`` and prevents startup —
   the fail-safe defaults property in §8 of the design doc.

Both run in all modes (``disabled`` and ``standalone``). Coverage is a
code-correctness property; skipping the audit in ``disabled`` mode
would defeat its purpose (an unmarked endpoint that ships to
production would only surface the first time an operator flips to
``standalone``).
"""

from __future__ import annotations

import logging
from typing import Iterable, List

from fastapi import FastAPI
from fastapi.routing import APIRoute

from skillberry_store.access_control.config import (
    AccessControlConfig,
    AccessControlConfigError,
)
from skillberry_store.access_control.decorator import get_marker

logger = logging.getLogger(__name__)


def stamp_rbac_markers(app: FastAPI) -> int:
    """Copy @requires markers from handlers onto their route's openapi_extra.

    Returns the number of routes that received a marker (for logging).
    Safe to call more than once — repeat calls are idempotent.
    """
    stamped = 0
    for route in _api_routes(app):
        marker = get_marker(route.endpoint)
        if marker is None:
            continue
        resource, verb = marker
        extra = dict(route.openapi_extra or {})
        # Only write if either key is missing or the existing value differs
        # from the marker. A pre-existing x-rbac-* set directly on
        # openapi_extra (legacy overrides) is preserved.
        changed = False
        if extra.get("x-rbac-resource") != resource:
            extra["x-rbac-resource"] = resource
            changed = True
        if extra.get("x-rbac-verb") != verb:
            extra["x-rbac-verb"] = verb
            changed = True
        if changed:
            route.openapi_extra = extra
            stamped += 1
    return stamped


def audit_rbac_coverage(app: FastAPI, cfg: AccessControlConfig) -> None:
    """Fail startup if any non-allowlisted route lacks RBAC markers.

    Raises ``AccessControlConfigError`` with a listing of every
    offender. Intended to be called after ``stamp_rbac_markers`` and
    after every ``register_*_api`` and plugin ``mount_routers`` call.
    """
    unmarked: List[str] = []
    for route in _api_routes(app):
        methods = route.methods or {"GET"}
        # If every method on this route is allow-listed, we can skip it.
        # If any method requires auth, the route needs a marker.
        needs_marker = False
        for method in methods:
            if not cfg.is_unauthenticated(method, route.path):
                needs_marker = True
                break
        if not needs_marker:
            continue
        extra = route.openapi_extra or {}
        missing = [
            key
            for key in ("x-rbac-resource", "x-rbac-verb")
            if not isinstance(extra.get(key), str) or not extra.get(key)
        ]
        if missing:
            unmarked.append(
                f"{'|'.join(sorted(methods))} {route.path} "
                f"[missing: {', '.join(missing)}]"
            )
    if unmarked:
        raise AccessControlConfigError(
            f"RBAC coverage audit failed: {len(unmarked)} endpoint(s) "
            "missing @requires marker(s). Apply @requires(resource, verb) "
            "above @app.<method> on each, or add the path to "
            "unauthenticated_paths if it should bypass ACL entirely.\n  "
            + "\n  ".join(unmarked)
        )


def _api_routes(app: FastAPI) -> Iterable[APIRoute]:
    for route in app.routes:
        if isinstance(route, APIRoute):
            yield route
