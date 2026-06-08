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

    # ── Skills ─────────────────────────────────────────────────────────────

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

    def _matches_filter(self, item: Dict[str, Any], filter_criteria: Dict) -> bool:
        return all(item.get(k) == v for k, v in filter_criteria.items())

# Made with Bob
