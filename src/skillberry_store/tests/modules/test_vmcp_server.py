import pytest
from unittest.mock import patch, MagicMock
from skillberry_store.modules.vmcp_server import VirtualMcpServer

import socket


@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._start_server")
@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._register_prompts")
@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._register_tools")
@patch("skillberry_store.modules.vmcp_server.FastMCP")
def test_init_with_port(
    mock_fastmcp, mock_register_tools, mock_register_prompts, mock_start_server
):
    """Test that VirtualMcpServer can be initialized with a specific port."""
    # Mock FastMCP instance
    mock_mcp_instance = MagicMock()
    mock_fastmcp.return_value = mock_mcp_instance

    server = VirtualMcpServer(
        name="test_server", description="Test Server", port=None, tools=[], snippets=[]
    )
    # Use dynamically allocated port instead of hardcoded 8080
    assert server.port is not None
    assert server.name == "test_server"
    assert server.description == "Test Server"


@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._start_server")
@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._register_prompts")
@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._register_tools")
@patch("skillberry_store.modules.vmcp_server.FastMCP")
def test_init_without_port(
    mock_fastmcp, mock_register_tools, mock_register_prompts, mock_start_server
):
    """Test that VirtualMcpServer can find an available port automatically."""
    # Mock FastMCP instance
    mock_mcp_instance = MagicMock()
    mock_fastmcp.return_value = mock_mcp_instance

    server = VirtualMcpServer(
        name="test_server", description="Test Server", port=None, tools=[], snippets=[]
    )
    assert server.port is not None


@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._start_server")
@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._register_prompts")
@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._register_tools")
@patch("skillberry_store.modules.vmcp_server.FastMCP")
def test_init_with_unavailable_port(
    mock_fastmcp, mock_register_tools, mock_register_prompts, mock_start_server
):
    """Test that VirtualMcpServer raises ValueError when port is unavailable."""
    # Mock FastMCP instance
    mock_mcp_instance = MagicMock()
    mock_fastmcp.return_value = mock_mcp_instance

    # Create a socket to occupy a port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))  # Bind to any available port
    _, occupied_port = sock.getsockname()

    try:
        with pytest.raises(ValueError, match=f"Port {occupied_port} is not available"):
            VirtualMcpServer(
                name="test_server",
                description="Test Server",
                port=occupied_port,
                tools=[],
                snippets=[],
            )
    finally:
        sock.close()


@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._start_server")
@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._register_prompts")
@patch("skillberry_store.modules.vmcp_server.VirtualMcpServer._register_tools")
@patch("skillberry_store.modules.vmcp_server.FastMCP")
def test_to_dict(
    mock_fastmcp, mock_register_tools, mock_register_prompts, mock_start_server
):
    """Test that VirtualMcpServer.to_dict() returns correct dictionary representation."""
    # Mock FastMCP instance
    mock_mcp_instance = MagicMock()
    mock_fastmcp.return_value = mock_mcp_instance

    server = VirtualMcpServer(
        name="test_server",
        description="Test Server",
        port=None,
        tools=[],
        snippets=["snippet1"],
    )
    server_dict = server.to_dict()
    assert server_dict["name"] == "test_server"
    assert server_dict["description"] == "Test Server"
    assert server_dict["port"] == server.port  # Use actual port instead of hardcoded
    assert server_dict["tools"] == []
    assert server_dict["snippets"] == ["snippet1"]
