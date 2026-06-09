"""Tests for plugin base classes."""

import pytest
from typing import Optional, Dict, Any


def test_plugin_type_enum():
    """Test that PluginType enum has expected values."""
    from skillberry_store.plugins.base import PluginType
    
    assert PluginType.CREATOR == "creator"
    assert PluginType.EVALUATOR == "evaluator"
    assert PluginType.OPTIMIZER == "optimizer"
    assert PluginType.IMPORTER == "importer"


def test_plugin_metadata_creation():
    """Test creating PluginMetadata with required fields."""
    from skillberry_store.plugins.base import PluginMetadata, PluginType
    
    metadata = PluginMetadata(
        name="Test Plugin",
        description="A test plugin",
        version="1.0.0",
        plugin_type=PluginType.CREATOR
    )
    
    assert metadata.name == "Test Plugin"
    assert metadata.description == "A test plugin"
    assert metadata.version == "1.0.0"
    assert metadata.plugin_type == PluginType.CREATOR
    assert metadata.author is None
    assert metadata.homepage is None


def test_plugin_metadata_with_optional_fields():
    """Test creating PluginMetadata with optional fields."""
    from skillberry_store.plugins.base import PluginMetadata, PluginType
    
    metadata = PluginMetadata(
        name="Test Plugin",
        description="A test plugin",
        version="1.0.0",
        plugin_type=PluginType.CREATOR,
        author="Test Author",
        homepage="https://example.com"
    )
    
    assert metadata.author == "Test Author"
    assert metadata.homepage == "https://example.com"


def test_plugin_base_is_abstract():
    """Test that PluginBase cannot be instantiated directly."""
    from skillberry_store.plugins.base import PluginBase
    
    with pytest.raises(TypeError):
        PluginBase()


def test_plugin_base_concrete_implementation():
    """Test that a concrete plugin implementation works."""
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    
    class TestPlugin(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="Test",
                description="Test plugin",
                version="1.0.0",
                plugin_type=PluginType.CREATOR
            )
        
        def is_enabled(self) -> bool:
            return True
        
        def get_router(self) -> Optional[Any]:
            return None
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return None
    
    plugin = TestPlugin()
    assert plugin.metadata.name == "Test"
    assert plugin.is_enabled() is True
    assert plugin.get_router() is None
    assert plugin.get_cli_commands() is None
    assert plugin.get_ui_config() is None


def test_plugin_base_store_api_access():
    """Test that plugin can access store API after initialization."""
    from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
    
    class TestPlugin(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="Test",
                description="Test plugin",
                version="1.0.0",
                plugin_type=PluginType.CREATOR
            )
        
        def is_enabled(self) -> bool:
            return True
        
        def get_router(self) -> Optional[Any]:
            return None
        
        def get_cli_commands(self) -> Optional[Dict[str, Any]]:
            return None
        
        def get_ui_config(self) -> Optional[Dict[str, Any]]:
            return None
    
    plugin = TestPlugin()
    
    # Should raise error before store API is set
    with pytest.raises(RuntimeError, match="Store API not initialized"):
        _ = plugin.store
    
    # Mock store API
    class MockStoreAPI:
        pass
    
    mock_store = MockStoreAPI()
    plugin.set_store_api(mock_store)
    
    # Should work after setting
    assert plugin.store is mock_store


def test_plugin_base_requires_all_abstract_methods():
    """Test that plugin must implement all abstract methods."""
    from skillberry_store.plugins.base import PluginBase
    
    # Missing get_router
    class IncompletePlugin(PluginBase):
        @property
        def metadata(self):
            pass
        
        def is_enabled(self):
            pass
        
        def get_cli_commands(self):
            pass
        
        def get_ui_config(self):
            pass
    
    with pytest.raises(TypeError):
        IncompletePlugin()

# Made with Bob
