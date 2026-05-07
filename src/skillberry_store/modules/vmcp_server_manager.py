import json
import logging
import os
import threading

from typing import Any, Dict, Optional

from skillberry_store.modules.vmcp_server import VirtualMcpServer
from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.lookup_cache import build_lookup_cache
from skillberry_store.tools.configure import (
    get_skills_directory,
    get_snippets_directory,
    get_tools_directory,
    get_vmcp_directory,
)

logger = logging.getLogger(__name__)


class VirtualMcpServerManager:
    """Manages virtual MCP servers for the Skillberry Store service.

    This class provides functionality to create, manage, and persist virtual MCP servers
    that can be dynamically created from tool search results or manually configured.

    Loads servers from VmcpSchema JSON files in the vmcp directory on startup.
    """

    def __init__(self, sts_url: str = "http://localhost:8000", app=None):
        """Initialize the virtual MCP server manager.

        Args:
            sts_url: The STS server URL to use for tool execution.
            app: The SBS FastAPI app instance for direct method calls.

        Loads existing virtual MCP servers from VmcpSchema JSON files.
        """
        self.servers: Dict[str, VirtualMcpServer] = {}
        self.sts_url = sts_url
        self.app = app
        self._lock = threading.RLock()

        # Use the same directory as vmcp_api for consistency
        self.vmcp_directory = get_vmcp_directory()
        self.vmcp_handler = FileHandler(self.vmcp_directory)

        logger.info(f"Loading vmcp_servers from {self.vmcp_directory}")
        self.load_servers()

    def add_server(
        self,
        name: str,
        description: str,
        port: Optional[int],
        tools: list,
        snippets: list = None,
        env_id: str = "",
    ) -> VirtualMcpServer:
        """Add a new virtual MCP server.

        Args:
            name: The name of the virtual MCP server.
            description: A description of the virtual MCP server.
            port: The port number for the server (optional, auto-assigned if None).
            tools: List of tool names to include in the server.
            snippets: List of snippet names to include as prompts in the server (optional).
            env_id: A string representing the environment id to be used for this server (Optional).

        Returns:
            VirtualMcpServer: The created virtual MCP server instance.

        Raises:
            Exception: If error occurred
        """
        logger.info(f"Adding vmcp_server: {name}")
        with self._lock:
            server = VirtualMcpServer(
                name=name,
                description=description,
                port=port,
                tools=tools,
                snippets=snippets or [],
                sts_url=self.sts_url,
                app=self.app,
                env_id=env_id,
            )
            self.servers[server.name] = server

            logger.info(
                f"Added and started new vmcp_server: {name} on port {server.port} with {len(tools)} tools and {len(snippets or [])} prompts"
            )
            return server

    def remove_server(self, name: str):
        """Remove a virtual MCP server.

        Args:
            name: The name of the virtual MCP server to remove.
        """
        with self._lock:
            if name in self.servers:
                logger.info(f"Removing vmcp_server: {name}")
                server = self.servers[name]
                # Stop the server before removing it
                try:
                    server.stop()
                    logger.info(f"Stopped vmcp_server: {name}")
                except Exception as e:
                    logger.warning(f"Failed to stop vmcp_server {name}: {str(e)}")

                del self.servers[name]
            else:
                logger.debug(f"vmcp_server {name} not found")

    def list_servers(self):
        """List all virtual MCP server names.

        Returns:
            List[str]: A list of virtual MCP server names.
        """
        logger.debug("Listing vmcp_servers")
        with self._lock:
            return list(self.servers.keys())

    def get_server(self, name: str) -> Optional[VirtualMcpServer]:
        """Get a virtual MCP server by name.

        Args:
            name: The name of the virtual MCP server.

        Returns:
            VirtualMcpServer: The virtual MCP server instance, or None if not found.
        """
        logger.debug(f"Getting vmcp_server: {name}")
        with self._lock:
            return self.servers.get(name)

    def get_server_details(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a virtual MCP server.

        Args:
            name: The name of the virtual MCP server.

        Returns:
            Dict[str, Any]: A dictionary containing server details.

        Raises:
            ValueError: If the virtual MCP server is not found.
        """
        logger.debug(f"Getting details of vmcp_server: {name}")
        with self._lock:
            server = self.get_server(name)
            if server:
                return {
                    "name": server.name,
                    "description": server.description,
                    "port": server.port,
                    "tools": server.tools,
                    "snippets": server.snippets,
                }
            else:
                raise ValueError(f"vmcp_server '{name}' not found")

    def load_servers(self):
        """Load virtual MCP servers from VmcpSchema JSON files.

        Reads all JSON files from the vmcp directory and starts runtime servers for each.
        This ensures that servers persist across restarts.
        """
        try:
            vmcp_files = self.vmcp_handler.list_files()
            for filename in vmcp_files:
                if filename.endswith(".json"):
                    try:
                        content = self.vmcp_handler.read_file(
                            filename, raw_content=True
                        )
                        if isinstance(content, str):
                            vmcp_data = json.loads(content)

                            # Extract the necessary fields to start the server
                            name = vmcp_data.get("name")
                            description = vmcp_data.get("description", "")
                            port = vmcp_data.get("port")
                            skill_uuid = vmcp_data.get("skill_uuid")

                            # Resolve tool names and snippet names from skill_uuid
                            tool_names = []
                            snippet_names = []
                            if skill_uuid:
                                logger.info(
                                    f"Resolving tools and snippets for skill_uuid: {skill_uuid} during server load"
                                )
                                try:
                                    skills_handler = FileHandler(get_skills_directory())
                                    tools_handler = FileHandler(get_tools_directory())
                                    snippets_handler = FileHandler(
                                        get_snippets_directory()
                                    )
                                    lookup_cache = build_lookup_cache(
                                        skills_handler=skills_handler,
                                        tools_handler=tools_handler,
                                        snippets_handler=snippets_handler,
                                    )

                                    skill_dict = lookup_cache.skills_by_uuid.get(
                                        skill_uuid
                                    )
                                    skill_tool_uuids = (
                                        skill_dict.get("tool_uuids", [])
                                        if skill_dict
                                        else []
                                    )
                                    skill_snippet_uuids = (
                                        skill_dict.get("snippet_uuids", [])
                                        if skill_dict
                                        else []
                                    )

                                    if skill_dict:
                                        logger.info(
                                            f"Found skill '{skill_dict.get('name')}' with {len(skill_tool_uuids)} tool UUIDs and {len(skill_snippet_uuids)} snippet UUIDs"
                                        )

                                    for tool_uuid in skill_tool_uuids:
                                        tool_dict = lookup_cache.tools_by_uuid.get(
                                            tool_uuid
                                        )
                                        tool_name = (
                                            tool_dict.get("name") if tool_dict else None
                                        )
                                        if tool_name:
                                            tool_names.append(tool_name)
                                            logger.info(
                                                f"Resolved tool UUID {tool_uuid} to name '{tool_name}'"
                                            )

                                    for snippet_uuid in skill_snippet_uuids:
                                        snippet_dict = (
                                            lookup_cache.snippets_by_uuid.get(
                                                snippet_uuid
                                            )
                                        )
                                        snippet_name = (
                                            snippet_dict.get("name")
                                            if snippet_dict
                                            else None
                                        )
                                        if snippet_name:
                                            snippet_names.append(snippet_name)
                                            logger.info(
                                                f"Resolved snippet UUID {snippet_uuid} to name '{snippet_name}'"
                                            )

                                    logger.info(
                                        f"Resolved {len(tool_names)} tool names and {len(snippet_names)} snippet names for server '{name}'"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Error resolving tools and snippets for skill_uuid {skill_uuid}: {e}"
                                    )

                            # Start the runtime server
                            if name:
                                server = VirtualMcpServer(
                                    name=name,
                                    description=description,
                                    port=port,
                                    tools=tool_names,
                                    snippets=snippet_names,
                                    sts_url=self.sts_url,
                                    app=self.app,
                                    env_id="",
                                )
                                self.servers[server.name] = server
                                logger.info(
                                    f"Loaded and started vmcp_server: {server.name} on port {server.port} with {len(tool_names)} tools and {len(snippet_names)} prompts"
                                )
                    except Exception as e:
                        logger.error(
                            f"Failed to load vmcp_server from {filename}: {str(e)}"
                        )

            logger.info(
                f"Loaded {len(self.servers)} vmcp servers from {self.vmcp_directory}"
            )
        except Exception as e:
            logger.error(f"Failed to load vmcp_servers from directory. Error: {str(e)}")

    def cleanup_all_servers(self):
        """Stop and cleanup all running virtual MCP servers.

        This method should be called during application shutdown to ensure
        all VMCP servers are properly stopped.
        """
        logger.info("Cleaning up all VMCP servers...")
        with self._lock:
            server_names = list(self.servers.keys())
            for name in server_names:
                try:
                    logger.info(f"Stopping VMCP server: {name}")
                    server = self.servers[name]
                    server.stop()
                except Exception as e:
                    logger.warning(f"Error stopping VMCP server {name}: {e}")

            self.servers.clear()
            logger.info("All VMCP servers cleaned up")
