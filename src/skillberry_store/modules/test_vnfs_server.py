import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import socket
import tempfile
import shutil


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_init_with_port(mock_start):
    """Test that VirtualNfsServer can be initialized with a specific port."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer
    
    server = VirtualNfsServer(
        name="test_server",
        skill_uuid="test-skill-uuid",
        port=11001,
        protocol="webdav",
        description="Test Server"
    )
    
    assert server.port == 11001
    assert server.name == "test_server"
    assert server.description == "Test Server"
    assert server.skill_uuid == "test-skill-uuid"
    assert server.protocol == "webdav"
    assert server.running == False


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_init_without_port(mock_start):
    """Test that VirtualNfsServer can find an available port automatically."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer
    
    server = VirtualNfsServer(
        name="test_server",
        skill_uuid="test-skill-uuid",
        port=None,
        protocol="webdav",
        description="Test Server"
    )
    
    assert server.port is not None
    assert server.port >= 11000  # Default start port for VNFS


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_init_with_unavailable_port(mock_start):
    """Test that VirtualNfsServer raises ValueError when port is unavailable."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer
    
    # Create a socket to occupy a port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))  # Bind to any available port
    _, occupied_port = sock.getsockname()
    
    try:
        with pytest.raises(ValueError, match=f"Port {occupied_port} is not available"):
            VirtualNfsServer(
                name="test_server",
                skill_uuid="test-skill-uuid",
                port=occupied_port,
                protocol="webdav",
                description="Test Server"
            )
    finally:
        sock.close()


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_to_dict(mock_start):
    """Test that VirtualNfsServer.to_dict() returns correct dictionary representation."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer
    
    server = VirtualNfsServer(
        name="test_server",
        skill_uuid="test-skill-uuid",
        port=11002,
        protocol="webdav",
        description="Test Server"
    )
    
    server_dict = server.to_dict()
    assert server_dict["name"] == "test_server"
    assert server_dict["skill_uuid"] == "test-skill-uuid"
    assert server_dict["description"] == "Test Server"
    assert server_dict["port"] == 11002
    assert server_dict["protocol"] == "webdav"
    assert server_dict["running"] == False
    assert "export_path" in server_dict


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_nfs_protocol_selection(mock_start):
    """Test that VirtualNfsServer correctly selects NFS backend."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer, ShenanigaNFSBackend
    
    server = VirtualNfsServer(
        name="test_nfs_server",
        skill_uuid="test-skill-uuid",
        port=11003,
        protocol="nfs",
        description="NFS Test Server"
    )
    
    assert isinstance(server.backend, ShenanigaNFSBackend)
    assert server.protocol == "nfs"


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_webdav_protocol_selection(mock_start):
    """Test that VirtualNfsServer correctly selects WebDAV backend."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer, WebDavBackend
    
    server = VirtualNfsServer(
        name="test_webdav_server",
        skill_uuid="test-skill-uuid",
        port=11004,
        protocol="webdav",
        description="WebDAV Test Server"
    )
    
    assert isinstance(server.backend, WebDavBackend)
    assert server.protocol == "webdav"


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_export_path_creation(mock_start):
    """Test that VirtualNfsServer creates a temporary export path."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer
    
    server = VirtualNfsServer(
        name="test_server",
        skill_uuid="test-skill-uuid",
        port=11005,
        protocol="webdav",
        description="Test Server"
    )
    
    assert server.export_path is not None
    assert isinstance(server.export_path, Path)
    assert server.export_path.exists()
    assert "vnfs_" in str(server.export_path)
    
    # Cleanup
    shutil.rmtree(server.export_path, ignore_errors=True)


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer._is_port_available")
@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_find_available_port(mock_start, mock_is_port_available):
    """Test that VirtualNfsServer finds the next available port."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer
    
    # Simulate first two ports being unavailable, third one available
    mock_is_port_available.side_effect = [False, False, True]
    
    server = VirtualNfsServer(
        name="test_server",
        skill_uuid="test-skill-uuid",
        port=None,
        protocol="webdav",
        description="Test Server"
    )
    
    # Should have tried 3 times and found port on third attempt
    assert mock_is_port_available.call_count == 3
    assert server.port is not None


def test_webdav_backend_initialization():
    """Test WebDAV backend can be initialized."""
    from skillberry_store.modules.vnfs_server import WebDavBackend
    
    backend = WebDavBackend()
    assert backend._server is None
    assert backend._thread is None


def test_shenaniganfs_backend_initialization():
    """Test ShenanigaNFS backend can be initialized."""
    from skillberry_store.modules.vnfs_server import ShenanigaNFSBackend
    
    backend = ShenanigaNFSBackend()
    assert backend._thread is None
    assert backend._loop is None


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_uuid_defaults_to_name(mock_start):
    """Test that UUID defaults to name if not provided."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer
    
    server = VirtualNfsServer(
        name="test_server",
        skill_uuid="test-skill-uuid",
        port=11006,
        protocol="webdav",
        description="Test Server",
        uuid=None
    )
    
    assert server.uuid == "test_server"


@patch("skillberry_store.modules.vnfs_server.VirtualNfsServer.start")
def test_uuid_can_be_set(mock_start):
    """Test that UUID can be explicitly set."""
    from skillberry_store.modules.vnfs_server import VirtualNfsServer
    
    server = VirtualNfsServer(
        name="test_server",
        skill_uuid="test-skill-uuid",
        port=11007,
        protocol="webdav",
        description="Test Server",
        uuid="custom-uuid-123"
    )
    
    assert server.uuid == "custom-uuid-123"

# Made with Bob
