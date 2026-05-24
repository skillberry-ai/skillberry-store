"""Lifecycle manager for virtual NFS servers."""

import json
import logging
import threading
from typing import Any, Dict, List, Optional

from skillberry_store.modules.vnfs_server import VirtualNfsServer
from skillberry_store.modules.object_handler import get_object_handler
from skillberry_store.tools.configure import get_vnfs_directory
from skillberry_store.utils.utils import make_name_with_uuid

logger = logging.getLogger(__name__)


class VirtualNfsServerManager:
    """Manages virtual NFS servers for the Skillberry Store service.

    Loads persisted vNFS configurations from JSON files on startup and starts
    each server's filesystem backend.
    """

    def __init__(self, sts_url: str = "http://localhost:8000", app=None):
        self.servers: Dict[str, VirtualNfsServer] = {}
        self.sts_url = sts_url
        self.app = app
        self._lock = threading.RLock()

        self.vnfs_directory = get_vnfs_directory()
        self.vnfs_handler = get_object_handler("vnfs")

        logger.info(f"Loading vnfs_servers from {self.vnfs_directory}")
        self.load_servers()

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    def add_server(self, schema) -> VirtualNfsServer:
        """Create, start, and register a new vNFS server.

        Args:
            schema: VnfsSchema instance with configuration.

        Returns:
            The started VirtualNfsServer.
        """
        # Generate unique runtime server name using composite name
        runtime_server_name = make_name_with_uuid(schema.name, schema.uuid)
        logger.info(f"Adding vnfs_server: {runtime_server_name}")
        skill, tools, snippets, tool_modules = self._resolve_skill(schema.skill_uuid)

        with self._lock:
            server = VirtualNfsServer(
                name=runtime_server_name,
                skill_uuid=schema.skill_uuid,
                port=schema.port,
                protocol=getattr(schema, "protocol", "webdav"),
                description=schema.description or "",
                uuid=schema.uuid,
            )
            server.start(skill, tools, snippets, tool_modules)
            self.servers[runtime_server_name] = server

        logger.info(
            f"Added and started vnfs_server '{runtime_server_name}' on port {server.port}"
        )
        return server

    def remove_server(self, name: str, uuid: str) -> None:
        """Remove a virtual NFS server.

        Args:
            name: The human-readable name of the virtual NFS server.
            uuid: The UUID of the VNFS object.
        """
        runtime_server_name = make_name_with_uuid(name, uuid)
        
        with self._lock:
            if runtime_server_name in self.servers:
                logger.info(f"Removing vnfs_server: {runtime_server_name}")
                try:
                    self.servers[runtime_server_name].stop()
                except Exception as exc:
                    logger.warning(f"Failed to stop vnfs_server '{runtime_server_name}': {exc}")
                del self.servers[runtime_server_name]
            else:
                logger.debug(f"vnfs_server '{runtime_server_name}' not found")

    def get_server(self, name: str, uuid: str) -> Optional[VirtualNfsServer]:
        """Get a virtual NFS server by name and UUID.

        Args:
            name: The human-readable name of the virtual NFS server.
            uuid: The UUID of the VNFS object.

        Returns:
            VirtualNfsServer: The virtual NFS server instance, or None if not found.
        """
        runtime_server_name = make_name_with_uuid(name, uuid)
        logger.debug(f"Getting vnfs_server with composite name: {runtime_server_name}")
        
        with self._lock:
            return self.servers.get(runtime_server_name)

    def list_servers(self) -> List[str]:
        with self._lock:
            return list(self.servers.keys())

    def get_server_details(self, name: str, uuid: str) -> Dict[str, Any]:
        """Get detailed information about a virtual NFS server.

        Args:
            name: The human-readable name of the virtual NFS server.
            uuid: The UUID of the VNFS object.

        Returns:
            Dict[str, Any]: A dictionary containing server details.

        Raises:
            ValueError: If the virtual NFS server is not found.
        """
        runtime_server_name = make_name_with_uuid(name, uuid)
        logger.debug(f"Getting details of vnfs_server: {runtime_server_name}")
        
        with self._lock:
            server = self.get_server(name, uuid)
            if server is None:
                raise ValueError(f"vnfs_server '{name}' not found")
            return {
                "name": server.name,
                "description": server.description,
                "port": server.port,
                "protocol": server.protocol,
                "running": server.running,
                "export_path": str(server.export_path),
            }

    # ------------------------------------------------------------------
    # Startup / shutdown
    # ------------------------------------------------------------------

    def load_servers(self) -> None:
        """Read persisted JSON files and start a runtime server for each."""
        try:
            # Get all VNFS server resources
            vnfs_resources = self.vnfs_handler.list_all_dicts()
            
            for data in vnfs_resources:
                name = data.get("name")
                uuid = data.get("uuid")
                if not name or not uuid:
                    continue
                
                try:
                    skill_uuid = data.get("skill_uuid")
                    skill, tools, snippets, tool_modules = self._resolve_skill(
                        skill_uuid
                    )

                    # Use composite name for uniqueness
                    runtime_server_name = make_name_with_uuid(name, uuid)
                    server = VirtualNfsServer(
                        name=runtime_server_name,
                        skill_uuid=skill_uuid,
                        port=data.get("port"),
                        protocol=data.get("protocol", "webdav"),
                        description=data.get("description", ""),
                        uuid=uuid,
                    )
                    server.start(skill, tools, snippets, tool_modules)
                    self.servers[runtime_server_name] = server
                    logger.info(f"Loaded vnfs_server '{runtime_server_name}' on port {server.port}")
                except Exception as exc:
                    logger.error(f"Failed to load vnfs_server '{name}': {exc}")

            logger.info(
                f"Loaded {len(self.servers)} vnfs_servers from {self.vnfs_directory}"
            )
        except Exception as exc:
            logger.error(f"Failed to load vnfs_servers: {exc}")

    def cleanup_all_servers(self) -> None:
        """Stop and clean up all running vNFS servers (called on shutdown)."""
        logger.info("Cleaning up all vNFS servers...")
        with self._lock:
            for name in list(self.servers.keys()):
                try:
                    self.servers[name].stop()
                except Exception as exc:
                    logger.warning(f"Error stopping vNFS server '{name}': {exc}")
            self.servers.clear()
        logger.info("All vNFS servers cleaned up")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_skill(self, skill_uuid: Optional[str]):
        """Return (skill_dict, tools_list, snippets_list, tool_modules) for a skill UUID.
        
        Uses ObjectHandler for UUID-based object access, consistent with VMCP implementation.
        """
        if not skill_uuid:
            return {}, [], [], {}

        try:
            # Use ObjectHandler for UUID-based access
            skills_handler = get_object_handler("skill")
            tools_handler = get_object_handler("tool")
            snippets_handler = get_object_handler("snippet")

            # Read skill dict by UUID
            skill_dict = skills_handler.read_dict(skill_uuid)
            
            # Get tool and snippet UUIDs from skill
            tool_uuids = skill_dict.get("tool_uuids", [])
            snippet_uuids = skill_dict.get("snippet_uuids", [])
            
            # Get tools and snippets by UUID
            tools = tools_handler.read_dicts(tool_uuids) if tool_uuids else []
            snippets = snippets_handler.read_dicts(snippet_uuids) if snippet_uuids else []
            
            # Read tool modules from tool's UUID subdirectory
            tool_modules = {}
            for tool in tools:
                tool_uuid = tool.get("uuid")
                module_name = tool.get("module_name")
                tool_name = tool.get("name")
                
                if not tool_uuid or not module_name or not tool_name:
                    logger.warning(f"Tool missing required fields: uuid={tool_uuid}, module_name={module_name}, name={tool_name}")
                    continue
                
                try:
                    content = tools_handler.read_file(
                        tool_uuid, module_name, raw_content=True
                    )
                    if isinstance(content, str):
                        tool_modules[tool_name] = content
                    else:
                        logger.warning(f"Could not read module for tool '{tool_name}': content is not a string")
                except Exception as exc:
                    logger.warning(f"Could not read module for tool '{tool_name}': {exc}")

            logger.info(f"Resolved skill '{skill_dict.get('name')}' with {len(tools)} tools and {len(snippets)} snippets")
            return skill_dict, tools, snippets, tool_modules
            
        except Exception as exc:
            logger.error(f"Error resolving skill_uuid '{skill_uuid}': {exc}")
            return {}, [], [], {}
