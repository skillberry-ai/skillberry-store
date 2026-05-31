"""Plugin loader for discovering and managing plugins."""

import logging
from typing import Dict, List, Optional, Any
from importlib.metadata import entry_points
from fastapi import FastAPI

from skillberry_store.plugins.base import PluginBase
from skillberry_store.plugins.store_api import StoreAPI

logger = logging.getLogger(__name__)


class PluginLoader:
    """Discovers and manages plugins via entry points.
    
    Plugins are discovered through the 'skillberry_store.plugins' entry point group.
    Each plugin must be a subclass of PluginBase.
    """
    
    def __init__(self, store_api: StoreAPI):
        """Initialize the plugin loader.
        
        Args:
            store_api: StoreAPI instance to inject into plugins
        """
        self.store_api = store_api
        self.plugins: Dict[str, PluginBase] = {}
    
    def discover_plugins(self) -> List[str]:
        """Discover and load all available plugins.
        
        Plugins are discovered via the 'skillberry_store.plugins' entry point.
        Invalid plugins or those with missing dependencies are skipped with a warning.
        
        Returns:
            List of successfully loaded plugin names
        """
        discovered = []
        
        # Get all entry points for skillberry_store.plugins
        eps = entry_points()
        
        # Handle different return types from entry_points()
        if isinstance(eps, list):
            # Mocked or old-style list
            plugin_entries = eps
        elif hasattr(eps, 'select'):
            # Python 3.10+
            plugin_entries = eps.select(group='skillberry_store.plugins')
        else:
            # Python 3.9 dict-like
            plugin_entries = eps.get('skillberry_store.plugins', [])
        
        for entry_point in plugin_entries:
            try:
                # Load the plugin class
                plugin_class = entry_point.load()
                
                # Verify it's a PluginBase subclass
                if not isinstance(plugin_class, type) or not issubclass(plugin_class, PluginBase):
                    logger.warning(
                        f"Plugin '{entry_point.name}' is not a PluginBase subclass, skipping"
                    )
                    continue
                
                # Instantiate the plugin
                plugin = plugin_class()
                
                # Inject store API
                plugin.set_store_api(self.store_api)
                
                # Store the plugin
                self.plugins[entry_point.name] = plugin
                discovered.append(entry_point.name)
                
                logger.info(
                    f"Loaded plugin '{entry_point.name}': {plugin.metadata.name} v{plugin.metadata.version}"
                )
                
            except ImportError as e:
                logger.warning(
                    f"Plugin '{entry_point.name}' has missing dependencies: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to load plugin '{entry_point.name}': {e}",
                    exc_info=True
                )
        
        return discovered
    
    def mount_routers(self, app: FastAPI):
        """Mount plugin routers to the FastAPI app.
        
        Only enabled plugins with routers are mounted.
        Routers are mounted at /plugins/{plugin_name}/
        
        Args:
            app: FastAPI application instance
        """
        for plugin_name, plugin in self.plugins.items():
            # Skip disabled plugins
            if not plugin.is_enabled():
                logger.info(f"Plugin '{plugin_name}' is disabled, skipping router mount")
                continue
            
            # Get router
            router = plugin.get_router()
            if router is None:
                continue
            
            # Mount router
            prefix = f"/plugins/{plugin_name}"
            app.include_router(
                router,
                prefix=prefix,
                tags=["plugins", plugin_name]
            )
            
            logger.info(f"Mounted router for plugin '{plugin_name}' at {prefix}")
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dict with plugin info, or None if plugin not found
        """
        plugin = self.plugins.get(plugin_name)
        if plugin is None:
            return None
        
        metadata = plugin.metadata
        ui_config = plugin.get_ui_config()
        
        return {
            "slug": plugin_name,  # Entry point name used in URLs
            "name": metadata.name,
            "description": metadata.description,
            "version": metadata.version,
            "plugin_type": metadata.plugin_type.value,
            "author": metadata.author,
            "homepage": metadata.homepage,
            "enabled": plugin.is_enabled(),
            "status": plugin.get_status_message(),
            "has_router": plugin.get_router() is not None,
            "has_cli": plugin.get_cli_commands() is not None,
            "has_ui": ui_config is not None,
            "ui_config": ui_config,
        }
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins.
        
        Returns:
            List of plugin info dicts
        """
        result = []
        for plugin_name in self.plugins.keys():
            info = self.get_plugin_info(plugin_name)
            if info is not None:
                result.append(info)
        return result

# Made with Bob