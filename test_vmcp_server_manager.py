import pytest
from fastapi.testclient import TestClient
from skillberry_store.fast_api.server import SBS


def test_vmcp_server_manager_searchable_via_fastapi():
    """Test that VMCP server endpoints are accessible via FastAPI."""
    # Create FastAPI test client
    app = SBS()
    client = TestClient(app)
    
    # Test that the vmcp_servers endpoint exists and returns the expected structure
    response = client.get("/vmcp_servers/")
    assert response.status_code == 200
    servers = response.json()
    assert isinstance(servers, dict)
    assert "virtual_mcp_servers" in servers
    assert isinstance(servers["virtual_mcp_servers"], dict)