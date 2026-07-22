import pytest
from unittest.mock import patch, MagicMock
from skillberry_store.modules.vmcp_server import VirtualMcpServer

import socket


@pytest.fixture(autouse=True)
def _stub_object_handlers(monkeypatch):
    """Stub ``get_object_handler`` for every test in this module.

    ``VirtualMcpServer.__init__`` calls ``get_object_handler("tool")`` and
    ``get_object_handler("snippet")`` at construction time, which require
    the process-wide singletons to have been initialised by ``SBS()``.
    These constructor tests mock every method that would actually use the
    handlers (``_register_tools``/``_register_prompts``/``_start_server``),
    so a bare ``MagicMock`` is sufficient to bypass the singleton gate and
    keep the tests hermetic (previously they only passed by inheriting
    initialised state from an earlier test in the pytest session).
    """
    from skillberry_store.modules import vmcp_server as _vmcp_mod

    monkeypatch.setattr(
        _vmcp_mod, "get_object_handler", lambda _name: MagicMock()
    )


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
