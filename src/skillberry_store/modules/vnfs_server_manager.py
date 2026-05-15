"""Lifecycle manager for virtual NFS servers."""

import json
import logging
import threading
from typing import Any, Dict, List, Optional

from skillberry_store.modules.vnfs_server import VirtualNfsServer
from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.lookup_cache import build_lookup_cache
from skillberry_store.tools.configure import (
    get_files_directory_path,
    get_skills_directory,
    get_snippets_directory,
    get_tools_directory,
    get_vnfs_directory,
)

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
        self.vnfs_handler = FileHandler(self.vnfs_directory)

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
        logger.info(f"Adding vnfs_server: {schema.name}")
        skill, tools, snippets, tool_modules = self._resolve_skill(schema.skill_uuid)

        with self._lock:
            server = VirtualNfsServer(
                name=schema.name,
                skill_uuid=schema.skill_uuid,
                port=schema.port,
                protocol=getattr(schema, "protocol", "webdav"),
                description=schema.description or "",
                uuid=schema.uuid,
            )
            server.start(skill, tools, snippets, tool_modules)
            self.servers[server.name] = server

        logger.info(
            f"Added and started vnfs_server '{schema.name}' on port {server.port}"
        )
        return server

    def remove_server(self, name: str) -> None:
        with self._lock:
            if name in self.servers:
                logger.info(f"Removing vnfs_server: {name}")
                try:
                    self.servers[name].stop()
                except Exception as exc:
                    logger.warning(f"Failed to stop vnfs_server '{name}': {exc}")
                del self.servers[name]
            else:
                logger.debug(f"vnfs_server '{name}' not found")

    def get_server(self, name: str) -> Optional[VirtualNfsServer]:
        with self._lock:
            return self.servers.get(name)

    def list_servers(self) -> List[str]:
        with self._lock:
            return list(self.servers.keys())

    def get_server_details(self, name: str) -> Dict[str, Any]:
        with self._lock:
            server = self.servers.get(name)
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
            for filename in self.vnfs_handler.list_files():
                if not filename.endswith(".json"):
                    continue
                try:
                    content = self.vnfs_handler.read_file(filename, raw_content=True)
                    if not isinstance(content, str):
                        continue
                    data = json.loads(content)
                    name = data.get("name")
                    if not name:
                        continue

                    skill_uuid = data.get("skill_uuid")
                    skill, tools, snippets, tool_modules = self._resolve_skill(skill_uuid)

                    server = VirtualNfsServer(
                        name=name,
                        skill_uuid=skill_uuid,
                        port=data.get("port"),
                        protocol=data.get("protocol", "webdav"),
                        description=data.get("description", ""),
                        uuid=data.get("uuid"),
                    )
                    server.start(skill, tools, snippets, tool_modules)
                    self.servers[server.name] = server
                    logger.info(
                        f"Loaded vnfs_server '{name}' on port {server.port}"
                    )
                except Exception as exc:
                    logger.error(f"Failed to load vnfs_server from '{filename}': {exc}")

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
        """Return (skill_dict, tools_list, snippets_list, tool_modules) for a skill UUID."""
        if not skill_uuid:
            return {}, [], [], {}

        try:
            skills_handler = FileHandler(get_skills_directory())
            tools_handler = FileHandler(get_tools_directory())
            snippets_handler = FileHandler(get_snippets_directory())
            files_handler = FileHandler(get_files_directory_path())
            cache = build_lookup_cache(
                skills_handler=skills_handler,
                tools_handler=tools_handler,
                snippets_handler=snippets_handler,
            )

            skill_dict = cache.skills_by_uuid.get(skill_uuid)
            if not skill_dict:
                logger.warning(f"No skill found for skill_uuid: {skill_uuid}")
                return {}, [], [], {}

            tools = [
                cache.tools_by_uuid[u]
                for u in skill_dict.get("tool_uuids", [])
                if u in cache.tools_by_uuid
            ]
            snippets = [
                cache.snippets_by_uuid[u]
                for u in skill_dict.get("snippet_uuids", [])
                if u in cache.snippets_by_uuid
            ]

            tool_modules = {}
            for tool in tools:
                tool_name = tool.get("name")
                lang = tool.get("programming_language", "python").lower()
                ext = ".sh" if lang in ("bash", "sh", "shell") else ".py"
                try:
                    content = files_handler.read_file(f"{tool_name}{ext}", raw_content=True)
                    if isinstance(content, str):
                        tool_modules[tool_name] = content
                except Exception as exc:
                    logger.warning(f"Could not read module for tool '{tool_name}': {exc}")

            return skill_dict, tools, snippets, tool_modules
        except Exception as exc:
            logger.error(f"Error resolving skill_uuid '{skill_uuid}': {exc}")
            return {}, [], [], {}
