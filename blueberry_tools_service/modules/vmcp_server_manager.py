import os
import json
import logging
from typing import Any, Dict, Optional
from blueberry_tools_service.modules.vmcp_server import VirtualMcpServer
from blueberry_tools_service.modules.lifecycle import LifecycleState
from blueberry_tools_service.modules.description import Description
from blueberry_tools_service.modules.description_vector_index import DescriptionVectorIndex
from blueberry_tools_service.tools.configure import get_descriptions_directory

logger = logging.getLogger(__name__)

VMCP_SERVERS_FILE = os.environ.get("VMCP_SERVERS_FILE", "/tmp/vmcp_servers.json")


class VirtualMcpServerManager:
    def __init__(self):
        self.servers: Dict[str, VirtualMcpServer] = {}
        logger.info(f"Loading vmcp_servers from {VMCP_SERVERS_FILE}")
        self.load_servers()

    def add_server(self, name: str, description: str, port: Optional[int], tools: list):
        print(f"Adding vmcp_server: {name}")
        logger.info(f"Adding vmcp_server: {name}")
        server = VirtualMcpServer(
            name=name, description=description, port=port, tools=tools
        )
        self.servers[server.name] = server
        self.save_servers()
        print(f"Added and started new vmcp_server: {name} on port {server.port}")
        logger.info(f"Added and started new vmcp_server: {name} on port {server.port}")
        return server

    def remove_server(self, name: str):
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
        logger.debug("Listing vmcp_servers")
        return list(self.servers.keys())

    def get_server(self, name: str) -> VirtualMcpServer:
        logger.debug(f"Getting vmcp_server: {name}")
        return self.servers.get(name)

    def get_server_details(self, name: str) -> Dict[str, Any]:
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
        try:
            print(f"Starting add_server_from_search_term for: {search_term}")
            descriptions_directory = get_descriptions_directory()
            descriptions = Description(
                descriptions_directory=descriptions_directory,
                vector_index=DescriptionVectorIndex,
            )
            search_results = descriptions.search_description(
                search_term=search_term, k=max_results
            )
            tools = [result["filename"] for result in search_results]
            print(f"Found tools: {tools}")

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

            print(f"About to call add_server with name={name}, tools={tools}")
            self.add_server(name=name, description=description, port=port, tools=tools)
            print(f"Completed add_server_from_search_term")
        except Exception as e:
            print(f"Exception in add_server_from_search_term: {e}")
            logger.error(f"Failed to add vmcp_server from search term: {str(e)}")
            raise
