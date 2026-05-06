import json
import logging
import os
import threading

from typing import Any, Dict, Optional

from skillberry_store.modules.vmcp_server import VirtualMcpServer
from skillberry_store.modules.resource_handler import ResourceHandler
from skillberry_store.tools.configure import get_vmcp_directory, get_skills_directory, get_tools_directory, get_snippets_directory

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
        self.vmcp_handler = ResourceHandler(self.vmcp_directory, "vmcp")
        
        # Initialize handlers for skills, tools, and snippets
        self.skills_handler = ResourceHandler(get_skills_directory(), "skill")
        self.tools_handler = ResourceHandler(get_tools_directory(), "tool")
        self.snippets_handler = ResourceHandler(get_snippets_directory(), "snippet")

        logger.info(f"Loading vmcp_servers from {self.vmcp_directory}")
        self.load_servers()
    
    @staticmethod
    def get_runtime_server_name(vmcp_name: str, vmcp_uuid: str) -> str:
        """Generate unique runtime server name from VMCP name and UUID.
        
        This ensures each VMCP object gets a unique runtime server, even if
        multiple VMCP objects share the same name.
        
        Args:
            vmcp_name: The human-readable VMCP name
            vmcp_uuid: The unique VMCP UUID
            
        Returns:
            Composite name: "{name}_{uuid}"
        """
        return f"{vmcp_name}_{vmcp_uuid}"

    def add_server(
        self,
        name: str,
        uuid: str,
        description: str,
        port: Optional[int],
        tools: list,
        snippets: list = None,
        env_id: str = "",
    ) -> VirtualMcpServer:
        """Add a new virtual MCP server.

        Args:
            name: The human-readable name of the virtual MCP server.
            uuid: The unique UUID of the VMCP object.
            description: A description of the virtual MCP server.
            port: The port number for the server (optional, auto-assigned if None).
            tools: List of tool UUIDs to include in the server.
            snippets: List of snippet UUIDs to include as prompts in the server (optional).
            env_id: A string representing the environment id to be used for this server (Optional).

        Returns:
            VirtualMcpServer: The created virtual MCP server instance.

        Raises:
            Exception: If error occurred
        """
        # Generate unique runtime server name
        runtime_server_name = self.get_runtime_server_name(name, uuid)
        logger.info(f"Adding vmcp_server: {runtime_server_name}")
        
        with self._lock:
            server = VirtualMcpServer(
                name=runtime_server_name,
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
                f"Added and started new vmcp_server: {runtime_server_name} on port {server.port} with {len(tools)} tool UUIDs and {len(snippets or [])} snippet UUIDs"
            )
            return server

    def remove_server(self, name: str, uuid: str):
        """Remove a virtual MCP server.

        Args:
            name: The human-readable name of the virtual MCP server.
            uuid: The UUID of the VMCP object.
        """
        runtime_server_name = self.get_runtime_server_name(name, uuid)
            
        with self._lock:
            if runtime_server_name in self.servers:
                logger.info(f"Removing vmcp_server: {runtime_server_name}")
                server = self.servers[runtime_server_name]
                # Stop the server before removing it
                try:
                    server.stop()
                    logger.info(f"Stopped vmcp_server: {runtime_server_name}")
                except Exception as e:
                    logger.warning(f"Failed to stop vmcp_server {runtime_server_name}: {str(e)}")

                del self.servers[runtime_server_name]
            else:
                logger.debug(f"vmcp_server {runtime_server_name} not found")

    def list_servers(self):
        """List all virtual MCP server names.

        Returns:
            List[str]: A list of virtual MCP server names.
        """
        logger.debug("Listing vmcp_servers")
        with self._lock:
            return list(self.servers.keys())

    def get_server(self, name: str, uuid: str) -> Optional[VirtualMcpServer]:
        """Get a virtual MCP server by name and UUID.

        Args:
            name: The human-readable name of the virtual MCP server.
            uuid: The UUID of the VMCP object.

        Returns:
            VirtualMcpServer: The virtual MCP server instance, or None if not found.
        """
        runtime_server_name = self.get_runtime_server_name(name, uuid)
        logger.debug(f"Getting vmcp_server with composite name: {runtime_server_name}")
        
        with self._lock:
            return self.servers.get(runtime_server_name)

    def get_server_details(self, name: str, uuid: str) -> Dict[str, Any]:
        """Get detailed information about a virtual MCP server.

        Args:
            name: The human-readable name of the virtual MCP server.
            uuid: The UUID of the VMCP object.

        Returns:
            Dict[str, Any]: A dictionary containing server details.

        Raises:
            ValueError: If the virtual MCP server is not found.
        """
        runtime_server_name = self.get_runtime_server_name(name, uuid)
        logger.debug(f"Getting details of vmcp_server: {runtime_server_name}")
        with self._lock:
            server = self.get_server(name, uuid)
            if server:
                return {
                    "name": server.name,
                    "description": server.description,
                    "port": server.port,
                    "tools": server.tool_uuids,
                    "snippets": server.snippet_uuids,
                }
            else:
                raise ValueError(f"vmcp_server '{name}' not found")

    def load_servers(self):
        """Load virtual MCP servers from VmcpSchema JSON files.

        Reads all JSON files from the vmcp directory and starts runtime servers for each.
        This ensures that servers persist across restarts.
        """
        try:
            # Get all VMCP server resources
            vmcp_resources = self.vmcp_handler.list_all_resources()
            
            for vmcp_data in vmcp_resources:
                name = vmcp_data.get("name", "unknown")
                uuid = vmcp_data.get("uuid", "")
                try:
                    # Extract the necessary fields to start the server
                    description = vmcp_data.get("description", "")
                    port = vmcp_data.get("port")
                    skill_uuid = vmcp_data.get("skill_uuid")
                    
                    # Get tool and snippet UUIDs from skill_uuid
                    tool_uuids = []
                    snippet_uuids = []
                    if skill_uuid:
                        logger.info(f"Resolving tools and snippets for skill_uuid: {skill_uuid} during server load")
                        try:
                            # Get skill by UUID
                            skill_dict = self.skills_handler.get_resource_by_id(skill_uuid)
                            tool_uuids = skill_dict.get("tool_uuids", [])
                            snippet_uuids = skill_dict.get("snippet_uuids", [])
                            logger.info(f"Found skill '{skill_dict.get('name')}' with {len(tool_uuids)} tool UUIDs and {len(snippet_uuids)} snippet UUIDs")
                        except Exception as e:
                            logger.error(f"Error resolving tools and snippets for skill_uuid {skill_uuid}: {e}")
                    
                    # Start the runtime server with UUIDs (not names)
                    # Use composite name for uniqueness
                    if name and uuid:
                        runtime_server_name = self.get_runtime_server_name(name, uuid)
                        server = VirtualMcpServer(
                            name=runtime_server_name,
                            description=description,
                            port=port,
                            tools=tool_uuids,  # Pass UUIDs, not names
                            snippets=snippet_uuids,  # Pass UUIDs, not names
                            sts_url=self.sts_url,
                            app=self.app,
                            env_id="",
                        )
                        self.servers[server.name] = server
                        logger.info(f"Loaded and started vmcp_server: {server.name} on port {server.port} with {len(tool_uuids)} tool UUIDs and {len(snippet_uuids)} snippet UUIDs")
                except Exception as e:
                    logger.error(f"Failed to load vmcp_server '{name}': {str(e)}")
            
            logger.info(f"Loaded {len(self.servers)} vmcp servers from {self.vmcp_directory}")
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
