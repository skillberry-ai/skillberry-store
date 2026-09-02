"""Store API for plugin access to content.

Thin proxy that delegates to service layer. Provides a stable interface
for plugins without exposing internal implementation details.

One instance is constructed per process and handed to the plugin loader,
which gives each plugin its own **per-slug view** via :meth:`StoreAPI.for_plugin`.
The view shares the services but knows which plugin is calling — without that,
an outcome cannot be attributed to a plugin, an autonomous operation cannot
resolve whose owner tenant applies, and per-plugin authorization has nothing
to key on (plugin-identity §2.4).
"""

import copy
from typing import Any, Dict, List, Optional
import logging
import warnings

logger = logging.getLogger(__name__)

_HANDLER_PROPERTY_DEPRECATION = (
    "StoreAPI.{name} returns the raw ObjectHandler and is deprecated for plugin "
    "use: it exposes the whole persistence layer, not a supported interface. Use "
    "the named accessors instead — get_tool_module()/update_tool_module() for "
    "module source, and update_tool()/update_skill()/update_snippet() to write a "
    "complete object."
)


def _warn_handler_property(name: str) -> None:
    warnings.warn(
        _HANDLER_PROPERTY_DEPRECATION.format(name=name),
        DeprecationWarning,
        stacklevel=3,
    )


class StoreAPI:
    """Plugin interface — delegates to service layer."""

    def __init__(self, services: Dict[str, Any]):
        self.tools_service = services.get("tools")
        self.skills_service = services.get("skills")
        self.snippets_service = services.get("snippets")
        self.vnfs_service = services.get("vnfs")
        self.vmcp_service = services.get("vmcp")
        # Which plugin this view belongs to. ``None`` on the shared instance
        # the server constructs; set on each view handed to a plugin.
        self._slug: Optional[str] = None

    @property
    def slug(self) -> Optional[str]:
        """The plugin this view was created for, or ``None`` if it is shared."""
        return self._slug

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

    # ── Tools ──────────────────────────────────────────────────────────────

    def get_tool(self, uuid: str) -> Optional[Dict[str, Any]]:
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
        if not self.tools_service:
            raise RuntimeError("Tools service not available")
        return await self.tools_service.execute(
            uuid_or_name, parameters or {}, env_id=env_id
        )

    def update_tool_tags(self, uuid: str, tags: List[str]) -> bool:
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
        if not self.tools_service:
            raise RuntimeError("Tools service not available")
        return self.tools_service.create(data, module_content, module_filename)

    def update_tool_metadata(self, uuid: str, metadata: Dict[str, Any]) -> bool:
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
        if not self.skills_service:
            raise RuntimeError("Skills service not available")
        return self.skills_service.create(data)

    def get_skill(self, uuid: str) -> Optional[Dict[str, Any]]:
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
        if not self.skills_service:
            return []
        # Plugins consume the complete skill dict (populated tools /
        # snippets, extra, timestamps). Opt into ``full`` since the
        # service default is ``narrow``.
        return self.skills_service.list_all(filter_criteria, fields="full")

    def update_skill_tags(self, uuid: str, tags: List[str]) -> bool:
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
        if not self.snippets_service:
            return []
        # Plugins consume the complete snippet dict (including
        # ``content``). Opt into ``full`` since the service default is
        # ``narrow``.
        return self.snippets_service.list_all(filter_criteria, fields="full")

    def create_snippet(self, snippet_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.snippets_service:
            raise RuntimeError("Snippets service not available")
        return self.snippets_service.create(snippet_data)

    def update_snippet_tags(self, uuid: str, tags: List[str]) -> bool:
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
        if not self.vmcp_service:
            raise RuntimeError("vMCP service not available")
        return self.vmcp_service.create(data, env_id=env_id)

    def get_vmcp(self, uuid_or_name: str) -> Optional[Dict[str, Any]]:
        if not self.vmcp_service:
            return None
        try:
            return self.vmcp_service.get(uuid_or_name, fields="full")
        except KeyError:
            return None

    def list_vmcps(self) -> List[Dict[str, Any]]:
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
