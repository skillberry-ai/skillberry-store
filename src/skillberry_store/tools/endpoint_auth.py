# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Per-endpoint authentication for outbound skill-import fetches.

Configuration lives in a YAML file (``import_auth_config.yaml`` by default,
overridable via the ``SBS_IMPORT_AUTH_CONFIG`` env var). It mirrors the shape of
``gh``'s ``~/.config/gh/hosts.yml``: a mapping keyed by hostname, each value a
dict of ``user`` / ``oauth_token`` / ``git_protocol`` (plus an optional
``login_url``). When a URL is fetched during a skill import, the entry whose host
matches the URL's hostname supplies the auth. For a matched host, auth is
resolved in this order:

1. ``oauth_token`` - a configured token, sent as ``Authorization: Bearer``.
2. ``login_url`` (forced-reauthentication) - no stored token; the API returns
   this URL and the caller retries with an ``X-Endpoint-Token`` header carrying
   a token they obtained from the provider.
3. **GitHub CLI credentials** - if neither of the above is set, fall back to the
   token stored by the ``gh`` CLI in ``~/.config/gh/hosts.yml`` (skill import
   currently supports GitHub only). If none is found, the fetch is anonymous.

The remote is assumed to accept an ``Authorization: Bearer <token>`` API token.

When no endpoint entry matches, falls back to the ``API_KEY`` env var, then to
GitHub CLI credentials, then to anonymous access.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

import yaml

logger = logging.getLogger(__name__)

# Auth modes
MODE_API_KEY = "api_key"
MODE_FORCED_REAUTH = "forced-reauthentication"

_DEFAULT_CONFIG_FILENAME = "import_auth_config.yaml"


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
    """Auth for a single host, mirroring the shape of ``gh``'s hosts.yml.

    ``host`` is the YAML key (e.g. ``github.com``). ``oauth_token`` is the
    stored token, sent as ``Authorization: Bearer``. ``user`` and
    ``git_protocol`` are carried for parity with ``gh`` but are advisory only.
    ``login_url`` is the forced-reauthentication target when no token is stored.
    """

    host: str
    user: Optional[str] = None
    oauth_token: Optional[str] = None
    git_protocol: Optional[str] = None
    login_url: Optional[str] = None

    @property
    def mode(self) -> str:
        if self.oauth_token:
            return MODE_API_KEY
        return MODE_FORCED_REAUTH


@dataclass
class EndpointAuthConfig:
    endpoints: List[EndpointAuth] = field(default_factory=list)

    def resolve(self, url: str) -> Optional[EndpointAuth]:
        """Return the host entry matching ``url``'s hostname, or None.

        Matching is by hostname equality (case-insensitive), the same shape as
        ``gh``'s hosts.yml where each top-level key is a bare host.
        """
        if not url or not self.endpoints:
            return None
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return None
        for entry in self.endpoints:
            if entry.host.lower() == host:
                return entry
        return None


# --------------------------------------------------------------------------- #
# Loading (cached module-level)
# --------------------------------------------------------------------------- #
_config_cache: Optional[EndpointAuthConfig] = None
_config_path_loaded: Optional[str] = None


def _resolve_config_path(path: Optional[str]) -> str:
    return path or os.environ.get("SBS_IMPORT_AUTH_CONFIG") or _DEFAULT_CONFIG_FILENAME


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

    if not isinstance(data, dict):
        logger.warning(
            "Config file %s is not a host-keyed mapping; ignoring.", cfg_path
        )
        return EndpointAuthConfig()

    entries: List[EndpointAuth] = []
    for host, raw in data.items():
        if not host or not isinstance(raw, dict):
            logger.warning(
                "Skipping invalid host entry in %s: %r: %r", cfg_path, host, raw
            )
            continue
        entries.append(
            EndpointAuth(
                host=str(host),
                user=raw.get("user"),
                oauth_token=raw.get("oauth_token"),
                git_protocol=raw.get("git_protocol"),
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
# GitHub CLI credential fallback (~/.config/gh/hosts.yml)
# --------------------------------------------------------------------------- #
# Default location of the GitHub CLI's stored hosts/credentials. Skill imports
# currently support GitHub only, so this reads the github.com token if `gh` has
# stored one in plaintext there.
_GH_HOSTS_PATH = os.path.expanduser("~/.config/gh/hosts.yml")
_GH_HOST = "github.com"


def gh_cli_token(host: str = _GH_HOST) -> Optional[str]:
    """Return the GitHub CLI's stored token for ``host``, or None.

    Reads ``~/.config/gh/hosts.yml`` and returns the ``oauth_token`` for the
    given host if present. Note: when `gh` stores tokens in the OS keyring
    (the default on many systems), hosts.yml has no ``oauth_token`` field and
    this returns None — there is no token to read from the file in that case.
    Missing/unreadable file => None (so resolution falls through to anonymous).
    """
    if not os.path.isfile(_GH_HOSTS_PATH):
        return None
    try:
        with open(_GH_HOSTS_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as e:  # noqa: BLE001 - best-effort, never break imports
        logger.debug("Could not read %s: %s", _GH_HOSTS_PATH, e)
        return None
    host_cfg = data.get(host)
    if not isinstance(host_cfg, dict):
        logger.info(
            "No GitHub CLI credentials for %s in %s; falling back to anonymous.",
            host,
            _GH_HOSTS_PATH,
        )
        return None
    token = host_cfg.get("oauth_token")
    if not token:
        # `gh` keeps the token in the OS keyring (its default), so hosts.yml has
        # no plaintext oauth_token to read. Surface it and fall back to anonymous.
        logger.warning(
            "GitHub CLI token for %s is not in %s (likely stored in the OS "
            "keyring); cannot read it from the file — falling back to anonymous.",
            host,
            _GH_HOSTS_PATH,
        )
        return None
    logger.info("Using GitHub CLI credentials from %s for %s", _GH_HOSTS_PATH, host)
    return token


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
    empty headers without consulting the config, env key, or gh credentials,
    and never raises ReauthRequired. This is the default for interactive
    imports so that public sources work with zero setup.

    Otherwise, resolution for a matched endpoint, in order:
      1. ``oauth_token``            -> Bearer oauth_token
      2. caller ``override_token``  -> Bearer override_token (the retry path)
      3. ``login_url``              -> raise ReauthRequired(login_url)
      4. GitHub CLI credentials     -> Bearer token from ~/.config/gh/hosts.yml
      5. otherwise                  -> anonymous ({})

    No matching endpoint -> ``API_KEY`` env, then GitHub CLI credentials, then
    anonymous ({}).

    Raises:
        ReauthRequired
    """
    if anonymous:
        return {}

    cfg = config if config is not None else get_config()
    entry = cfg.resolve(url) if url else None

    if entry is None:
        # No endpoint configured: a global API_KEY, then gh credentials, then
        # anonymous.
        return _bearer(os.environ.get("API_KEY") or gh_cli_token())

    # 1. Configured oauth_token wins.
    if entry.oauth_token:
        return _bearer(entry.oauth_token)

    # 2. A token supplied on the retry (X-Endpoint-Token) is used as-is.
    if override_token:
        return _bearer(override_token)

    # 3. Explicit login URL (forced-reauthentication).
    if entry.login_url:
        raise ReauthRequired(entry.login_url)

    # 4. Fall back to the GitHub CLI's stored credentials, if any.
    gh_token = gh_cli_token()
    if gh_token:
        return _bearer(gh_token)

    # 5. Nothing available -> anonymous.
    return {}
