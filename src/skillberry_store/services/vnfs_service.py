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
    """Build a SimpleNamespace with attributes needed by VirtualNfsServerManager.add_server.
    
    Args:
        data: Dictionary containing vNFS server configuration.
        
    Returns:
        SimpleNamespace: Object with name, uuid, port, skill_uuid, description, and protocol attributes.
    """
    return SimpleNamespace(
        name=data.get("name"),
        uuid=data.get("uuid"),
        port=data.get("port"),
        skill_uuid=data.get("skill_uuid"),
        description=data.get("description") or "",
        protocol=data.get("protocol", "webdav"),
    )


class VnfsService:
    """Service layer for virtual NFS server CRUD operations.
    
    Provides business logic for managing virtual NFS servers, which expose
    snippets through network file system interfaces on specified ports.
    
    Attributes:
        handler: ObjectHandler for vNFS server persistence operations.
        server_manager: VirtualNfsServerManager for runtime server management.
        descriptions: Optional Description instance for semantic search indexing.
    """
    
    def __init__(
        self,
        handler: ObjectHandler,
        server_manager: VirtualNfsServerManager,
        descriptions: Optional[Description] = None,
    ):
        """Initialize the VnfsService.
        
        Args:
            handler: ObjectHandler instance for vNFS server operations.
            server_manager: VirtualNfsServerManager for managing runtime servers.
            descriptions: Optional Description instance for managing vNFS descriptions.
        """
        self.handler = handler
        self.server_manager = server_manager
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        """Resolve a vNFS server identifier to its UUID.
        
        Args:
            uuid_or_name: vNFS server UUID or name to resolve.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            KeyError: If vNFS server not found.
        """
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"vNFS server '{uuid_or_name}' not found")
            raise

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new virtual NFS server and start it.
        
        Creates a vNFS server entry, starts the runtime server process, and updates
        caches and indexes.
        
        Args:
            data: vNFS server metadata dictionary (name, skill_uuid, port, protocol, etc.).
            
        Returns:
            Dict[str, Any]: The created vNFS server data with UUID, timestamps, and assigned port.
            
        Raises:
            ValueError: If vNFS server with the same UUID already exists.
        """
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
        """Safely read a vNFS server dictionary with error handling.
        
        Args:
            uuid: vNFS server UUID to read.
            label: Human-readable label for error messages.
            
        Returns:
            Dict[str, Any]: vNFS server metadata dictionary.
            
        Raises:
            KeyError: If vNFS server not found.
        """
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"vNFS server '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        """Get vNFS server metadata by UUID or name with runtime status.
        
        Args:
            uuid_or_name: vNFS server UUID or name.
            
        Returns:
            Dict[str, Any]: vNFS server metadata with 'running' and 'export_path' fields.
            
        Raises:
            KeyError: If vNFS server not found.
        """
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
        """List all vNFS servers with runtime status.
        
        Returns:
            Dict[str, Any]: Dictionary with 'virtual_nfs_servers' key containing server info
                           indexed by UUID, including runtime status and export paths.
        """
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
        """Update an existing vNFS server's metadata and restart it.
        
        Stops the old runtime server, updates metadata, starts a new runtime server
        with updated configuration, and updates caches and indexes.
        
        Args:
            uuid_or_name: vNFS server UUID or name to update.
            data: Dictionary of fields to update.
            
        Returns:
            Dict[str, Any]: The updated vNFS server metadata with new port.
            
        Raises:
            KeyError: If vNFS server not found.
        """
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
        server = self.server_manager.add_server(_to_ns(data))
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
        logger.info(f"vNFS server '{new_name}' updated on port {server.port}")
        return data

    def delete(self, uuid_or_name: str) -> None:
        """Delete a vNFS server and stop its runtime process.
        
        Stops the runtime server, removes metadata, cache entries, and description indexes.
        
        Args:
            uuid_or_name: vNFS server UUID or name to delete.
            
        Raises:
            KeyError: If vNFS server not found.
        """
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
