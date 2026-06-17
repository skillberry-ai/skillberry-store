"""Business logic for virtual NFS server CRUD operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.utils.utils import generate_or_validate_uuid

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description
    from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager

logger = logging.getLogger(__name__)


def _to_ns(data: Dict[str, Any]) -> SimpleNamespace:
    """Build a SimpleNamespace with the attributes VirtualNfsServerManager.add_server needs."""
    return SimpleNamespace(
        name=data.get("name"),
        uuid=data.get("uuid"),
        port=data.get("port"),
        skill_uuid=data.get("skill_uuid"),
        description=data.get("description") or "",
        protocol=data.get("protocol", "webdav"),
    )


class VnfsService:
    def __init__(
        self,
        handler: ObjectHandler,
        server_manager: VirtualNfsServerManager,
        descriptions: Optional[Description] = None,
    ):
        self.handler = handler
        self.server_manager = server_manager
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"vNFS server '{uuid_or_name}' not found")
            raise

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"vNFS server with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(
                data["uuid"], data["name"]
            )
        server = self.server_manager.add_server(_to_ns(data))
        data["port"] = server.port
        self.handler.write_dict(data["uuid"], data)
        if data.get("name"):
            self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"vNFS server '{data.get('name')}' created on port {server.port}")
        return data

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"vNFS server '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        d = self._safe_read(uuid, uuid_or_name)
        try:
            runtime = self.server_manager.get_server(
                d.get("name", ""), d.get("uuid", "")
            )
            d["running"] = runtime is not None and runtime.running
            d["export_path"] = str(runtime.export_path) if runtime else None
        except Exception:
            d["running"] = False
            d["export_path"] = None
        return d

    def list_all(self) -> Dict[str, Any]:
        items = self.handler.list_all_dicts()
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
                    "protocol": item.get("protocol", "webdav"),
                    "modified_at": item.get("modified_at", ""),
                    "running": runtime is not None and runtime.running,
                    "export_path": str(runtime.export_path) if runtime else None,
                }
                servers.append(info)
            except Exception as e:
                logger.warning(f"Error loading vnfs server '{item.get('name')}': {e}")
        servers.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return {"virtual_nfs_servers": {s["uuid"]: s for s in servers}}

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        existing = self.handler.read_dict(uuid)
        old_name = existing.get("name")
        old_parent = existing.get("parent")
        server_uuid = existing.get("uuid")
        
        # Merge existing data with new data
        merged = {**existing, **data}
        merged["modified_at"] = datetime.now(timezone.utc).isoformat()
        merged["uuid"] = server_uuid
        
        new_name = merged.get("name")
        if new_name:
            merged["parent"] = self.handler.get_cache_parent_for_head(
                server_uuid or "", new_name
            )
        try:
            self.server_manager.remove_server(old_name or "", server_uuid or "")
        except Exception as e:
            logger.warning(f"Could not stop old runtime server: {e}")
        server = self.server_manager.add_server(_to_ns(merged))
        merged["port"] = server.port
        self.handler.write_dict(server_uuid or "", merged)
        if new_name and old_name:
            self.handler.update_cache(
                server_uuid or "",
                new_name=new_name,
                old_name=old_name,
                old_parent=old_parent,
            )
        if self.descriptions and merged.get("description") and server_uuid:
            self.descriptions.write_description(server_uuid, merged["description"])
        logger.info(f"vNFS server '{new_name}' updated on port {server.port}")
        return merged

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
                logger.warning(f"Could not delete vnfs description for {uuid}: {e}")
        logger.info(f"vNFS server '{uuid_or_name}' deleted")
