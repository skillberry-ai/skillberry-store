from typing import List, Optional
import uuid
import socket
import logging
import os
from mcp.server.fastmcp import FastMCP
import requests


class VirtualMcpServer:
    """
    Represents a virtual MCP server.

    Attributes:
        name (str): The name of the virtual MCP server.
        description (str): A description of the virtual MCP server.
        port (int): The port on which the virtual MCP server is running.
        tools (List[str]): A list of tool UUIDs registered with the virtual MCP server.
        mcp (FastMCP): The underlying FastMCP instance.
    """

    def __init__(
        self, name: str, description: str, port: Optional[int], tools: List[str], bts_url: str = None
    ):
        """
        Initializes and starts a new VirtualMcpServer instance.

        Args:
            name (str): The name of the virtual MCP server.
            description (str): A description of the virtual MCP server.
            port (Optional[int]): The port for the virtual MCP server. If None, an available port will be found.
            tools (List[str]): A list of tool UUIDs to register with the virtual MCP server.

        Raises:
            ValueError: If the specified port is not available.
        """
        self.name = name
        self.description = description
        self.tools = tools
        self.bts_url = bts_url or "http://localhost:8000"

        if port is None:
            self.port = self._find_available_port()
        else:
            self.port = port
            if not self._is_port_available(port):
                raise ValueError(f"Port {port} is not available")

        print(f"Creating VirtualMcpServer '{name}' on port {self.port}")
        self.mcp = FastMCP(name=name, port=self.port)
        self._start_server()
        print(f"VirtualMcpServer '{name}' created and started on port {self.port}")

    def _is_port_available(self, port: int) -> bool:
        """
        Checks if a port is available.

        Args:
            port (int): The port to check.

        Returns:
            bool: True if the port is available, False otherwise.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return True
            except socket.error:
                return False

    def _find_available_port(self, start_port: int = None) -> int:
        """
        Finds the next available port starting from a given port.

        Args:
            start_port (int): The port to start checking from. If None, uses VMCP_START_PORT env var or 10000.

        Returns:
            int: The available port.
        """
        if start_port is None:
            start_port = int(os.environ.get("VMCP_SERVERS_START_PORT", 10000))

        port = start_port
        while not self._is_port_available(port):
            port += 1
        return port



    def list_tools(self):
        """
        Lists the tools registered with the virtual MCP server.

        Returns:
            list: A list of tools.
        """
        tools = []
        for tool_uuid in self.tools:
            try:
                response = requests.get(f"{self.bts_url}/manifests/{tool_uuid}")
                response.raise_for_status()
                manifest = response.json()
                tools.append(self.manifest_to_tool(manifest))
            except Exception as e:
                logging.warning(f"Failed to get manifest for tool {tool_uuid}: {e}")
        return tools

    async def invoke_tool(self, tool_name: str, parameters: dict):
        """
        Invokes a tool on the virtual MCP server.

        Args:
            tool_name (str): The name of the tool to invoke.
            parameters (dict): The parameters for the tool invocation.

        Returns:
            result: The result of the tool invocation.
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        response = requests.post(
            f"{self.bts_url}/manifests/execute/{tool_name}", json=parameters
        )
        response.raise_for_status()
        return response.json()

    def manifest_to_tool(self, manifest: dict):
        """
        Convert BTS manifest to MCP tool format.
        """
        from mcp import types

        # Clean up extras before unpacking
        extras = manifest.copy()
        for key in ["name", "description", "params"]:
            extras.pop(key, None)

        return types.Tool(
            name=str(manifest["name"]),
            description=manifest.get("description"),
            inputSchema=manifest["params"],
            **extras,
        )

    def _start_server(self, transport="sse"):
        """
        Starts the virtual MCP server.

        Args:
            transport (str): The transport to use. Defaults to "sse".
        """
        import threading

        def run_server():
            print(f"Starting FastMCP server '{self.name}' on port {self.port}")
            self.mcp.run(transport=transport)
            print(f"FastMCP server '{self.name}' started on port {self.port}")
            logging.info(
                f"Virtual MCP server '{self.name}' running on port {self.port} with transport {transport}"
            )

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

    def stop(self):
        """
        Stops the virtual MCP server.
        """
        if hasattr(self, "server_thread") and self.server_thread.is_alive():
            # FastMCP doesn't have a clean stop method, thread will terminate when process ends
            pass

    def to_dict(self):
        """
        Converts the VirtualMcpServer instance to a dictionary.

        Returns:
            dict: A dictionary representation of the VirtualMcpServer.
        """
        return {
            "name": self.name,
            "description": self.description,
            "port": self.port,
            "tools": self.tools,
        }
