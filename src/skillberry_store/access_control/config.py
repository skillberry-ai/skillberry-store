"""Access-control YAML config: load, validate, in-memory model.

See §5 of ``docs/design/access-control.md`` for the schema.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Set, TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from skillberry_store.access_control.pdp import Subject

logger = logging.getLogger(__name__)


DEFAULT_CONFIG_FILENAME = "access_control_config.yaml"

VALID_MODES = {"disabled", "standalone"}
RESERVED_MODES = {"delegated"}

# Known resources / verbs. Unknown values in a rule are dropped with a
# warning per §5.2.
KNOWN_RESOURCES = {
    "skills",
    "tools",
    "snippets",
    "vmcp_servers",
    "vnfs_servers",
    "admin",
    "plugins",
    "facets",
    "system",
    "*",
}
KNOWN_VERBS = {
    "list",
    "get",
    "create",
    "update",
    "delete",
    "search",
    "execute",
    "admin",
    "*",
}

DEFAULT_SESSION_TTL_SECONDS = 43200  # 12h


class AccessControlConfigError(Exception):
    """Hard-fail during config load (e.g. mode=standalone but file broken)."""


@dataclass
class User:
    username: str
    tenant_id: str
    password_hash: str
    groups: List[str] = field(default_factory=list)


@dataclass
class Rule:
    resources: List[str]
    verbs: List[str]


@dataclass
class Role:
    name: str
    rules: List[Rule] = field(default_factory=list)


@dataclass
class Subject:  # binding subject reference (kind/name), not the runtime Subject
    kind: str  # 'tenant' | 'group'
    name: str


@dataclass
class RoleBinding:
    name: str
    subjects: List[Subject]
    roles: List[str]
    # scope: parsed but not surfaced in step 1 (forward-compat). Kept as raw
    # mapping if present, else None.
    scope: Optional[dict] = None


@dataclass
class AccessControlConfig:
    mode: str = "disabled"
    unauthenticated_paths: List[str] = field(default_factory=list)
    users: List[User] = field(default_factory=list)
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    roles: List[Role] = field(default_factory=list)
    bindings: List[RoleBinding] = field(default_factory=list)

    # -------- lookups -------------------------------------------------- #
    def role(self, name: str) -> Optional[Role]:
        for r in self.roles:
            if r.name == name:
                return r
        return None

    def user(self, username: str) -> Optional[User]:
        for u in self.users:
            if u.username == username:
                return u
        return None

    def roles_for(self, subject: "Subject") -> List[str]:
        """Return the union of role names bound to this subject."""
        result: List[str] = []
        seen: Set[str] = set()
        tenant_id = subject.tenant_id
        groups = set(subject.groups or [])
        for b in self.bindings:
            if not _binding_matches(b, tenant_id, groups):
                continue
            for role_name in b.roles:
                if role_name not in seen:
                    seen.add(role_name)
                    result.append(role_name)
        return result

    def is_unauthenticated(self, method: str, path: str) -> bool:
        method = method.upper()
        for entry in self.unauthenticated_paths:
            m, p = _split_method_path(entry)
            if m is None or m == method:
                if _path_matches(p, path):
                    return True
        return False


def _binding_matches(b: RoleBinding, tenant_id: Optional[str], groups: Set[str]) -> bool:
    for s in b.subjects:
        if s.kind == "tenant" and tenant_id is not None and s.name == tenant_id:
            return True
        if s.kind == "group" and s.name in groups:
            return True
    return False


def _split_method_path(entry: str) -> tuple[Optional[str], str]:
    """Parse ``'GET /health'`` into ``('GET', '/health')``; bare paths → (None, path)."""
    parts = entry.strip().split(None, 1)
    if len(parts) == 2 and parts[0].isalpha():
        return parts[0].upper(), parts[1]
    return None, entry.strip()


def _path_matches(pattern: str, path: str) -> bool:
    """Loose match: exact, or pattern with a trailing '*' as a prefix match."""
    if pattern.endswith("*"):
        return path.startswith(pattern[:-1])
    return path == pattern


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
_DEFAULT_UNAUTH_PATHS = [
    "GET /health",
    "GET /health/ready",
    "GET /admin/metrics",
    "POST /auth/login",
    # Logout and whoami need to be reachable without RBAC: they self-resolve
    # the bearer token from the request. See §7.2 / §10.4.
    "POST /auth/logout",
    "GET /auth/whoami",
    "GET /docs",
    "GET /openapi.json",
    "GET /redoc",
    # Root redirect and SPA deep-links → /ui: public, no auth needed.
    # HEAD is listed alongside GET because the /ui handler serves both (the
    # audit requires *every* method on a route to be allow-listed).
    "GET /",
    "GET /ui*",
    "HEAD /ui*",
    # Every /control_sse* path is a Control MCP transport (SSE handshake +
    # JSON-RPC messages), including per-tenant mount points like
    # /control_sse/<username>. The tool invocations that the transport
    # forwards ARE gated by the enforce dependency on re-dispatch; the
    # transport itself is not (SSE mounts are Starlette ``Mount`` objects,
    # so router-level deps don't reach them either — the allow-list entry
    # is defensive belt-and-braces).
    "GET /control_sse*",
    "POST /control_sse*",
]


def _resolve_config_path(path: Optional[str]) -> str:
    return (
        path
        or os.environ.get("SBS_ACCESS_CONTROL_CONFIG")
        or DEFAULT_CONFIG_FILENAME
    )


def _resolve_session_ttl(yaml_value: Optional[int]) -> int:
    env_val = os.environ.get("SBS_SESSION_TTL")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            logger.warning("SBS_SESSION_TTL=%r is not an int; ignoring", env_val)
    if yaml_value is not None:
        try:
            return int(yaml_value)
        except (TypeError, ValueError):
            logger.warning(
                "standalone.session_ttl_seconds=%r is not an int; using default",
                yaml_value,
            )
    return DEFAULT_SESSION_TTL_SECONDS


def load_config(path: Optional[str] = None) -> AccessControlConfig:
    """Load and validate the access-control YAML.

    Returns an ``AccessControlConfig`` instance. Behavior:

    * Missing file, ``mode`` unset or ``disabled`` -> defaults (disabled).
    * Missing/broken file with ``mode: standalone`` -> hard fail
      (``AccessControlConfigError``), per §5.2 fail-closed principle.
    * Unknown resource/verb tokens in rules -> warn + drop rule, per §5.2.
    * ``mode: delegated`` -> hard fail with a clear "not yet supported" msg.
    """
    cfg_path = _resolve_config_path(path)

    if not os.path.isfile(cfg_path):
        logger.info(
            "Access-control config file not present at %s; using defaults "
            "(mode=disabled)",
            cfg_path,
        )
        return AccessControlConfig(
            mode="disabled",
            unauthenticated_paths=list(_DEFAULT_UNAUTH_PATHS),
        )

    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    except Exception as e:  # noqa: BLE001
        # Can't peek at mode; assume worst case -> fail closed if the file
        # exists but is broken.
        raise AccessControlConfigError(
            f"Failed to parse access-control config {cfg_path}: {e}"
        ) from e

    if not isinstance(raw, dict):
        raise AccessControlConfigError(
            f"Access-control config {cfg_path} is not a mapping"
        )

    mode = raw.get("mode", "disabled")
    if mode in RESERVED_MODES:
        raise AccessControlConfigError(
            f"Access-control mode '{mode}' is reserved but not yet supported"
        )
    if mode not in VALID_MODES:
        # Malformed mode: fail-closed only if it wasn't 'disabled' by intent.
        raise AccessControlConfigError(
            f"Unknown access-control mode '{mode}' (valid: {sorted(VALID_MODES)})"
        )

    unauth_paths = list(raw.get("unauthenticated_paths") or _DEFAULT_UNAUTH_PATHS)

    standalone = raw.get("standalone") or {}
    if not isinstance(standalone, dict):
        raise AccessControlConfigError(
            f"'standalone' block in {cfg_path} must be a mapping"
        )
    session_ttl = _resolve_session_ttl(standalone.get("session_ttl_seconds"))
    users = _parse_users(standalone.get("users") or [], cfg_path)

    roles = _parse_roles(raw.get("roles") or [], cfg_path)
    bindings = _parse_bindings(raw.get("bindings") or [], cfg_path)

    # Cross-reference validation.
    role_names = {r.name for r in roles}
    for b in bindings:
        for role_name in b.roles:
            if role_name not in role_names:
                if mode == "standalone":
                    raise AccessControlConfigError(
                        f"Binding '{b.name}' references unknown role '{role_name}'"
                    )
                logger.warning(
                    "Binding '%s' references unknown role '%s' (ignored in "
                    "disabled mode)",
                    b.name,
                    role_name,
                )

    cfg = AccessControlConfig(
        mode=mode,
        unauthenticated_paths=unauth_paths,
        users=users,
        session_ttl_seconds=session_ttl,
        roles=roles,
        bindings=bindings,
    )
    logger.info(
        "Loaded access-control config from %s: mode=%s, users=%d, roles=%d, "
        "bindings=%d",
        cfg_path,
        cfg.mode,
        len(cfg.users),
        len(cfg.roles),
        len(cfg.bindings),
    )
    return cfg


def _parse_users(raw_users: Iterable, cfg_path: str) -> List[User]:
    users: List[User] = []
    for raw in raw_users:
        if not isinstance(raw, dict):
            logger.warning("Skipping non-mapping user entry in %s: %r", cfg_path, raw)
            continue
        username = raw.get("username")
        password_hash = raw.get("password_hash")
        if not username or not password_hash:
            logger.warning(
                "Skipping user with missing username/password_hash in %s: %r",
                cfg_path,
                raw,
            )
            continue
        users.append(
            User(
                username=str(username),
                tenant_id=str(raw.get("tenant_id") or username),
                password_hash=str(password_hash),
                groups=list(raw.get("groups") or []),
            )
        )
    return users


def _parse_roles(raw_roles: Iterable, cfg_path: str) -> List[Role]:
    roles: List[Role] = []
    for raw in raw_roles:
        if not isinstance(raw, dict):
            logger.warning("Skipping non-mapping role entry in %s: %r", cfg_path, raw)
            continue
        name = raw.get("name")
        if not name:
            logger.warning("Skipping role with no name in %s: %r", cfg_path, raw)
            continue
        rules: List[Rule] = []
        for raw_rule in raw.get("rules") or []:
            if not isinstance(raw_rule, dict):
                continue
            resources = _filter_tokens(
                raw_rule.get("resources") or [],
                KNOWN_RESOURCES,
                f"role '{name}'",
                "resource",
            )
            verbs = _filter_tokens(
                raw_rule.get("verbs") or [],
                KNOWN_VERBS,
                f"role '{name}'",
                "verb",
            )
            if not resources or not verbs:
                continue
            rules.append(Rule(resources=resources, verbs=verbs))
        roles.append(Role(name=str(name), rules=rules))
    return roles


def _filter_tokens(
    tokens: Iterable, allowed: Set[str], context: str, kind: str
) -> List[str]:
    result: List[str] = []
    for t in tokens:
        if t in allowed:
            result.append(t)
        else:
            logger.warning(
                "Dropping unknown %s '%s' in %s", kind, t, context
            )
    return result


def _parse_bindings(raw_bindings: Iterable, cfg_path: str) -> List[RoleBinding]:
    bindings: List[RoleBinding] = []
    for raw in raw_bindings:
        if not isinstance(raw, dict):
            logger.warning(
                "Skipping non-mapping binding entry in %s: %r", cfg_path, raw
            )
            continue
        name = raw.get("name") or f"binding-{len(bindings)}"
        subjects_raw = raw.get("subjects") or []
        subjects: List[Subject] = []
        for s in subjects_raw:
            if not isinstance(s, dict):
                continue
            kind = s.get("kind")
            s_name = s.get("name")
            if kind not in ("tenant", "group") or not s_name:
                logger.warning(
                    "Skipping invalid subject in binding '%s': %r", name, s
                )
                continue
            subjects.append(Subject(kind=str(kind), name=str(s_name)))
        roles = [str(r) for r in (raw.get("roles") or [])]
        scope = raw.get("scope")  # parsed but ignored in step 1
        bindings.append(
            RoleBinding(
                name=str(name),
                subjects=subjects,
                roles=roles,
                scope=scope if isinstance(scope, dict) else None,
            )
        )
    return bindings


# --------------------------------------------------------------------------- #
# Cached loader (mirrors endpoint_auth.get_config).
# --------------------------------------------------------------------------- #
_config_cache: Optional[AccessControlConfig] = None
_config_path_loaded: Optional[str] = None


def get_config(path: Optional[str] = None) -> AccessControlConfig:
    """Return the cached access-control config, loading it on first use."""
    global _config_cache, _config_path_loaded
    cfg_path = _resolve_config_path(path)
    if _config_cache is None or _config_path_loaded != cfg_path:
        _config_cache = load_config(cfg_path)
        _config_path_loaded = cfg_path
    return _config_cache


def reset_config_cache() -> None:
    global _config_cache, _config_path_loaded
    _config_cache = None
    _config_path_loaded = None
