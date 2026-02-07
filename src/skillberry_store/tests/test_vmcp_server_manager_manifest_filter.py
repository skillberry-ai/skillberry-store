import pytest
from unittest.mock import Mock, patch, mock_open
from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager
from skillberry_store.modules.lifecycle import LifecycleState


def test_add_server_from_manifest_filter():
    """Test adding a virtual MCP server from manifest filter."""
    with patch('skillberry_store.modules.vmcp_server_manager.VirtualMcpServer') as mock_server_class, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch('os.path.exists', return_value=False), \
         patch('skillberry_store.modules.vmcp_server_manager.Manifest') as mock_manifest, \
         patch('skillberry_store.modules.vmcp_server_manager.Description') as mock_description:
        
        # Mock server instance
        mock_server = Mock()
        mock_server.name = "Test Server"
        mock_server.description = "Test Description"
        mock_server.port = 8080
        mock_server.tools = ["tool1", "tool2"]
        mock_server.snippets = []
        mock_server.to_dict.return_value = {
            "name": "Test Server",
            "description": "Test Description",
            "port": 8080,
            "tools": ["tool1", "tool2"],
            "snippets": []
        }
        mock_server.to_manifest.return_value = {
            "name": "Test Server",
            "description": "Test Description"
        }
        mock_server_class.return_value = mock_server
        
        # Mock app with handle_get_manifests method
        mock_app = Mock()
        mock_app.handle_get_manifests.return_value = [
            {"name": "tool1", "description": "Test tool 1"},
            {"name": "tool2", "description": "Test tool 2"}
        ]
        
        # Create manager instance with app
        manager = VirtualMcpServerManager(app=mock_app)
        
        # Reset the mock to ignore calls from load_servers()
        mock_server_class.reset_mock()
        
        # Test the method
        manager.add_server_from_manifest_filter(
            manifest_filter="test_filter",
            lifecycle_state=LifecycleState.APPROVED,
            name="Test Server",
            description="Test Description",
            port=8080,
        )
        
        # Verify handle_get_manifests was called with correct parameters
        mock_app.handle_get_manifests.assert_called_once_with("test_filter", LifecycleState.APPROVED)
        
        # Verify VirtualMcpServer was created with correct parameters
        mock_server_class.assert_called_once_with(
            name="Test Server",
            description="Test Description",
            port=8080,
            tools=["tool1", "tool2"],
            snippets=[],
            bts_url="http://localhost:8000",
            app=mock_app,
            env_id=None
        )
        
        # Verify server was added to manager
        assert "Test Server" in manager.servers
        assert manager.get_server("Test Server") == mock_server


def test_add_server_from_manifest_filter_auto_name():
    """Test adding a virtual MCP server with auto-generated name."""
    with patch('skillberry_store.modules.vmcp_server_manager.VirtualMcpServer') as mock_server_class, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch('os.path.exists', return_value=False), \
         patch('skillberry_store.modules.vmcp_server_manager.Manifest') as mock_manifest, \
         patch('skillberry_store.modules.vmcp_server_manager.Description') as mock_description:
        
        mock_server = Mock()
        mock_server.name = "Manifest Filter Server - auto_filter"
        mock_server.to_dict.return_value = {
            "name": "Manifest Filter Server - auto_filter",
            "description": "Virtual MCP Server created from manifest filter: auto_filter, lifecycle state: any",
            "port": None,
            "tools": ["tool3"],
            "snippets": []
        }
        mock_server.to_manifest.return_value = {
            "name": "Manifest Filter Server - auto_filter",
            "description": "Virtual MCP Server created from manifest filter: auto_filter, lifecycle state: any"
        }
        mock_server_class.return_value = mock_server
        
        mock_app = Mock()
        mock_app.handle_get_manifests.return_value = [
            {"name": "tool3", "description": "Test tool 3"}
        ]
        
        manager = VirtualMcpServerManager(app=mock_app)
        
        # Reset the mock to ignore calls from load_servers()
        mock_server_class.reset_mock()
        
        manager.add_server_from_manifest_filter(
            manifest_filter="auto_filter",
        )
        
        # Verify VirtualMcpServer was called with auto-generated values
        expected_name = "Manifest Filter Server - auto_filter"
        expected_description = "Virtual MCP Server created from manifest filter: auto_filter, lifecycle state: any"
        
        mock_server_class.assert_called_once_with(
            name=expected_name,
            description=expected_description,
            port=None,
            tools=["tool3"],
            snippets=[],
            bts_url="http://localhost:8000",
            app=mock_app,
            env_id=None
        )
        
        # Verify server was added to manager
        assert expected_name in manager.servers


def test_add_server_from_manifest_filter_missing_app():
    """Test error when app is not provided."""
    with patch('builtins.open', mock_open()) as mock_file, \
         patch('os.path.exists', return_value=False), \
         patch('skillberry_store.modules.vmcp_server_manager.Manifest') as mock_manifest, \
         patch('skillberry_store.modules.vmcp_server_manager.Description') as mock_description:
        
        manager = VirtualMcpServerManager()
        
        with pytest.raises(ValueError, match="app is required for manifest filtering"):
            manager.add_server_from_manifest_filter(
                manifest_filter="test_filter"
            )