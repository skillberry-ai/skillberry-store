import pytest
from unittest.mock import Mock
from blueberry_tools_service.modules.vmcp_server_manager import VirtualMcpServerManager
from blueberry_tools_service.modules.lifecycle import LifecycleState


def test_add_server_from_manifest_filter():
    """Test adding a virtual MCP server from manifest filter."""
    # Mock get_manifests function
    mock_get_manifests = Mock(return_value=[
        {"name": "tool1", "description": "Test tool 1"},
        {"name": "tool2", "description": "Test tool 2"}
    ])
    
    # Create manager instance
    manager = VirtualMcpServerManager()
    
    # Test the method
    manager.add_server_from_manifest_filter(
        manifest_filter="test_filter",
        lifecycle_state=LifecycleState.APPROVED,
        name="Test Server",
        description="Test Description",
        port=8080,
        get_manifests_func=mock_get_manifests
    )
    
    # Verify get_manifests was called with correct parameters
    mock_get_manifests.assert_called_once_with("test_filter", LifecycleState.APPROVED)
    
    # Verify server was created
    assert "Test Server" in manager.servers
    server = manager.get_server("Test Server")
    assert server.name == "Test Server"
    assert server.description == "Test Description"
    assert server.port == 8080
    assert server.tools == ["tool1", "tool2"]


def test_add_server_from_manifest_filter_auto_name():
    """Test adding a virtual MCP server with auto-generated name."""
    mock_get_manifests = Mock(return_value=[
        {"name": "tool3", "description": "Test tool 3"}
    ])
    
    manager = VirtualMcpServerManager()
    
    manager.add_server_from_manifest_filter(
        manifest_filter="auto_filter",
        get_manifests_func=mock_get_manifests
    )
    
    # Verify server was created with auto-generated name
    expected_name = "Manifest Filter Server - auto_filter"
    assert expected_name in manager.servers
    server = manager.get_server(expected_name)
    assert "Virtual MCP Server created from manifest filter: auto_filter" in server.description


def test_add_server_from_manifest_filter_missing_func():
    """Test error when get_manifests_func is not provided."""
    manager = VirtualMcpServerManager()
    
    with pytest.raises(ValueError, match="get_manifests_func is required"):
        manager.add_server_from_manifest_filter(
            manifest_filter="test_filter"
        )