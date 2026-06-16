"""Store API for plugin access to content.

Thin proxy that delegates to service layer. Provides a stable interface
for plugins without exposing internal implementation details.
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class StoreAPI:
    """Plugin interface — delegates to service layer."""

    def __init__(self, services: Dict[str, Any]):
        self.tools_service = services.get("tools")
        self.skills_service = services.get("skills")
        self.snippets_service = services.get("snippets")
        self.vnfs_service = services.get("vnfs")
        self.vmcp_service = services.get("vmcp")

    @property
    def tools(self):
        """Expose tools handler for testing/plugin access."""
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
        """Expose skills handler for testing/plugin access."""
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
        """Expose snippets handler for testing/plugin access."""
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
            return self.tools_service.get(uuid)
        except KeyError:
            return None

    def list_tools(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        if not self.tools_service:
            return []
        return self.tools_service.list_all(filter_criteria)

    def update_tool_tags(self, uuid: str, tags: List[str]) -> bool:
        if not self.tools_service:
            return False
        try:
            tool = self.tools_service.get(uuid)
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
            tool = self.tools_service.get(uuid)
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
        handler = self.tools
        if not handler:
            return False
        try:
            handler.write_dict(uuid, tool_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update tool {uuid}: {e}")
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
            return self.skills_service.get(uuid)
        except KeyError:
            return None

    def list_skills(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        if not self.skills_service:
            return []
        return self.skills_service.list_all(filter_criteria)

    def update_skill_tags(self, uuid: str, tags: List[str]) -> bool:
        if not self.skills_service:
            return False
        try:
            skill = self.skills_service.get(uuid)
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
            skill = self.skills_service.get(uuid)
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
        handler = self.skills
        if not handler:
            return False
        try:
            handler.write_dict(uuid, skill_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update skill {uuid}: {e}")
            return False

    # ── Snippets ───────────────────────────────────────────────────────────

    def get_snippet(self, uuid: str) -> Optional[Dict[str, Any]]:
        if not self.snippets_service:
            return None
        try:
            return self.snippets_service.get(uuid)
        except KeyError:
            return None

    def list_snippets(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        if not self.snippets_service:
            return []
        return self.snippets_service.list_all(filter_criteria)

    def create_snippet(self, snippet_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.snippets_service:
            raise RuntimeError("Snippets service not available")
        return self.snippets_service.create(snippet_data)

    def update_snippet_tags(self, uuid: str, tags: List[str]) -> bool:
        if not self.snippets_service:
            return False
        try:
            snippet = self.snippets_service.get(uuid)
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
        handler = self.snippets
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
            return self.vmcp_service.get(uuid_or_name)
        except KeyError:
            return None

    def list_vmcps(self) -> List[Dict[str, Any]]:
        if not self.vmcp_service:
            return []
        result = self.vmcp_service.list_all()
        return list(result.get("virtual_mcp_servers", {}).values())

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
