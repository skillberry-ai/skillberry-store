"""Store API for plugin access to content.

Thin proxy that delegates to service layer. Provides a stable interface
for plugins without exposing internal implementation details.

One instance is constructed per process and handed to the plugin loader,
which gives each plugin its own **per-slug view** via :meth:`StoreAPI.for_plugin`.
The view shares the services but knows which plugin is calling — without that,
an outcome cannot be attributed to a plugin, an autonomous operation cannot
resolve whose owner tenant applies, and per-plugin authorization has nothing
to key on (plugin-identity §2.4).

**This class is enforcement point 2.** A core HTTP request is decided once, at
the PEP. A plugin reaches the store in-process — no HTTP, no router, no
dependency — so its calls would otherwise never be decided at all. Every named
method here therefore opens with :meth:`StoreAPI._admit`, which calls the same
``authorize()`` with the same config against the ambient subject the PEP or the
event dispatcher published (§2.2).

A plugin *API* call is consequently decided twice: at the door for the pair its
route declared, and here per object it actually touches. That is deliberate
rather than redundant — the door refuses a caller early with a clean 403, and
``_admit`` covers the fan-out a single ``@requires`` pair cannot express (SAST
scanning a skill reaches its tools *and* its snippets; DAST needs ``tools:get``
and ``tools:execute`` on the way to a ``skills:update``).
"""

import copy
from typing import Any, Dict, List, Optional
import logging
import warnings

from skillberry_store.access_control.config import AccessControlConfig
from skillberry_store.access_control.context import current_subject
from skillberry_store.access_control.pdp import authorize
from skillberry_store.plugins.errors import (
    PluginAuthorizationError,
    PluginIdentityError,
)
from skillberry_store.plugins.outcomes import OUTCOME_ERROR, record_outcome

logger = logging.getLogger(__name__)

_HANDLER_PROPERTY_DEPRECATION = (
    "StoreAPI.{name} returns the raw ObjectHandler and is deprecated for plugin "
    "use: it exposes the whole persistence layer, not a supported interface. Use "
    "the named accessors instead — get_tool_module()/update_tool_module() for "
    "module source, and update_tool()/update_skill()/update_snippet() to write a "
    "complete object."
)

_HANDLER_PROPERTY_REFUSED = (
    "StoreAPI.{name} is unavailable while access control is enabled: it returns "
    "the raw ObjectHandler, which reaches write_dict, write_file and the locks "
    "without passing admission control — enforcement point 2 would report full "
    "coverage while a caller bypassed it entirely. Use the named accessors "
    "instead (get_tool_module()/update_tool_module() for module source, "
    "update_tool()/update_skill()/update_snippet() to write a complete object); "
    "each of those is admitted by the PDP."
)


def _warn_handler_property(name: str) -> None:
    warnings.warn(
        _HANDLER_PROPERTY_DEPRECATION.format(name=name),
        DeprecationWarning,
        stacklevel=3,
    )


class StoreAPI:
    """Plugin interface — delegates to service layer."""

    def __init__(
        self,
        services: Dict[str, Any],
        cfg: AccessControlConfig,
        sessions: Optional[Any] = None,
    ):
        """
        Args:
            services: the service-layer registry to delegate to.
            cfg: access-control config. **Required, deliberately not
                defaulted.** A ``cfg=None`` default that skipped enforcement
                would be exactly the fail-open shape the marker system was
                designed to avoid: a construction site that forgot to pass it
                would silently disable enforcement point 2 while every test
                still passed.
            sessions: the session store, used to mint short-lived tokens for a
                plugin's out-of-process calls (§4.5). ``None`` means no token
                can be minted.
        """
        self._cfg = cfg
        self._sessions = sessions
        # Where each tenant's Control MCP is mounted, filled in by the server
        # once the mounts exist. Held in ONE mutable dict deliberately:
        # ``for_plugin`` shallow-copies, so every per-plugin view shares this
        # object and sees a late assignment. Rebinding the attribute instead
        # would leave the views (created during plugin discovery, before the
        # mounts exist) permanently empty.
        self._mcp: Dict[str, Any] = {"mounts": {}, "default": None}
        self.tools_service = services.get("tools")
        self.skills_service = services.get("skills")
        self.snippets_service = services.get("snippets")
        self.vnfs_service = services.get("vnfs")
        self.vmcp_service = services.get("vmcp")
        # Which plugin this view belongs to. ``None`` on the shared instance
        # the server constructs; set on each view handed to a plugin.
        self._slug: Optional[str] = None

    # ── Enforcement point 2 ────────────────────────────────────────────────

    @property
    def acl_enabled(self) -> bool:
        """Whether admission control applies to this store API's calls."""
        return self._cfg.mode != "disabled"

    def _admit(self, resource: str, verb: str, uuid: Optional[str] = None) -> None:
        """Authorize one store operation for the ambient subject, or raise.

        Raises rather than returning a bool: translating a refusal to HTTP
        belongs on the app (see :mod:`skillberry_store.plugins.errors`), and a
        bool would let a caller ignore the answer.

        Records the outcome on the object itself before raising, because on the
        event path the raise reaches nothing but a log line — background tasks
        sit outside any request, so the app-level handlers cannot fire (§8).
        """
        if not self.acl_enabled:
            # No tenants exist in this mode, so there is nothing to decide.
            return
        subject = current_subject()
        if subject is None or not subject.tenant_id:
            reason = (
                "no tenant in context; assign an owner tenant for autonomous "
                "work (per plugin by enabling it as that tenant, or "
                "deployment-wide via plugins.owner_tenant)"
            )
            self._record_outcome(uuid, reason)
            raise PluginIdentityError(reason)
        decision = authorize(subject, resource, verb, self._cfg)
        if not decision.allowed:
            self._record_outcome(uuid, decision.reason)
            raise PluginAuthorizationError(decision.reason)

    def _record_outcome(self, uuid: Optional[str], reason: str) -> None:
        """Label the object with this plugin's failure, above plugin code.

        Deliberately not gated by the identity that was just refused — that is
        the whole point (§9.1). One consequence worth naming: a refused *read*
        also writes, so a caller who cannot read an object can still cause a
        fixed ``<slug>:error`` tag on it. The tag vocabulary is closed and the
        reason comes from the PDP, never from the caller, so the write is
        bounded; recording it is what keeps a refusal distinguishable from
        "never ran".
        """
        record_outcome(
            {
                "skills": self.skills_service,
                "tools": self.tools_service,
                "snippets": self.snippets_service,
            },
            self._slug,
            uuid,
            OUTCOME_ERROR,
            reason,
        )

    @property
    def slug(self) -> Optional[str]:
        """The plugin this view was created for, or ``None`` if it is shared."""
        return self._slug

    # ── Out-of-process delegation (§4.5) ───────────────────────────────────

    def set_mcp_mounts(
        self, mounts: Dict[str, str], default: Optional[str] = None
    ) -> None:
        """Record where each tenant's Control MCP is mounted.

        Called once by the server after the mounts are created. ``default`` is
        the single shared mount used in ``disabled`` mode, where no tenant
        concept exists.
        """
        self._mcp["mounts"] = dict(mounts)
        self._mcp["default"] = default

    def mcp_mount_path(self) -> Optional[str]:
        """The Control MCP mount path for the ambient subject, or ``None``.

        ``None`` means this identity has no MCP surface — an agent handed a URL
        built from it would connect to nothing. That is honest rather than
        convenient: the per-subject mount loop covers configured users and
        plugin owner tenants, and a subject outside both has no surface.
        """
        if not self.acl_enabled:
            return self._mcp["default"]
        subject = current_subject()
        if subject is None or not subject.tenant_id:
            return None
        return self._mcp["mounts"].get(subject.tenant_id)

    def internal_token(self, ttl_seconds: Optional[int] = None) -> Optional[str]:
        """Mint a short-lived bearer token for the ambient subject.

        Context variables stop at the process boundary, so an out-of-process
        agent needs the identity *materialized*. ``SessionStore.mint`` takes no
        credential — ``AuthService.login`` does the bcrypt check and then calls
        it as a separate step — so a plugin sharing the process can mint for the
        subject it is already running as. No password, no hash, no environment
        variable, nothing on disk: the credential is derived from identity the
        store already holds and dies with the process.

        Under P3 this is the *calling* tenant, so the agent's calls re-enter
        through the PEP as that tenant and are admitted against its own role —
        nothing is escalated. Under P1 it is the owner tenant.

        Returns ``None`` in ``disabled`` mode: there is no PEP to validate a
        token and ``/control_sse`` is already unauthenticated, so minting would
        be pointless. Callers must not inject an empty ``Authorization`` header.

        Raises:
            PluginIdentityError: if no tenant is in scope (P5). Minting is the
                first step of an outward call, so it fails rather than
                producing an anonymous one.
        """
        if not self.acl_enabled:
            return None
        subject = current_subject()
        if subject is None or not subject.tenant_id:
            raise PluginIdentityError(
                "no tenant in context; cannot mint a token for an outward call"
            )
        if self._sessions is None:
            logger.error(
                "Plugin %r asked for a token but no session store was injected",
                self._slug,
            )
            return None
        ttl = ttl_seconds or self._cfg.plugin_token_ttl_seconds
        token, _expires_at = self._sessions.mint(
            subject.tenant_id, list(subject.groups), ttl
        )
        # Never logged: a minted token is a real bearer token and anything it is
        # handed to inherits the subject's rights until it expires (§8).
        logger.info(
            "Minted a %ss Control MCP token for tenant %s (plugin %r)",
            ttl,
            subject.tenant_id,
            self._slug,
        )
        return token

    def mcp_sse_config(self, base_url: str) -> Optional[Dict[str, Any]]:
        """A Claude-Code MCP server entry for this store, as the ambient subject.

        ``base_url`` is the scheme://host:port the agent can reach this store on
        — the plugin knows its own deployment shape, this class knows the
        identity. Returns ``None`` when the ambient subject has no mount.
        """
        path = self.mcp_mount_path()
        if not path:
            return None
        entry: Dict[str, Any] = {"type": "sse", "url": f"{base_url.rstrip('/')}{path}"}
        token = self.internal_token()
        if token:
            entry["headers"] = {"Authorization": f"Bearer {token}"}
        return entry

    def for_plugin(self, slug: str) -> "StoreAPI":
        """A view of this store API that knows which plugin is calling.

        A shallow copy rather than a delegating facade: it shares every service
        object with the shared instance (so there is one set of handlers and
        one set of locks) while carrying its own ``_slug``, and it needs no
        per-method forwarding that a new ``StoreAPI`` method could be forgotten
        from. A test that injects a fake through the deprecated handler
        properties writes to its own view rather than to every plugin's.
        """
        view = copy.copy(self)
        view._slug = slug
        return view

    @property
    def tools(self):
        """Deprecated: the raw tools ObjectHandler.

        Retained for out-of-tree plugins and for test injection. In-tree callers
        use the named accessors; see :func:`_warn_handler_property`.
        """
        self._refuse_handler_property("tools")
        _warn_handler_property("tools")
        # For testing: check if attribute was set directly (bypassing property)
        if '_tools' in self.__dict__:
            return self._tools
        # Check if we have a tools_service attribute (might be None or a service)
        if hasattr(self, 'tools_service') and self.tools_service:
            return self.tools_service.handler
        return None

    @tools.setter
    def tools(self, value):
        """Allow direct assignment for testing."""
        self._tools = value

    @property
    def skills(self):
        """Deprecated: the raw skills ObjectHandler.

        Retained for out-of-tree plugins and for test injection. In-tree callers
        use the named accessors; see :func:`_warn_handler_property`.
        """
        self._refuse_handler_property("skills")
        _warn_handler_property("skills")
        # For testing: check if attribute was set directly (bypassing property)
        if '_skills' in self.__dict__:
            return self._skills
        # Check if we have a skills_service attribute (might be None or a service)
        if hasattr(self, 'skills_service') and self.skills_service:
            return self.skills_service.handler
        return None

    @skills.setter
    def skills(self, value):
        """Allow direct assignment for testing."""
        self._skills = value

    @property
    def snippets(self):
        """Deprecated: the raw snippets ObjectHandler.

        Retained for out-of-tree plugins and for test injection. In-tree callers
        use the named accessors; see :func:`_warn_handler_property`.
        """
        self._refuse_handler_property("snippets")
        _warn_handler_property("snippets")
        # For testing: check if attribute was set directly (bypassing property)
        if '_snippets' in self.__dict__:
            return self._snippets
        # Check if we have a snippets_service attribute (might be None or a service)
        if hasattr(self, 'snippets_service') and self.snippets_service:
            return self.snippets_service.handler
        return None

    @snippets.setter
    def snippets(self, value):
        """Allow direct assignment for testing."""
        self._snippets = value

    def _refuse_handler_property(self, name: str) -> None:
        """Close the escape hatch beside the named methods.

        No in-tree plugin uses these properties, and their setters are how
        tests inject fakes — so refusing them under ACL closes the hole with no
        proxy layer, while ``disabled``-mode injection keeps working.
        """
        if self.acl_enabled:
            raise PluginAuthorizationError(
                _HANDLER_PROPERTY_REFUSED.format(name=name)
            )

    # ── Tools ──────────────────────────────────────────────────────────────

    def get_tool(self, uuid: str) -> Optional[Dict[str, Any]]:
        self._admit("tools", "get", uuid)
        if not self.tools_service:
            return None
        try:
            # Plugins consume the complete tool dict (module_name,
            # packaging_*, params, dependencies, …). Opt into ``full``
            # since the service default is ``narrow``.
            return self.tools_service.get(uuid, fields="full")
        except KeyError:
            return None

    def list_tools(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        self._admit("tools", "list")
        if not self.tools_service:
            return []
        # Plugins consume the complete tool dict (module_name,
        # packaging_*, params, dependencies, …). The service default is
        # ``narrow``, so opt back into ``full`` here.
        return self.tools_service.list_all(filter_criteria, fields="full")

    def get_tool_module(self, uuid_or_name: str) -> Optional[str]:
        """Return a tool's module source, or None if unavailable.

        Prefer this over reaching for ``store.tools.read_file(...)``: it needs
        no filename, and for MCP-packaged tools it returns the generated stub
        instead of failing (there is no stored module file for those).
        """
        self._admit("tools", "get", uuid_or_name)
        if not self.tools_service:
            return None
        try:
            return self.tools_service.get_module(uuid_or_name)
        except KeyError:
            return None
        except Exception as e:
            logger.error(f"Failed to read module for {uuid_or_name}: {e}")
            return None

    def update_tool_module(self, uuid_or_name: str, content: str) -> bool:
        """Replace a tool's module source. Returns False if it could not be written."""
        self._admit("tools", "update", uuid_or_name)
        if not self.tools_service:
            return False
        try:
            self.tools_service.set_module(uuid_or_name, content)
            return True
        except Exception as e:
            logger.error(f"Failed to write module for {uuid_or_name}: {e}")
            return False

    async def execute_tool(
        self,
        uuid_or_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        env_id: str = "",
    ) -> Dict[str, Any]:
        """Execute a tool through the store's own execution path.

        Resolves dependencies and runs the tool exactly as the REST
        ``/tools/{uuid}/execute`` endpoint does, so callers do not have to
        assemble execution inputs themselves.

        Raises:
            RuntimeError: If the tools service is unavailable, or the tool
                reported an execution error.
            KeyError: If the tool was not found.
        """
        self._admit("tools", "execute", uuid_or_name)
        if not self.tools_service:
            raise RuntimeError("Tools service not available")
        return await self.tools_service.execute(
            uuid_or_name, parameters or {}, env_id=env_id
        )

    def update_tool_tags(self, uuid: str, tags: List[str]) -> bool:
        self._admit("tools", "update", uuid)
        if not self.tools_service:
            return False
        try:
            tool = self.tools_service.get(uuid, fields="full")
        except KeyError:
            return False
        existing = set(tool.get("tags", []))
        tool["tags"] = list(existing.union(set(tags)))
        try:
            self.tools_service.handler.write_dict(uuid, tool)
            return True
        except Exception as e:
            logger.error(f"Failed to update tool tags for {uuid}: {e}")
            return False

    def create_tool(self, data: Dict[str, Any], module_content: bytes, module_filename: str) -> Dict[str, Any]:
        self._admit("tools", "create")
        if not self.tools_service:
            raise RuntimeError("Tools service not available")
        return self.tools_service.create(data, module_content, module_filename)

    def update_tool_metadata(self, uuid: str, metadata: Dict[str, Any]) -> bool:
        self._admit("tools", "update", uuid)
        if not self.tools_service:
            return False
        try:
            tool = self.tools_service.get(uuid, fields="full")
        except KeyError:
            return False
        if "extra" not in tool:
            tool["extra"] = {}
        tool["extra"].update(metadata)
        try:
            self.tools_service.handler.write_dict(uuid, tool)
            return True
        except Exception as e:
            logger.error(f"Failed to update tool metadata for {uuid}: {e}")
            return False

    def update_tool(self, uuid: str, tool_data: Dict[str, Any]) -> bool:
        """Write a complete tool object to the store."""
        self._admit("tools", "update", uuid)
        # Deliberately not via the public ``tools`` property: that accessor is
        # deprecated for plugin use, and StoreAPI must not trip its own warning.
        handler = self.tools_service.handler if self.tools_service else None
        if not handler:
            return False
        try:
            handler.write_dict(uuid, tool_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update tool {uuid}: {e}")
            return False

    def delete_tool(self, uuid_or_name: str) -> bool:
        self._admit("tools", "delete", uuid_or_name)
        if not self.tools_service:
            return False
        try:
            self.tools_service.delete(uuid_or_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete tool {uuid_or_name}: {e}")
            return False

    # ── Skills ─────────────────────────────────────────────────────────────

    def create_skill(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._admit("skills", "create")
        if not self.skills_service:
            raise RuntimeError("Skills service not available")
        return self.skills_service.create(data)

    def get_skill(self, uuid: str) -> Optional[Dict[str, Any]]:
        self._admit("skills", "get", uuid)
        if not self.skills_service:
            return None
        try:
            # Plugins consume the complete skill dict (populated tools /
            # snippets, extra, timestamps). Opt into ``full`` since the
            # service default is ``narrow``.
            return self.skills_service.get(uuid, fields="full")
        except KeyError:
            return None

    def list_skills(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        self._admit("skills", "list")
        if not self.skills_service:
            return []
        # Plugins consume the complete skill dict (populated tools /
        # snippets, extra, timestamps). Opt into ``full`` since the
        # service default is ``narrow``.
        return self.skills_service.list_all(filter_criteria, fields="full")

    def update_skill_tags(self, uuid: str, tags: List[str]) -> bool:
        self._admit("skills", "update", uuid)
        if not self.skills_service:
            return False
        try:
            skill = self.skills_service.get(uuid, fields="full")
        except KeyError:
            return False
        existing = set(skill.get("tags", []))
        skill["tags"] = list(existing.union(set(tags)))
        try:
            self.skills_service.handler.write_dict(uuid, skill)
            return True
        except Exception as e:
            logger.error(f"Failed to update skill tags for {uuid}: {e}")
            return False

    def update_skill_metadata(self, uuid: str, metadata: Dict[str, Any]) -> bool:
        self._admit("skills", "update", uuid)
        if not self.skills_service:
            return False
        try:
            skill = self.skills_service.get(uuid, fields="full")
        except KeyError:
            return False
        if "extra" not in skill or not isinstance(skill.get("extra"), dict):
            skill["extra"] = {}
        skill["extra"].update(metadata)
        try:
            self.skills_service.handler.write_dict(uuid, skill)
            return True
        except Exception as e:
            logger.error(f"Failed to update skill metadata for {uuid}: {e}")
            return False

    def update_skill(self, uuid: str, skill_data: Dict[str, Any]) -> bool:
        """Write a complete skill object to the store."""
        self._admit("skills", "update", uuid)
        # Deliberately not via the public ``skills`` property: that accessor is
        # deprecated for plugin use, and StoreAPI must not trip its own warning.
        handler = self.skills_service.handler if self.skills_service else None
        if not handler:
            return False
        try:
            handler.write_dict(uuid, skill_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update skill {uuid}: {e}")
            return False

    def delete_skill(self, uuid_or_name: str) -> bool:
        self._admit("skills", "delete", uuid_or_name)
        if not self.skills_service:
            return False
        try:
            self.skills_service.delete(uuid_or_name)
            return True
        except KeyError:
            return False
        except Exception as e:
            logger.error(f"Failed to delete skill {uuid_or_name}: {e}")
            return False

    # ── Snippets ───────────────────────────────────────────────────────────

    def get_snippet(self, uuid: str) -> Optional[Dict[str, Any]]:
        self._admit("snippets", "get", uuid)
        if not self.snippets_service:
            return None
        try:
            # Plugins consume the complete snippet dict (including
            # ``content``). Opt into ``full`` since the service default
            # is ``narrow``.
            return self.snippets_service.get(uuid, fields="full")
        except KeyError:
            return None

    def list_snippets(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        self._admit("snippets", "list")
        if not self.snippets_service:
            return []
        # Plugins consume the complete snippet dict (including
        # ``content``). Opt into ``full`` since the service default is
        # ``narrow``.
        return self.snippets_service.list_all(filter_criteria, fields="full")

    def create_snippet(self, snippet_data: Dict[str, Any]) -> Dict[str, Any]:
        self._admit("snippets", "create")
        if not self.snippets_service:
            raise RuntimeError("Snippets service not available")
        return self.snippets_service.create(snippet_data)

    def update_snippet_tags(self, uuid: str, tags: List[str]) -> bool:
        self._admit("snippets", "update", uuid)
        if not self.snippets_service:
            return False
        try:
            snippet = self.snippets_service.get(uuid, fields="full")
        except KeyError:
            return False
        existing = set(snippet.get("tags", []))
        snippet["tags"] = list(existing.union(set(tags)))
        try:
            self.snippets_service.handler.write_dict(uuid, snippet)
            return True
        except Exception as e:
            logger.error(f"Failed to update snippet tags for {uuid}: {e}")
            return False

    def update_snippet(self, uuid: str, snippet_data: Dict[str, Any]) -> bool:
        """Write a complete snippet object to the store."""
        self._admit("snippets", "update", uuid)
        # Deliberately not via the public ``snippets`` property: that accessor is
        # deprecated for plugin use, and StoreAPI must not trip its own warning.
        handler = self.snippets_service.handler if self.snippets_service else None
        if not handler:
            return False
        try:
            handler.write_dict(uuid, snippet_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update snippet {uuid}: {e}")
            return False

    # ── vMCP ───────────────────────────────────────────────────────────────

    def create_vmcp(self, data: Dict[str, Any], env_id: str = "") -> Dict[str, Any]:
        self._admit("vmcp_servers", "create")
        if not self.vmcp_service:
            raise RuntimeError("vMCP service not available")
        return self.vmcp_service.create(data, env_id=env_id)

    def get_vmcp(self, uuid_or_name: str) -> Optional[Dict[str, Any]]:
        self._admit("vmcp_servers", "get", uuid_or_name)
        if not self.vmcp_service:
            return None
        try:
            return self.vmcp_service.get(uuid_or_name, fields="full")
        except KeyError:
            return None

    def list_vmcps(self) -> List[Dict[str, Any]]:
        self._admit("vmcp_servers", "list")
        if not self.vmcp_service:
            return []
        # ``VmcpService.list_all()`` returns a bare list now (see Phase 3).
        result = self.vmcp_service.list_all()
        if isinstance(result, list):
            return result
        # Envelope shape when the caller paginates. Not expected here (we
        # pass no ``limit`` / ``offset``) but tolerate it defensively.
        if isinstance(result, dict) and "items" in result:
            return list(result["items"])
        return []

    def start_vmcp(self, uuid_or_name: str, env_id: str = "") -> bool:
        self._admit("vmcp_servers", "execute", uuid_or_name)
        if not self.vmcp_service:
            return False
        try:
            uuid = self.vmcp_service._resolve_uuid(uuid_or_name)
            d = self.vmcp_service.handler.read_dict(uuid)
            tool_uuids, snippet_uuids = self.vmcp_service._resolve_skill_uuids(
                d.get("skill_uuid")
            )
            self.vmcp_service.server_manager.add_server(
                name=d.get("name", ""),
                uuid=d.get("uuid", ""),
                description=d.get("description", ""),
                port=d.get("port"),
                tools=tool_uuids,
                snippets=snippet_uuids,
                env_id=env_id,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to start vMCP {uuid_or_name}: {e}")
            return False

    def delete_vmcp(self, uuid_or_name: str) -> bool:
        self._admit("vmcp_servers", "delete", uuid_or_name)
        if not self.vmcp_service:
            return False
        try:
            self.vmcp_service.delete(uuid_or_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete vMCP {uuid_or_name}: {e}")
            return False

    def _matches_filter(self, item: Dict[str, Any], filter_criteria: Dict) -> bool:
        return all(item.get(k) == v for k, v in filter_criteria.items())

# Made with Bob
