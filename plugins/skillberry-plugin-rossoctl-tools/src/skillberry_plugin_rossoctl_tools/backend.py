"""Client for rossoctl's backend REST API (``/api/v1``).

The plugin's only outbound destination is ``ROSSOCTL_BACKEND_URL``. It never
connects to tool pods: rossoctl's backend does that (``/connect``,
``/invoke``). Tool and namespace names are validated as DNS-1123 labels and
used only in URL paths on that host.

Authentication: a client-credentials token from ``ROSSOCTL_TOKEN_ENDPOINT``
when ``ROSSOCTL_CLIENT_ID``/``ROSSOCTL_CLIENT_SECRET`` are set (cached until
shortly before expiry, refreshed once on 401); no ``Authorization`` header when
they are unset (rossoctl with ``ENABLE_AUTH=false``); or the caller's own
bearer when one is passed (delegated mode).
"""

import asyncio
import logging
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

DNS1123_LABEL = re.compile(r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$")


class RossoctlError(Exception):
    """Base class for backend call failures."""

    status_code = 502


class RossoctlUnavailable(RossoctlError):
    """The backend (or the tool behind it) cannot be reached."""

    status_code = 502


class RossoctlNotFound(RossoctlError):
    status_code = 404


class RossoctlForbidden(RossoctlError):
    status_code = 403


def validate_label(value: Any, what: str) -> str:
    if not isinstance(value, str) or not DNS1123_LABEL.match(value):
        raise ValueError(f"{what} must be a DNS-1123 label (got {value!r})")
    return value


def _detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except ValueError:
        pass
    return (resp.text or resp.reason_phrase or "")[:500]


class RossoctlBackend:
    """Calls rossoctl's ``/api/v1/tools`` endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token_endpoint: Optional[str] = None,
        allowed_namespaces: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        env = os.environ
        self.base_url = (
            base_url if base_url is not None else env.get("ROSSOCTL_BACKEND_URL", "")
        ).rstrip("/")
        self.client_id = (
            client_id if client_id is not None else env.get("ROSSOCTL_CLIENT_ID", "")
        )
        self.client_secret = (
            client_secret
            if client_secret is not None
            else env.get("ROSSOCTL_CLIENT_SECRET", "")
        )
        self.token_endpoint = (
            token_endpoint
            if token_endpoint is not None
            else env.get("ROSSOCTL_TOKEN_ENDPOINT", "")
        )
        if allowed_namespaces is None:
            raw = env.get("ROSSOCTL_ALLOWED_NAMESPACES", "")
            allowed_namespaces = [n.strip() for n in raw.split(",") if n.strip()]
        self.allowed_namespaces = allowed_namespaces
        self.timeout = float(
            timeout if timeout is not None else env.get("ROSSOCTL_TIMEOUT", "30")
        )
        self._transport = transport
        self._clock = clock
        self._token: Optional[str] = None
        self._token_expiry = 0.0
        self._token_lock = asyncio.Lock()

    # ---- configuration ---------------------------------------------------- #

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    @property
    def uses_client_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret and self.token_endpoint)

    def check_namespace(self, namespace: str) -> str:
        validate_label(namespace, "namespace")
        if self.allowed_namespaces and namespace not in self.allowed_namespaces:
            raise ValueError(
                f"namespace '{namespace}' is not allowed (ROSSOCTL_ALLOWED_NAMESPACES="
                f"{','.join(self.allowed_namespaces)})"
            )
        return namespace

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout, transport=self._transport)

    # ---- token ------------------------------------------------------------ #

    async def _service_token(self, force: bool = False) -> Optional[str]:
        if not self.uses_client_credentials:
            return None
        async with self._token_lock:
            if not force and self._token and self._clock() < self._token_expiry:
                return self._token
            try:
                async with self._client() as client:
                    resp = await client.post(
                        self.token_endpoint,
                        data={
                            "grant_type": "client_credentials",
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                        },
                    )
            except httpx.HTTPError as e:
                raise RossoctlUnavailable(f"token endpoint unreachable: {e}") from e
            if resp.status_code != 200:
                raise RossoctlForbidden(
                    f"token request failed with HTTP {resp.status_code}: {_detail(resp)}"
                )
            body = resp.json()
            self._token = body.get("access_token")
            if not self._token:
                raise RossoctlForbidden("token endpoint returned no access_token")
            expires_in = float(body.get("expires_in") or 60)
            self._token_expiry = self._clock() + max(expires_in - 30, 0)
            return self._token

    # ---- requests --------------------------------------------------------- #

    async def _request(
        self,
        method: str,
        path: str,
        bearer: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        if not self.configured:
            raise RossoctlUnavailable("ROSSOCTL_BACKEND_URL is not set")
        url = f"{self.base_url}/api/v1{path}"
        for attempt in (0, 1):
            headers = dict(kwargs.pop("headers", {}) or {})
            token = bearer or await self._service_token(force=attempt == 1)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            try:
                async with self._client() as client:
                    resp = await client.request(method, url, headers=headers, **kwargs)
            except httpx.TimeoutException as e:
                raise RossoctlUnavailable(
                    f"rossoctl backend timed out: {method} {path}"
                ) from e
            except httpx.HTTPError as e:
                raise RossoctlUnavailable(f"rossoctl backend unreachable: {e}") from e
            if (
                resp.status_code == 401
                and attempt == 0
                and not bearer
                and self.uses_client_credentials
            ):
                logger.info(
                    "rossoctl backend returned 401; refreshing the service token"
                )
                self._token = None
                continue
            break
        if resp.status_code in (401, 403):
            raise RossoctlForbidden(
                f"rossoctl backend refused {method} {path}: {_detail(resp)}"
            )
        if resp.status_code == 404:
            raise RossoctlNotFound(_detail(resp) or f"{path} not found")
        if resp.status_code in (502, 503, 504):
            raise RossoctlUnavailable(_detail(resp) or f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            err = RossoctlError(
                f"rossoctl backend HTTP {resp.status_code}: {_detail(resp)}"
            )
            err.status_code = resp.status_code
            raise err
        return resp.json() if resp.content else None

    @staticmethod
    def _path(namespace: str, name: str, suffix: str = "") -> str:
        validate_label(name, "tool name")
        return f"/tools/{quote(namespace)}/{quote(name)}{suffix}"

    async def list_tools(
        self, namespace: str, bearer: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self.check_namespace(namespace)
        body = await self._request(
            "GET", "/tools", params={"namespace": namespace}, bearer=bearer
        )
        return list((body or {}).get("items") or [])

    async def get_tool(
        self, namespace: str, name: str, bearer: Optional[str] = None
    ) -> Dict[str, Any]:
        self.check_namespace(namespace)
        return (
            await self._request("GET", self._path(namespace, name), bearer=bearer) or {}
        )

    async def connect(
        self, namespace: str, name: str, bearer: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self.check_namespace(namespace)
        body = await self._request(
            "POST", self._path(namespace, name, "/connect"), bearer=bearer
        )
        return list((body or {}).get("tools") or [])

    async def invoke(
        self,
        namespace: str,
        name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        bearer: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.check_namespace(namespace)
        body = await self._request(
            "POST",
            self._path(namespace, name, "/invoke"),
            json={"tool_name": tool_name, "arguments": arguments},
            bearer=bearer,
        )
        return (body or {}).get("result") or {}


def service_port(tool_detail: Dict[str, Any], default: int = 8000) -> int:
    """The tool Service's first port from ``GET /tools/{ns}/{name}``."""
    service = tool_detail.get("service") or {}
    for port in service.get("ports") or []:
        value = port.get("port") if isinstance(port, dict) else None
        if isinstance(value, int) and 0 < value < 65536:
            return value
    return default
