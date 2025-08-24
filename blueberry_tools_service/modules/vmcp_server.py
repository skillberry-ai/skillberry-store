from typing import List, Optional
import uuid
import socket
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

    BTS_URL = "http://localhost:8000"  # Hardcoded local BTS URL

    def __init__(self, name: str, description: str, port: Optional[int], tools: List[str]):
        """
        Initializes a new VirtualMcpServer instance.

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
        
        if port is None:
            self.port = self._find_available_port()
        else:
            self.port = port
            if not self._is_port_available(port):
                raise ValueError(f"Port {port} is not available")
        
        self.mcp = FastMCP(name=name, port=self.port)

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

    def _find_available_port(self, start_port: int = 10000) -> int:
        """
        Finds the next available port starting from a given port.

        Args:
            start_port (int): The port to start checking from. Defaults to 10000.

        Returns:
            int: The available port.
        """
        port = start_port
        while not self._is_port_available(port):
            port += 1
        return port

    def _create_tool_proxy(self, tool_uuid: str):
        """
        Creates a tool proxy for a given tool UUID.

        Args:
            tool_uuid (str): The UUID of the tool.

        Returns:
            function: A proxy function that executes the tool.
        """
        def tool_proxy(**kwargs):
            response = requests.post(f"{self.BTS_URL}/manifests/execute/{tool_uuid}", json=kwargs)
            response.raise_for_status()
            return response.json()
        return tool_proxy

    def list_tools(self):
        """
        Lists the tools registered with the virtual MCP server.

        Returns:
            list: A list of tools.
        """
        return self.mcp.list_tools()

    def invoke_tool(self, tool_name: str, parameters: dict):
        """
        Invokes a tool on the virtual MCP server.

        Args:
            tool_name (str): The name of the tool to invoke.
            parameters (dict): The parameters for the tool invocation.

        Returns:
            result: The result of the tool invocation.
        """
        return self.mcp.invoke_tool(tool_name, parameters)

    def run(self, transport="sse"):
        """
        Runs the virtual MCP server.

        Args:
            transport (str): The transport to use. Defaults to "sse".
        """
        self.mcp.run(transport=transport)

    def to_dict(self):
        """
        Converts the VirtualMcpServer instance to a dictionary.

        Returns:
            dict: A dictionary representation of the VirtualMcpServer.
        """
        return {
            'name': self.name,
            'description': self.description,
            'port': self.port,
            'tools': self.tools,
        }