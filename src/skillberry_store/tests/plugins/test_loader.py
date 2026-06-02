"""Tests for plugin loader."""

import pytest
from typing import Optional, Dict, Any
from unittest.mock import Mock, MagicMock, patch
from fastapi import APIRouter, FastAPI


def test_plugin_loader_initialization():
    """Test that PluginLoader can be initialized."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    assert loader.store_api is mock_store_api
    assert loader.plugins == {}


def test_plugin_loader_discover_plugins_empty():
    """Test discovering plugins when none are installed."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    with patch('skillberry_store.plugins.loader.entry_points', return_value=[]):
        discovered = loader.discover_plugins()
    
    assert discovered == []
    assert loader.plugins == {}


def test_plugin_loader_discover_single_plugin():
    """Test discovering a single valid plugin."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    
    # Create a mock plugin class
    class MockPlugin(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="Test Plugin",
                description="A test plugin",
                version="1.0.0",
                plugin_type=PluginType.CREATOR
            )
        
        def is_enabled(self) -> bool:
            return True
        
        def get_router(self) -> Optional[APIRouter]:
            return None
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return None
    
    # Mock entry point
    mock_entry_point = Mock()
    mock_entry_point.name = "test_plugin"
    mock_entry_point.load.return_value = MockPlugin
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    with patch('skillberry_store.plugins.loader.entry_points', return_value=[mock_entry_point]):
        discovered = loader.discover_plugins()
    
    assert len(discovered) == 1
    assert "test_plugin" in loader.plugins
    assert isinstance(loader.plugins["test_plugin"], MockPlugin)
    assert loader.plugins["test_plugin"]._store_api is mock_store_api


def test_plugin_loader_discover_disabled_plugin():
    """Test that disabled plugins are discovered but marked as disabled."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    
    class DisabledPlugin(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="Disabled Plugin",
                description="A disabled plugin",
                version="1.0.0",
                plugin_type=PluginType.CREATOR
            )
        
        def is_enabled(self) -> bool:
            return False
        
        def get_router(self) -> Optional[APIRouter]:
            return None
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return None
    
    mock_entry_point = Mock()
    mock_entry_point.name = "disabled_plugin"
    mock_entry_point.load.return_value = DisabledPlugin
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    with patch('skillberry_store.plugins.loader.entry_points', return_value=[mock_entry_point]):
        discovered = loader.discover_plugins()
    
    assert len(discovered) == 1
    assert "disabled_plugin" in loader.plugins
    assert not loader.plugins["disabled_plugin"].is_enabled()


def test_plugin_loader_handles_missing_dependencies():
    """Test that loader handles plugins with missing dependencies gracefully."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    
    # Mock entry point that raises ImportError
    mock_entry_point = Mock()
    mock_entry_point.name = "broken_plugin"
    mock_entry_point.load.side_effect = ImportError("Missing dependency")
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    with patch('skillberry_store.plugins.loader.entry_points', return_value=[mock_entry_point]):
        discovered = loader.discover_plugins()
    
    # Should not crash, just skip the broken plugin
    assert discovered == []
    assert "broken_plugin" not in loader.plugins


def test_plugin_loader_handles_invalid_plugin_class():
    """Test that loader handles invalid plugin classes gracefully."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    
    # Mock entry point that returns non-PluginBase class
    class NotAPlugin:
        pass
    
    mock_entry_point = Mock()
    mock_entry_point.name = "invalid_plugin"
    mock_entry_point.load.return_value = NotAPlugin
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    with patch('skillberry_store.plugins.loader.entry_points', return_value=[mock_entry_point]):
        discovered = loader.discover_plugins()
    
    # Should skip invalid plugin
    assert discovered == []
    assert "invalid_plugin" not in loader.plugins


def test_plugin_loader_mount_routers_to_app():
    """Test mounting plugin routers to FastAPI app."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    
    # Create plugin with router
    mock_router = APIRouter()
    
    class PluginWithRouter(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="Router Plugin",
                description="Plugin with router",
                version="1.0.0",
                plugin_type=PluginType.CREATOR
            )
        
        def is_enabled(self) -> bool:
            return True
        
        def get_router(self) -> Optional[APIRouter]:
            return mock_router
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return None
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    # Manually add plugin
    plugin = PluginWithRouter()
    plugin.set_store_api(mock_store_api)
    loader.plugins["router_plugin"] = plugin
    
    # Mock FastAPI app
    mock_app = Mock(spec=FastAPI)
    
    loader.mount_routers(mock_app)
    
    # Verify router was mounted
    mock_app.include_router.assert_called_once()
    call_args = mock_app.include_router.call_args
    assert call_args[0][0] is mock_router
    assert call_args[1]["prefix"] == "/plugins/router_plugin"
    assert call_args[1]["tags"] == ["plugins", "router_plugin"]


def test_plugin_loader_mount_routers_skips_disabled():
    """Test that disabled plugins' routers are not mounted."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    
    mock_router = APIRouter()
    
    class DisabledPluginWithRouter(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="Disabled Router Plugin",
                description="Disabled plugin with router",
                version="1.0.0",
                plugin_type=PluginType.CREATOR
            )
        
        def is_enabled(self) -> bool:
            return False
        
        def get_router(self) -> Optional[APIRouter]:
            return mock_router
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return None
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    plugin = DisabledPluginWithRouter()
    plugin.set_store_api(mock_store_api)
    loader.plugins["disabled_router"] = plugin
    
    mock_app = Mock(spec=FastAPI)
    
    loader.mount_routers(mock_app)
    
    # Should not mount disabled plugin's router
    mock_app.include_router.assert_not_called()


def test_plugin_loader_mount_routers_skips_none():
    """Test that plugins returning None router are skipped."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    
    class PluginWithoutRouter(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="No Router Plugin",
                description="Plugin without router",
                version="1.0.0",
                plugin_type=PluginType.CREATOR
            )
        
        def is_enabled(self) -> bool:
            return True
        
        def get_router(self) -> Optional[APIRouter]:
            return None
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return None
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    plugin = PluginWithoutRouter()
    plugin.set_store_api(mock_store_api)
    loader.plugins["no_router"] = plugin
    
    mock_app = Mock(spec=FastAPI)
    
    loader.mount_routers(mock_app)
    
    # Should not mount anything
    mock_app.include_router.assert_not_called()


def test_plugin_loader_get_plugin_info():
    """Test getting info about a specific plugin."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    
    class TestPlugin(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="Test Plugin",
                description="A test plugin",
                version="1.0.0",
                plugin_type=PluginType.CREATOR,
                author="Test Author",
                homepage="https://example.com"
            )
        
        def is_enabled(self) -> bool:
            return True
        
        def get_router(self) -> Optional[APIRouter]:
            return None
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return {"icon": "PlusIcon", "color": "#0066CC"}
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    plugin = TestPlugin()
    plugin.set_store_api(mock_store_api)
    loader.plugins["test_plugin"] = plugin
    
    info = loader.get_plugin_info("test_plugin")
    
    assert info is not None
    assert info["name"] == "Test Plugin"
    assert info["description"] == "A test plugin"
    assert info["version"] == "1.0.0"
    assert info["plugin_type"] == "creator"
    assert info["author"] == "Test Author"
    assert info["homepage"] == "https://example.com"
    assert info["enabled"] is True
    assert info["has_router"] is False
    assert info["has_cli"] is False
    assert info["has_ui"] is True


def test_plugin_loader_get_plugin_info_not_found():
    """Test getting info for non-existent plugin."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    info = loader.get_plugin_info("nonexistent")
    
    assert info is None


def test_plugin_loader_list_all_plugins():
    """Test listing all plugins."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    
    class Plugin1(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="Plugin 1",
                description="First plugin",
                version="1.0.0",
                plugin_type=PluginType.CREATOR
            )
        
        def is_enabled(self) -> bool:
            return True
        
        def get_router(self) -> Optional[APIRouter]:
            return None
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return None
    
    class Plugin2(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="Plugin 2",
                description="Second plugin",
                version="2.0.0",
                plugin_type=PluginType.EVALUATOR
            )
        
        def is_enabled(self) -> bool:
            return False
        
        def get_router(self) -> Optional[APIRouter]:
            return None
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return None
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    plugin1 = Plugin1()
    plugin1.set_store_api(mock_store_api)
    loader.plugins["plugin1"] = plugin1
    
    plugin2 = Plugin2()
    plugin2.set_store_api(mock_store_api)
    loader.plugins["plugin2"] = plugin2
    
    all_plugins = loader.list_plugins()
    
    assert len(all_plugins) == 2
    assert any(p["name"] == "Plugin 1" and p["enabled"] is True for p in all_plugins)
    assert any(p["name"] == "Plugin 2" and p["enabled"] is False for p in all_plugins)


def test_plugin_loader_list_plugins_empty():
    """Test listing plugins when none are loaded."""
    from skillberry_store.plugins.loader import PluginLoader
    from skillberry_store.plugins.store_api import StoreAPI
    
    mock_store_api = Mock(spec=StoreAPI)
    loader = PluginLoader(store_api=mock_store_api)
    
    all_plugins = loader.list_plugins()
    
    assert all_plugins == []

# Made with Bob