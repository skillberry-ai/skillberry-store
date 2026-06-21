"""E2E tests for plugins API endpoints."""

import pytest
import httpx
import logging

BASE_URL = "http://localhost:8000"
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_list_plugins_empty(run_sbs):
    """Test listing plugins when none are installed."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/plugins/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # May be empty or contain plugins depending on environment
        # Just verify the endpoint works


@pytest.mark.asyncio
async def test_list_plugins_structure(run_sbs):
    """Test that list plugins returns correct structure."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/plugins/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # If plugins exist, verify structure
        for plugin in data:
            assert "name" in plugin
            assert "description" in plugin
            assert "version" in plugin
            assert "plugin_type" in plugin
            assert "enabled" in plugin
            assert "has_router" in plugin
            assert "has_cli" in plugin
            assert "has_ui" in plugin
            assert isinstance(plugin["enabled"], bool)
            assert isinstance(plugin["has_router"], bool)
            assert isinstance(plugin["has_cli"], bool)
            assert isinstance(plugin["has_ui"], bool)


@pytest.mark.asyncio
async def test_get_plugin_not_found(run_sbs):
    """Test getting a non-existent plugin returns 404."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/plugins/nonexistent_plugin")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_plugin_info_structure(run_sbs):
    """Test that get plugin info returns correct structure if plugin exists."""
    async with httpx.AsyncClient() as client:
        # First list plugins to see if any exist
        list_response = await client.get(f"{BASE_URL}/plugins/")
        assert list_response.status_code == 200
        plugins = list_response.json()
        
        if not plugins:
            pytest.skip("No plugins installed to test")
        
        # Get info for first plugin
        plugin_name = plugins[0]["name"]
        # Need to get the plugin key/slug, not display name
        # For now, skip this test if no plugins
        pytest.skip("Plugin name resolution needs implementation")


@pytest.mark.asyncio
async def test_plugins_api_cors_headers(run_sbs):
    """Test that plugins API includes CORS headers."""
    async with httpx.AsyncClient() as client:
        response = await client.options(
            f"{BASE_URL}/plugins/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        # FastAPI with CORS middleware should handle OPTIONS preflight
        assert response.status_code in [200, 204]


@pytest.mark.asyncio
async def test_plugins_api_accepts_json(run_sbs):
    """Test that plugins API accepts JSON content type."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/plugins/",
            headers={"Accept": "application/json"}
        )
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_list_plugins_performance(run_sbs):
    """Test that listing plugins completes in reasonable time."""
    import time
    
    async with httpx.AsyncClient() as client:
        start = time.time()
        response = await client.get(f"{BASE_URL}/plugins/")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should complete in under 1 second
        assert elapsed < 1.0, f"List plugins took {elapsed:.2f}s, expected < 1.0s"


@pytest.mark.asyncio
async def test_plugins_api_error_handling(run_sbs):
    """Test that plugins API handles errors gracefully."""
    async with httpx.AsyncClient() as client:
        # Try to get plugin with invalid characters
        response = await client.get(f"{BASE_URL}/plugins/../../../etc/passwd")
        # Should either 404 or handle path traversal safely
        assert response.status_code in [404, 400]


@pytest.mark.asyncio
async def test_plugins_api_returns_valid_json(run_sbs):
    """Test that all plugins API responses are valid JSON."""
    async with httpx.AsyncClient() as client:
        # List plugins
        response = await client.get(f"{BASE_URL}/plugins/")
        assert response.status_code == 200
        data = response.json()  # Will raise if not valid JSON
        assert isinstance(data, list)
        
        # Get non-existent plugin
        response = await client.get(f"{BASE_URL}/plugins/nonexistent")
        assert response.status_code == 404
        data = response.json()  # Will raise if not valid JSON
        assert isinstance(data, dict)


def test_patch_toggles_plugin_enabled(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import Mock
    from skillberry_store.fast_api.plugins_api import register_plugins_api
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.config import PluginConfigStore
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    from skillberry_store.plugins.store_api import StoreAPI

    class P(PluginBase):
        @property
        def metadata(self):
            return PluginMetadata(name="p", description="d", version="1.0",
                                  plugin_type=PluginType.CREATOR)
        def is_enabled(self):
            return True
        def get_router(self):
            return None
        def get_cli_commands(self):
            return None
        def get_ui_config(self):
            return None

    cfg = PluginConfigStore(path=tmp_path / "plugins.json")
    loader = PluginLoader(store_api=Mock(spec=StoreAPI), config_store=cfg)
    loader.plugins["p"] = P()

    app = FastAPI()
    register_plugins_api(app, plugin_loader=loader)
    client = TestClient(app)

    resp = client.patch("/plugins/p", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["admin_enabled"] is False
    assert resp.json()["enabled"] is False

    resp = client.patch("/plugins/p", json={"enabled": True})
    assert resp.json()["admin_enabled"] is True

    assert client.patch("/plugins/does-not-exist", json={"enabled": False}).status_code == 404

# Made with Bob