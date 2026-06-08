"""Business logic for tool CRUD and execution operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.modules.file_executor import detect_tool_dependencies
from skillberry_store.utils.utils import generate_or_validate_uuid
from skillberry_store.tools.configure import is_auto_detect_dependencies_enabled

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description

logger = logging.getLogger(__name__)


class ToolsService:
    def __init__(
        self, handler: ObjectHandler, descriptions: Optional[Description] = None
    ):
        self.handler = handler
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Tool '{uuid_or_name}' not found")
            raise

    def find_dependencies(self, dependencies: List[str], tool_uuid: str) -> Set[str]:
        """Recursively resolve all transitive dependency UUIDs."""
        found: Set[str] = set()
        if not dependencies:
            return found
        for dep_uuid in dependencies:
            if dep_uuid in found:
                continue
            found.add(dep_uuid)
            dep_dict = self.handler.read_dict(dep_uuid)
            nested = dep_dict.get("dependencies", [])
            if nested:
                found.update(self.find_dependencies(nested, dep_uuid))
        return found

    def create(
        self, data: Dict[str, Any], module_content: bytes, module_filename: str
    ) -> Dict[str, Any]:
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"Tool with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(
                data["uuid"], data["name"]
            )
        self.handler.write_file(data["uuid"], module_filename, module_content)
        data["module_name"] = module_filename
        if not data.get("dependencies") and is_auto_detect_dependencies_enabled():
            try:
                content_str = (
                    module_content.decode("utf-8")
                    if isinstance(module_content, bytes)
                    else module_content
                )
                available = self.handler.get_existing_names()
                detected_names = detect_tool_dependencies(
                    content_str, data["name"], available
                )
                if detected_names:
                    data["dependencies"] = [
                        self.handler.name_to_uuid(n) for n in detected_names
                    ]
            except Exception as e:
                logger.warning(f"Failed to auto-detect dependencies: {e}")
        self.handler.write_dict(data["uuid"], data)
        self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"Tool '{data.get('name')}' created with UUID {data['uuid']}")
        return data

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Tool '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        return self._safe_read(uuid, uuid_or_name)

    def get_module(self, uuid_or_name: str) -> str:
        uuid = self._resolve_uuid(uuid_or_name)
        tool = self.handler.read_dict(uuid)
        module_name = tool.get("module_name")
        if not module_name:
            raise KeyError(f"Tool '{uuid_or_name}' has no module file")
        content = self.handler.read_file(uuid, module_name, raw_content=True)
        if not isinstance(content, str):
            raise RuntimeError(f"Invalid module content type for tool '{uuid_or_name}'")
        return content

    def list_all(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        items = self.handler.list_all_dicts()
        if filters:
            items = [i for i in items if all(i.get(k) == v for k, v in filters.items())]
        items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return items

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        existing = self.handler.read_dict(uuid)
        old_name = existing.get("name")
        old_parent = existing.get("parent")
        new_name = data.get("name") or old_name
        if new_name:
            data["parent"] = self.handler.get_cache_parent_for_head(uuid, new_name)
        merged = {**existing, **data}
        merged["uuid"] = existing.get("uuid", uuid)
        merged["created_at"] = existing.get("created_at")
        merged["modified_at"] = datetime.now(timezone.utc).isoformat()
        self.handler.write_dict(uuid, merged)
        if new_name:
            self.handler.update_cache(
                uuid, new_name=new_name, old_name=old_name, old_parent=old_parent
            )
        if self.descriptions and data.get("description"):
            old_desc = existing.get("description")
            if old_desc != data["description"]:
                try:
                    self.descriptions.delete_description(uuid)
                except Exception:
                    pass
                self.descriptions.write_description(uuid, data["description"])
        logger.info(f"Tool '{uuid_or_name}' updated")
        return merged

    def delete(self, uuid_or_name: str) -> None:
        uuid = self._resolve_uuid(uuid_or_name)
        try:
            d = self.handler.read_dict(uuid)
            name, parent = d.get("name"), d.get("parent")
        except Exception:
            name, parent = None, None
        if uuid and name:
            self.handler.update_cache(
                uuid, new_name=None, old_name=name, old_parent=parent
            )
        self.handler.delete_object(uuid)
        if self.descriptions:
            try:
                self.descriptions.delete_description(uuid)
            except Exception as e:
                logger.warning(f"Could not delete tool description for {uuid}: {e}")
        logger.info(f"Tool '{uuid_or_name}' deleted")
