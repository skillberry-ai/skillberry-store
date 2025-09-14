import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from blueberry_tools_service.fast_api.server import BTS


def test_vmcp_server_manager_searchable_via_fastapi():
    """Test that VirtualMcpServerManager instances are searchable via FastAPI endpoints."""
    with patch('blueberry_tools_service.fast_api.server.Manifest') as mock_manifest_server, \
         patch('blueberry_tools_service.fast_api.server.Description') as mock_description_server, \
         patch('blueberry_tools_service.modules.vmcp_server_manager.VirtualMcpServer') as mock_vmcp_server, \
         patch('blueberry_tools_service.modules.vmcp_server_manager.Manifest') as mock_manifest_manager, \
         patch('blueberry_tools_service.modules.vmcp_server_manager.Description') as mock_description_manager:
        
        # Mock server manifest instance for FastAPI server
        mock_manifest_server_instance = Mock()
        mock_manifest_server_instance.list_manifests.return_value = [{
            "name": "test_server",
            "description": "Test server for search",
            "programming_language": "vmcp_server",
            "packaging_format": "vmcp_server",
            "state": "approved",
            "uid": "test_server"
        }]
        mock_manifest_server.return_value = mock_manifest_server_instance
        
        # Mock VirtualMcpServer
        mock_server = Mock()
        mock_server.name = "test_server"
        mock_server.to_manifest.return_value = {
            "name": "test_server",
            "description": "Test server for search",
            "programming_language": "vmcp_server",
            "packaging_format": "vmcp_server",
            "state": "approved",
            "uid": "test_server"
        }
        mock_vmcp_server.return_value = mock_server
        
        # Create FastAPI test client
        app = BTS()
        client = TestClient(app)
        
        # Add a virtual MCP server
        response = client.post("/vmcp_servers/add", json={
            "name": "test_server",
            "description": "Test server for search",
            "port": 8080,
            "tools": ["tool1"]
        })
        assert response.status_code == 200
        
        # Verify the server manifest is searchable via manifests endpoint
        response = client.get("/manifests/", params={"manifest_filter": "programming_language:vmcp_server"})
        assert response.status_code == 200
        manifests = response.json()
        assert len(manifests) == 1
        assert manifests[0]["name"] == "test_server"