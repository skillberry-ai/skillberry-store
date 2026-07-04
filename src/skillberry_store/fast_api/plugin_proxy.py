"""Reverse-proxy for /plugins/{slug}/{path:path} → 127.0.0.1:{port}/{path}."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

logger = logging.getLogger(__name__)


@dataclass
class ProxyTarget:
    slug: str
    port: int
    token: str  # SBS→plugin auth (per-plugin bearer)


class PluginRegistry:
    """Maps plugin slugs to their subprocess proxy targets."""

    def __init__(self) -> None:
        self._targets: Dict[str, ProxyTarget] = {}

    def register(self, target: ProxyTarget) -> None:
        self._targets[target.slug] = target

    def unregister(self, slug: str) -> None:
        self._targets.pop(slug, None)

    def get(self, slug: str) -> Optional[ProxyTarget]:
        return self._targets.get(slug)

    def all(self) -> Dict[str, ProxyTarget]:
        return dict(self._targets)


# Verbs that a plugin proxy forwards; catch-all path takes any of them.
_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]

# Path fragments reserved for plugin *lifecycle* operations owned by SBS itself.
# The SBS PluginManager exposes these under /plugins/{slug}/... — the reverse
# proxy must never intercept them, or install/start/stop would be forwarded
# into a subprocess (that may not even be running).
_LIFECYCLE_PATH_PREFIXES = ("install", "start", "stop", "restart", "status", "info")

# Fallback delegated to the in-process router chain — set by Stage 2 wiring so
# behaviour is identical when no plugin is registered as out-of-process.
_FALLBACK_HANDLER = None


def add_plugin_proxy(app: FastAPI, registry: PluginRegistry) -> None:
    """Mount the catch-all /plugins/{slug}/{path:path} route."""

    @app.api_route("/plugins/{slug}/{path:path}", methods=_METHODS, include_in_schema=False)
    async def _proxy(slug: str, path: str, request: Request):  # noqa: D401
        # SBS lifecycle endpoints (install/start/stop/...) are defined on the same
        # /plugins/{slug}/... URL space; FastAPI matches those *before* this
        # catch-all when both are declared. This route only fires for plugin API
        # paths not consumed by the lifecycle router.
        target = registry.get(slug)
        if target is None:
            raise HTTPException(status_code=404, detail=f"Plugin '{slug}' is not running")

        url = f"http://127.0.0.1:{target.port}/{path}"
        headers = dict(request.headers)
        # Rewrite hop-by-hop headers.
        for h in ("host", "content-length"):
            headers.pop(h, None)

        body = await request.body()
        params = dict(request.query_params)

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                r = await client.request(
                    request.method,
                    url,
                    params=params,
                    content=body if body else None,
                    headers=headers,
                )
            except httpx.HTTPError as e:
                logger.warning("Proxy to plugin %s failed: %s", slug, e)
                raise HTTPException(status_code=503, detail=f"Plugin '{slug}' unreachable")

        response_headers = {
            k: v
            for k, v in r.headers.items()
            if k.lower() not in ("content-length", "transfer-encoding", "content-encoding")
        }
        return Response(
            content=r.content,
            status_code=r.status_code,
            headers=response_headers,
            media_type=r.headers.get("content-type"),
        )
