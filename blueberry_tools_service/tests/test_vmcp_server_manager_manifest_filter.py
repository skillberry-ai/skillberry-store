import pytest
from unittest.mock import Mock, patch
from blueberry_tools_service.modules.vmcp_server_manager import VirtualMcpServerManager
from blueberry_tools_service.modules.lifecycle import LifecycleState


def test_add_server_from_manifest_filter():
    """Test adding a virtual MCP server from manifest filter."""
    with patch('blueberry_tools_service.modules.vmcp_server_manager.VirtualMcpServer') as mock_server_class:
        # Mock server instance
        mock_server = Mock()
        mock_server.name = "Test Server"
        mock_server.description = "Test Description"
        mock_server.port = 8080
        mock_server.tools = ["tool1", "tool2"]
        mock_server_class.return_value = mock_server
        
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
        
        # Verify VirtualMcpServer was created with correct parameters
        mock_server_class.assert_called_once_with(
            name="Test Server",
            description="Test Description",
            port=8080,
            tools=["tool1", "tool2"]
        )
        
        # Verify server was added to manager
        assert "Test Server" in manager.servers
        assert manager.get_server("Test Server") == mock_server


def test_add_server_from_manifest_filter_auto_name():
    """Test adding a virtual MCP server with auto-generated name."""
    with patch('blueberry_tools_service.modules.vmcp_server_manager.VirtualMcpServer') as mock_server_class:
        mock_server = Mock()
        mock_server.name = "Manifest Filter Server - auto_filter"
        mock_server_class.return_value = mock_server
        
        mock_get_manifests = Mock(return_value=[
            {"name": "tool3", "description": "Test tool 3"}
        ])
        
        manager = VirtualMcpServerManager()
        
        manager.add_server_from_manifest_filter(
            manifest_filter="auto_filter",
            get_manifests_func=mock_get_manifests
        )
        
        # Verify VirtualMcpServer was called with auto-generated values
        expected_name = "Manifest Filter Server - auto_filter"
        expected_description = "Virtual MCP Server created from manifest filter: auto_filter, lifecycle state: LifecycleState.ANY"
        
        mock_server_class.assert_called_once_with(
            name=expected_name,
            description=expected_description,
            port=None,
            tools=["tool3"]
        )
        
        # Verify server was added to manager
        assert expected_name in manager.servers


def test_add_server_from_manifest_filter_missing_func():
    """Test error when get_manifests_func is not provided."""
    manager = VirtualMcpServerManager()
    
    with pytest.raises(ValueError, match="get_manifests_func is required"):
        manager.add_server_from_manifest_filter(
            manifest_filter="test_filter"
        )