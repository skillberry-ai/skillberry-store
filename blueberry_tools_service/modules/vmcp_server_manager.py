import os
import json
import logging
from typing import Any, Dict, Optional
from blueberry_tools_service.modules.vmcp_server import VirtualMcpServer
from blueberry_tools_service.modules.lifecycle import LifecycleState
from blueberry_tools_service.modules.description import Description
from blueberry_tools_service.modules.description_vector_index import (
    DescriptionVectorIndex,
)
from blueberry_tools_service.tools.configure import get_descriptions_directory

logger = logging.getLogger(__name__)

VMCP_SERVERS_FILE = os.environ.get("VMCP_SERVERS_FILE", "/tmp/vmcp_servers.json")


class VirtualMcpServerManager:
    """Manages virtual MCP servers for the Blueberry Tools Service.

    This class provides functionality to create, manage, and persist virtual MCP servers
    that can be dynamically created from tool search results or manually configured.
    """

    def __init__(self):
        """Initialize the virtual MCP server manager.

        Loads existing virtual MCP servers from persistent storage.
        """
        self.servers: Dict[str, VirtualMcpServer] = {}
        logger.info(f"Loading vmcp_servers from {VMCP_SERVERS_FILE}")
        self.load_servers()

    def add_server(self, name: str, description: str, port: Optional[int], tools: list):
        """Add a new virtual MCP server.

        Args:
            name: The name of the virtual MCP server.
            description: A description of the virtual MCP server.
            port: The port number for the server (optional, auto-assigned if None).
            tools: List of tool names to include in the server.

        Returns:
            VirtualMcpServer: The created virtual MCP server instance.
        """
        logger.info(f"Adding vmcp_server: {name}")
        server = VirtualMcpServer(
            name=name, description=description, port=port, tools=tools
        )
        self.servers[server.name] = server
        self.save_servers()
        logger.info(f"Added and started new vmcp_server: {name} on port {server.port}")
        return server

    def remove_server(self, name: str):
        """Remove a virtual MCP server.

        Args:
            name: The name of the virtual MCP server to remove.
        """
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
            self.save_servers()
        else:
            logger.debug(f"vmcp_server {name} not found")

    def list_servers(self):
        """List all virtual MCP server names.

        Returns:
            List[str]: A list of virtual MCP server names.
        """
        logger.debug("Listing vmcp_servers")
        return list(self.servers.keys())

    def get_server(self, name: str) -> VirtualMcpServer:
        """Get a virtual MCP server by name.

        Args:
            name: The name of the virtual MCP server.

        Returns:
            VirtualMcpServer: The virtual MCP server instance, or None if not found.
        """
        logger.debug(f"Getting vmcp_server: {name}")
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
        server = self.get_server(name)
        if server:
            return {
                "name": server.name,
                "description": server.description,
                "port": server.port,
                "tools": server.tools,
            }
        else:
            raise ValueError(f"vmcp_server '{name}' not found")

    def load_servers(self):
        """Load virtual MCP servers from persistent storage.

        Loads server configurations from the JSON file and recreates server instances.
        If the file doesn't exist, starts with an empty server list.
        """
        try:
            with open(VMCP_SERVERS_FILE, "r") as f:
                data = json.load(f)
                for server_data in data:
                    try:
                        server = VirtualMcpServer(**server_data)
                        self.servers[server.name] = server
                        logger.info(f"Loaded vmcp_server: {server.name}")
                    except Exception as e:
                        logger.error(
                            f"Failed to load vmcp_server: {server_data.get('name', 'unknown')}. Error: {str(e)}"
                        )
        except FileNotFoundError:
            logger.info(
                f"{VMCP_SERVERS_FILE} not found. Starting with empty list of vmcp_servers."
            )
        except Exception as e:
            logger.error(f"Failed to load vmcp_servers. Error: {str(e)}")

    def save_servers(self):
        """Save virtual MCP servers to persistent storage.

        Serializes all server configurations to a JSON file for persistence.
        """
        data = []
        for server in self.servers.values():
            server_data = server.to_dict()
            data.append(server_data)
        try:
            with open(VMCP_SERVERS_FILE, "w") as f:
                json.dump(data, f, indent=4)
            logger.info(f"Saved vmcp_servers to {VMCP_SERVERS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save vmcp_servers. Error: {str(e)}")

    def add_server_from_search_term(
        self,
        search_term: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        port: Optional[int] = None,
        max_results: int = 5,
    ):
        """Create a virtual MCP server from a search term.

        Searches for tools matching the search term and creates a virtual MCP server
        containing those tools.

        Args:
            search_term: The search term to find relevant tools.
            name: Optional name for the virtual MCP server (auto-generated if None).
            description: Optional description for the server (auto-generated if None).
            port: Optional port number for the server (auto-assigned if None).
            max_results: Maximum number of search results to include (default: 5).

        Raises:
            Exception: If server creation fails.
        """
        try:
            logger.info(f"Starting add_server_from_search_term for: {search_term}")
            descriptions_directory = get_descriptions_directory()
            descriptions = Description(
                descriptions_directory=descriptions_directory,
                vector_index=DescriptionVectorIndex,
            )
            search_results = descriptions.search_description(
                search_term=search_term, k=max_results
            )
            tools = [result["filename"] for result in search_results]
            logger.info(f"Found tools: {tools}")

            if name is None:
                name = f"Search Term Server - {search_term}"
                # Ensure name is unique
                base_name = name
                counter = 1
                while name in self.servers:
                    name = f"{base_name} ({counter})"
                    counter += 1

            if description is None:
                description = (
                    f"Virtual MCP Server created from search term: {search_term}"
                )

            logger.info(f"About to call add_server with name={name}, tools={tools}")
            self.add_server(name=name, description=description, port=port, tools=tools)
            logger.info(f"Completed add_server_from_search_term")
        except Exception as e:
            logger.error(f"Exception in add_server_from_search_term: {e}")
            logger.error(f"Failed to add vmcp_server from search term: {str(e)}")
            raise

    def add_server_from_manifest_filter(
        self,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
        name: Optional[str] = None,
        description: Optional[str] = None,
        port: Optional[int] = None,
        get_manifests_func=None,
    ):
        """Create a virtual MCP server from filtered manifests.

        Filters manifests based on the provided criteria and creates a virtual MCP server
        containing those tools.

        Args:
            manifest_filter: Manifest properties to filter (default: ".").
            lifecycle_state: Lifecycle state to filter (default: ANY).
            name: Optional name for the virtual MCP server (auto-generated if None).
            description: Optional description for the server (auto-generated if None).
            port: Optional port number for the server (auto-assigned if None).
            get_manifests_func: Function to get manifests (required).

        Raises:
            Exception: If server creation fails.
            ValueError: If get_manifests_func is not provided.
        """
        try:
            if get_manifests_func is None:
                raise ValueError("get_manifests_func is required")

            logger.info(
                f"Starting add_server_from_manifest_filter with filter: {manifest_filter}, state: {lifecycle_state}"
            )

            manifests = get_manifests_func(manifest_filter, lifecycle_state)
            tools = [manifest["name"] for manifest in manifests]
            logger.info(f"Found tools from manifests: {tools}")

            if name is None:
                name = f"Manifest Filter Server - {manifest_filter}"
                # Ensure name is unique
                base_name = name
                counter = 1
                while name in self.servers:
                    name = f"{base_name} ({counter})"
                    counter += 1

            if description is None:
                description = (
                    f"Virtual MCP Server created from manifest filter: {manifest_filter}, "
                    f"lifecycle state: {lifecycle_state}"
                )

            logger.info(f"About to call add_server with name={name}, tools={tools}")
            self.add_server(name=name, description=description, port=port, tools=tools)
            logger.info(f"Completed add_server_from_manifest_filter")
        except Exception as e:
            logger.error(f"Exception in add_server_from_manifest_filter: {e}")
            logger.error(f"Failed to add vmcp_server from manifest filter: {str(e)}")
            raise
