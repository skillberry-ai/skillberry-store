"""Business logic for virtual MCP server CRUD operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.utils.utils import generate_or_validate_uuid

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description
    from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager

logger = logging.getLogger(__name__)


class VmcpService:
    def __init__(
        self,
        handler: ObjectHandler,
        server_manager: VirtualMcpServerManager,
        skills_handler: ObjectHandler,
        descriptions: Optional[Description] = None,
    ):
        self.handler = handler
        self.server_manager = server_manager
        self.skills_handler = skills_handler
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"VMCP server '{uuid_or_name}' not found")
            raise

    def _resolve_skill_uuids(self, skill_uuid: Optional[str]):
        tool_uuids: List[str] = []
        snippet_uuids: List[str] = []
        if not skill_uuid:
            return tool_uuids, snippet_uuids
        try:
            skill = self.skills_handler.read_dict(skill_uuid)
            tool_uuids = skill.get("tool_uuids", [])
            snippet_uuids = skill.get("snippet_uuids", [])
        except Exception as e:
            logger.warning(f"Error loading skill {skill_uuid}: {e}")
        return tool_uuids, snippet_uuids

    def create(self, data: Dict[str, Any], env_id: str = "") -> Dict[str, Any]:
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"VMCP server with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(
                data["uuid"], data["name"]
            )
        tool_uuids, snippet_uuids = self._resolve_skill_uuids(data.get("skill_uuid"))
        server = self.server_manager.add_server(
            name=data.get("name") or "",
            uuid=data["uuid"],
            description=data.get("description") or "",
            port=data.get("port"),
            tools=tool_uuids,
            snippets=snippet_uuids,
            env_id=env_id,
        )
        data["port"] = server.port
        self.handler.write_dict(data["uuid"], data)
        if data.get("name"):
            self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"VMCP server '{data.get('name')}' created on port {server.port}")
        return data

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"VMCP server '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        d = self._safe_read(uuid, uuid_or_name)
        try:
            runtime_details = self.server_manager.get_server_details(
                d.get("name", ""), d.get("uuid", "")
            )
            d["runtime"] = runtime_details
            d["running"] = True
        except Exception:
            d["running"] = False
            d["runtime"] = None
        return d

    def list_all(self) -> Dict[str, Any]:
        items = self.handler.list_all_dicts()
        from skillberry_store.fast_api.search_filters import exclude_simulation
        items = exclude_simulation(items)
        servers = []
        for item in items:
            try:
                runtime = None
                try:
                    runtime = self.server_manager.get_server(
                        item.get("name", ""), item.get("uuid", "")
                    )
                except Exception:
                    pass
                info = {
                    "uuid": item.get("uuid"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "version": item.get("version"),
                    "state": item.get("state"),
                    "tags": item.get("tags", []),
                    "port": item.get("port"),
                    "skill_uuid": item.get("skill_uuid"),
                    "modified_at": item.get("modified_at", ""),
                    "running": runtime is not None,
                    "runtime": (
                        {
                            "name": runtime.name,
                            "description": runtime.description,
                            "port": runtime.port,
                            "tools": runtime.tool_uuids,
                        }
                        if runtime
                        else None
                    ),
                }
                servers.append(info)
            except Exception as e:
                logger.warning(f"Error loading vmcp server '{item.get('name')}': {e}")
        servers.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return {"virtual_mcp_servers": {s["uuid"]: s for s in servers}}

    def update(
        self, uuid_or_name: str, data: Dict[str, Any], env_id: str = ""
    ) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        existing = self.handler.read_dict(uuid)
        old_name = existing.get("name")
        old_parent = existing.get("parent")
        server_uuid = existing.get("uuid")
        data["modified_at"] = datetime.now(timezone.utc).isoformat()
        if not data.get("uuid"):
            data["uuid"] = server_uuid
        new_name = data.get("name")
        if new_name:
            data["parent"] = self.handler.get_cache_parent_for_head(
                data["uuid"] or "", new_name
            )
        try:
            self.server_manager.remove_server(old_name or "", server_uuid or "")
        except Exception as e:
            logger.warning(f"Could not stop old runtime server: {e}")
        tool_uuids, snippet_uuids = self._resolve_skill_uuids(data.get("skill_uuid"))
        server = self.server_manager.add_server(
            name=new_name or "",
            uuid=data["uuid"] or "",
            description=data.get("description") or "",
            port=data.get("port"),
            tools=tool_uuids,
            snippets=snippet_uuids,
            env_id=env_id,
        )
        data["port"] = server.port
        self.handler.write_dict(data["uuid"] or "", data)
        if new_name and old_name:
            self.handler.update_cache(
                data["uuid"] or "",
                new_name=new_name,
                old_name=old_name,
                old_parent=old_parent,
            )
        if self.descriptions and data.get("description") and data.get("uuid"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"VMCP server '{new_name}' updated on port {server.port}")
        return data

    def delete(self, uuid_or_name: str) -> None:
        uuid = self._resolve_uuid(uuid_or_name)
        d = self.handler.read_dict(uuid)
        name = d.get("name")
        parent = d.get("parent")
        try:
            self.server_manager.remove_server(name or "", uuid or "")
        except Exception as e:
            logger.warning(f"Could not stop runtime server: {e}")
        if name and uuid:
            self.handler.update_cache(
                uuid, new_name=None, old_name=name, old_parent=parent
            )
        self.handler.delete_object(uuid)
        if self.descriptions:
            try:
                self.descriptions.delete_description(uuid)
            except Exception as e:
                logger.warning(f"Could not delete vmcp description for {uuid}: {e}")
        logger.info(f"VMCP server '{uuid_or_name}' deleted")
