"""Startup helpers for the @requires marker system.

Two functions, run in order from ``SBS.__init__`` after every route
(including plugin sub-routers) has been registered:

1. ``stamp_rbac_markers(app)`` — walks every route on the app and copies
   each handler's ``__rbac_requires__`` attribute (set by the @requires
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

Walking the route table (plugin-identity §6.1)
----------------------------------------------
FastAPI >= 0.137 no longer flattens ``include_router()`` routes into
``app.routes``: it nests them under a private ``_IncludedRouter`` whose
``original_router.routes`` holds the real ``APIRoute`` objects, each
still carrying its *unprefixed* path (``/check``, not
``/plugins/provenance/check``). ``walk_api_routes`` descends that
nesting and re-assembles the full path, which is what makes plugin
routes visible to both the stamper and the audit. The request path
already saw those routes — Starlette stamps the matched ``APIRoute``
onto ``request.scope["route"]`` — so before this walk existed a plugin
route reached the mapper with no marker and blew up as a 500.

Two properties of a plugin router that the audit treats separately from
a core route (plugin-identity §6.3):

* An unmarked plugin route is a **hard failure in ``standalone``** (a
  live authorization hole) but only a **warning in ``disabled``**, where
  no PEP exists and therefore no decision is being skipped. Third-party
  plugin routes live outside this repository, so failing them in
  ``disabled`` mode would refuse to boot a deployment that has no access
  control and no reason to expect an ACL-related failure. Core routes
  are in-tree and keep failing in every mode.
* A non-``APIRoute`` object inside a plugin router (a websocket, a
  Starlette ``Mount``) declares a surface the PEP cannot guard — a
  ``Mount`` in particular is outside the FastAPI dependency chain
  entirely and answers with no token at all. Those are reported on the
  same terms as an unmarked route rather than silently skipped.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Iterator, List

from fastapi import FastAPI
from fastapi.routing import APIRoute

from skillberry_store.access_control.config import (
    AccessControlConfig,
    AccessControlConfigError,
)
from skillberry_store.access_control.decorator import get_marker

logger = logging.getLogger(__name__)

PLUGIN_PATH_PREFIX = "/plugins/"


@dataclass(frozen=True)
class WalkedRoute:
    """One ``APIRoute`` found on the app, with its fully-prefixed path."""

    route: APIRoute
    path: str
    plugin: bool  # reached through an include_router() under /plugins/


@dataclass(frozen=True)
class ForeignPluginRoute:
    """A non-``APIRoute`` route object found inside a plugin router."""

    kind: str
    path: str


def walk_api_routes(
    app_or_router, prefix: str = "", plugin: bool = False
) -> Iterator[WalkedRoute]:
    """Yield every ``APIRoute`` reachable from ``app_or_router``.

    Descends ``_IncludedRouter`` nesting (FastAPI >= 0.137) and
    accumulates each include prefix so ``WalkedRoute.path`` is the path a
    client actually calls.
    """
    for route in getattr(app_or_router, "routes", []):
        if isinstance(route, APIRoute):
            yield WalkedRoute(route=route, path=prefix + route.path, plugin=plugin)
            continue
        included = getattr(route, "original_router", None)
        if included is None:
            continue
        # The ``getattr`` chain keeps this correct on FastAPI versions that
        # still flatten included routes (no include_context to read).
        sub_prefix = prefix + getattr(
            getattr(route, "include_context", None), "prefix", ""
        )
        yield from walk_api_routes(
            included,
            prefix=sub_prefix,
            plugin=plugin or sub_prefix.startswith(PLUGIN_PATH_PREFIX),
        )


def walk_foreign_plugin_routes(
    app_or_router, prefix: str = "", plugin: bool = False
) -> Iterator[ForeignPluginRoute]:
    """Yield route objects inside a plugin router that are not ``APIRoute``s.

    Those are surfaces the PEP cannot reach: a ``Mount`` bypasses the
    FastAPI dependency chain outright, and an ``APIWebSocketRoute`` fails
    the handshake rather than being authorized. Core-app mounts
    (``/control_sse*``) are deliberate, allow-listed exceptions and are
    not reported — only what a plugin router declares.
    """
    for route in getattr(app_or_router, "routes", []):
        if isinstance(route, APIRoute):
            continue
        included = getattr(route, "original_router", None)
        if included is not None:
            sub_prefix = prefix + getattr(
                getattr(route, "include_context", None), "prefix", ""
            )
            yield from walk_foreign_plugin_routes(
                included,
                prefix=sub_prefix,
                plugin=plugin or sub_prefix.startswith(PLUGIN_PATH_PREFIX),
            )
            continue
        if plugin:
            yield ForeignPluginRoute(
                kind=type(route).__name__,
                path=prefix + str(getattr(route, "path", "") or "?"),
            )


def _api_routes(app_or_router) -> Iterable[APIRoute]:
    """Every ``APIRoute`` on the app, plugin sub-routers included."""
    for walked in walk_api_routes(app_or_router):
        yield walked.route


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


def _missing_markers(route: APIRoute) -> List[str]:
    extra = route.openapi_extra or {}
    return [
        key
        for key in ("x-rbac-resource", "x-rbac-verb")
        if not isinstance(extra.get(key), str) or not extra.get(key)
    ]


def audit_rbac_coverage(app: FastAPI, cfg: AccessControlConfig) -> None:
    """Fail startup if any non-allowlisted route lacks RBAC markers.

    Raises ``AccessControlConfigError`` with a listing of every
    offender. Intended to be called after ``stamp_rbac_markers`` and
    after every ``register_*_api`` and plugin ``mount_routers`` call.

    Core offenders always fail. Plugin offenders fail in ``standalone``
    and warn in ``disabled`` — see the module docstring.
    """
    core_offenders: List[str] = []
    plugin_offenders: List[str] = []

    for walked in walk_api_routes(app):
        route = walked.route
        methods = route.methods or {"GET"}
        # If every method on this route is allow-listed, we can skip it.
        # If any method requires auth, the route needs a marker.
        needs_marker = any(
            not cfg.is_unauthenticated(method, walked.path) for method in methods
        )
        if not needs_marker:
            continue
        missing = _missing_markers(route)
        if not missing:
            continue
        entry = (
            f"{'|'.join(sorted(methods))} {walked.path} "
            f"[missing: {', '.join(missing)}]"
        )
        (plugin_offenders if walked.plugin else core_offenders).append(entry)

    for foreign in walk_foreign_plugin_routes(app):
        plugin_offenders.append(
            f"{foreign.kind} {foreign.path} [not an APIRoute: the PEP cannot "
            f"guard it — expose this surface as a plugin APIRoute instead]"
        )

    if plugin_offenders and cfg.mode == "disabled":
        logger.warning(
            "RBAC coverage audit: %d plugin endpoint(s) missing @requires "
            "marker(s). Tolerated in mode=disabled (no PEP is installed), but "
            "startup will FAIL once access control is enabled. Apply "
            "@requires(resource, verb) above each plugin route.\n  %s",
            len(plugin_offenders),
            "\n  ".join(plugin_offenders),
        )
        plugin_offenders = []

    offenders = core_offenders + plugin_offenders
    if offenders:
        raise AccessControlConfigError(
            f"RBAC coverage audit failed: {len(offenders)} endpoint(s) "
            "missing @requires marker(s). Apply @requires(resource, verb) "
            "above @app.<method> on each, or add the path to "
            "unauthenticated_paths if it should bypass ACL entirely.\n  "
            + "\n  ".join(offenders)
        )
