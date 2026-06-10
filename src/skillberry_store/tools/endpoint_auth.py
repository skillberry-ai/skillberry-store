# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Per-endpoint authentication for outbound skill-import fetches.

Configuration lives in a YAML file (``config.yaml`` by default, overridable via
the ``SBS_CONFIG_FILE`` env var) holding a list of endpoint entries. When a URL
is fetched during a skill import, the entry whose ``endpoint`` matches the URL
supplies the auth. For a matched endpoint, auth is resolved in this order:

1. ``api_key``  - a configured API key/token, sent as ``Authorization: Bearer``.
2. ``login_url`` (forced-reauthentication) - no stored token; the API returns
   this URL and the caller retries with an ``X-Endpoint-Token`` header carrying
   a token they obtained from the provider.
3. **OAuth discovery** - if neither of the above is set, try to discover the
   provider's login endpoint via RFC 8414 / OpenID Connect well-known metadata
   and use that as the login URL (forced-reauthentication).

The architecture is provider-agnostic: the only assumption is that the remote
accepts an ``Authorization: Bearer <token>`` API token.

When no endpoint entry matches, falls back to the ``API_KEY`` env var so simple
deployments can set one global key.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse

import requests
import yaml

logger = logging.getLogger(__name__)

# Auth modes
MODE_API_KEY = "api_key"
MODE_FORCED_REAUTH = "forced-reauthentication"

_DEFAULT_CONFIG_FILENAME = "config.yaml"

# RFC 8414 / OIDC well-known discovery paths, tried in order.
_DISCOVERY_PATHS = (
    "/.well-known/oauth-authorization-server",
    "/.well-known/openid-configuration",
)


# --------------------------------------------------------------------------- #
# Exception carrying login data up to the API layer
# --------------------------------------------------------------------------- #
class ReauthRequired(Exception):
    """Raised when a matched endpoint has no usable token.

    Carries the ``login_url`` the user should visit to obtain a token, which
    they then resend via the ``X-Endpoint-Token`` header.
    """

    def __init__(self, login_url: Optional[str]):
        self.login_url = login_url
        super().__init__(f"Authentication required; log in at: {login_url}")


# --------------------------------------------------------------------------- #
# Config model
# --------------------------------------------------------------------------- #
@dataclass
class EndpointAuth:
    endpoint: str
    api_key: Optional[str] = None
    login_url: Optional[str] = None

    @property
    def mode(self) -> str:
        if self.api_key:
            return MODE_API_KEY
        return MODE_FORCED_REAUTH


@dataclass
class EndpointAuthConfig:
    endpoints: List[EndpointAuth] = field(default_factory=list)

    def resolve(self, url: str) -> Optional[EndpointAuth]:
        """Return the best-matching endpoint entry for ``url``, or None.

        An entry matches when its ``endpoint`` equals the URL host, or the URL
        (string) starts with the ``endpoint`` value (prefix match). The entry
        with the longest ``endpoint`` string wins, so more specific configs
        (org/path scoped) take precedence over a bare host.
        """
        if not url or not self.endpoints:
            return None
        host = (urlparse(url).hostname or "").lower()
        best: Optional[EndpointAuth] = None
        for entry in self.endpoints:
            ep = entry.endpoint.rstrip("/")
            ep_host = (urlparse(ep).hostname or ep).lower()
            matched = host == ep_host or url.startswith(entry.endpoint)
            if matched and (best is None or len(entry.endpoint) > len(best.endpoint)):
                best = entry
        return best


# --------------------------------------------------------------------------- #
# Loading (cached module-level)
# --------------------------------------------------------------------------- #
_config_cache: Optional[EndpointAuthConfig] = None
_config_path_loaded: Optional[str] = None


def _resolve_config_path(path: Optional[str]) -> str:
    return path or os.environ.get("SBS_CONFIG_FILE") or _DEFAULT_CONFIG_FILENAME


def load_endpoint_auth_config(path: Optional[str] = None) -> EndpointAuthConfig:
    """Load and parse the endpoint-auth config.

    Missing file => empty config (not an error). Malformed file => warning +
    empty config, so a bad file never crashes startup or imports.
    """
    cfg_path = _resolve_config_path(path)
    if not os.path.isfile(cfg_path):
        return EndpointAuthConfig()

    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as e:  # noqa: BLE001 - never let config break the app
        logger.warning("Failed to read config file %s: %s", cfg_path, e)
        return EndpointAuthConfig()

    entries: List[EndpointAuth] = []
    for raw in (data.get("endpoints") or []):
        if not isinstance(raw, dict) or not raw.get("endpoint"):
            logger.warning("Skipping invalid endpoint entry in %s: %r", cfg_path, raw)
            continue
        entries.append(
            EndpointAuth(
                endpoint=str(raw["endpoint"]),
                api_key=raw.get("api_key"),
                login_url=raw.get("login_url"),
            )
        )
    return EndpointAuthConfig(endpoints=entries)


def get_config(path: Optional[str] = None) -> EndpointAuthConfig:
    """Return the shared, cached config instance, loading it on first use."""
    global _config_cache, _config_path_loaded
    cfg_path = _resolve_config_path(path)
    if _config_cache is None or _config_path_loaded != cfg_path:
        _config_cache = load_endpoint_auth_config(cfg_path)
        _config_path_loaded = cfg_path
        logger.info(
            "Loaded endpoint-auth config from %s (%d endpoint entries)",
            cfg_path if os.path.isfile(cfg_path) else "(none)",
            len(_config_cache.endpoints),
        )
    return _config_cache


def reset_config_cache() -> None:
    """Clear the cached config (test helper / for reload)."""
    global _config_cache, _config_path_loaded
    _config_cache = None
    _config_path_loaded = None


# --------------------------------------------------------------------------- #
# OAuth login-endpoint discovery (RFC 8414 / OIDC), cached per host
# --------------------------------------------------------------------------- #
_discovery_cache: Dict[str, Optional[str]] = {}


def discover_login_url(url: str) -> Optional[str]:
    """Discover a provider's login (authorization) endpoint for ``url``'s host.

    Tries the RFC 8414 and OIDC well-known metadata documents and returns the
    ``authorization_endpoint`` if present. Result (including a None "no
    discovery" answer) is cached per host. Network/parse failures => None;
    providers without metadata (e.g. github.com) simply return None.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    if host in _discovery_cache:
        return _discovery_cache[host]

    base = (parsed.scheme or "https", parsed.netloc, "", "", "", "")
    found: Optional[str] = None
    for path in _DISCOVERY_PATHS:
        well_known = urlunparse(
            (base[0], base[1], path, "", "", "")
        )
        try:
            resp = requests.get(
                well_known, headers={"Accept": "application/json"}, timeout=10
            )
            if not resp.ok:
                continue
            meta = resp.json()
            endpoint = meta.get("authorization_endpoint")
            if endpoint:
                found = endpoint
                logger.info(
                    "Discovered authorization_endpoint for %s via %s: %s",
                    host,
                    path,
                    endpoint,
                )
                break
        except Exception as e:  # noqa: BLE001 - discovery is best-effort
            logger.debug("Discovery probe %s failed: %s", well_known, e)
            continue

    _discovery_cache[host] = found
    return found


def reset_discovery_cache() -> None:
    """Clear the per-host discovery cache (test helper)."""
    _discovery_cache.clear()


# --------------------------------------------------------------------------- #
# Header resolution - the single entry point used by the importer / API
# --------------------------------------------------------------------------- #
def _bearer(token: Optional[str]) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def resolve_auth_headers(
    url: Optional[str],
    *,
    override_token: Optional[str] = None,
    anonymous: bool = False,
    config: Optional[EndpointAuthConfig] = None,
) -> Dict[str, str]:
    """Resolve Authorization headers for fetching ``url``.

    If ``anonymous`` is True, no authentication is attempted at all: returns
    empty headers without consulting the config, env key, or discovery, and
    never raises ReauthRequired. This is the default for interactive imports
    so that public sources work with zero setup.

    Otherwise, resolution for a matched endpoint, in order:
      1. ``api_key``                -> Bearer api_key
      2. caller ``override_token``  -> Bearer override_token (the retry path)
      3. ``login_url``              -> raise ReauthRequired(login_url)
      4. OAuth discovery            -> raise ReauthRequired(discovered_url)
                                       (or, if nothing is discovered, with None)

    No matching endpoint -> ``API_KEY`` env fallback (or anonymous ``{}``).

    Raises:
        ReauthRequired
    """
    if anonymous:
        return {}

    cfg = config if config is not None else get_config()
    entry = cfg.resolve(url) if url else None

    if entry is None:
        # Legacy/simple behavior: single global key, or anonymous.
        return _bearer(os.environ.get("API_KEY"))

    # 1. Configured API key wins.
    if entry.api_key:
        return _bearer(entry.api_key)

    # 2. A token supplied on the retry (X-Endpoint-Token) is used as-is.
    if override_token:
        return _bearer(override_token)

    # 3. Explicit login URL (forced-reauthentication).
    if entry.login_url:
        raise ReauthRequired(entry.login_url)

    # 4. No explicit URL: try to auto-discover the provider's login endpoint.
    discovered = discover_login_url(url) if url else None
    raise ReauthRequired(discovered)
