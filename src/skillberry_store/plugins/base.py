"""Base classes for Skillberry Store plugins."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from enum import Enum

if TYPE_CHECKING:
    from fastapi import APIRouter


class PluginType(str, Enum):
    """Types of plugins supported."""
    CREATOR = "creator"
    EVALUATOR = "evaluator"
    OPTIMIZER = "optimizer"


class PluginMetadata(BaseModel):
    """Metadata describing a plugin."""
    name: str = Field(..., description="Display name of the plugin")
    description: str = Field(..., description="What the plugin does")
    version: str = Field(..., description="Plugin version")
    plugin_type: PluginType = Field(..., description="Type of plugin")
    author: Optional[str] = None
    homepage: Optional[str] = None


class PluginBase(ABC):
    """Base class all plugins must inherit from.
    
    Plugins are SELF-CONTAINED and provide their own:
    - API routes (via get_router())
    - CLI commands (via get_cli_commands())
    - UI components (via get_ui_config())
    
    The store core automatically discovers and integrates these
    without requiring any code changes to the store itself.
    """
    
    def __init__(self):
        self._store_api: Optional[Any] = None
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if plugin is properly configured and enabled."""
        pass
    
    def get_status_message(self) -> str:
        """Get a human-readable status message explaining plugin state.
        
        This method should return:
        - "Ready" or similar positive message when enabled
        - A clear explanation of what's missing/wrong when disabled
        
        Returns:
            Status message string
        """
        if self.is_enabled():
            return "Ready"
        return "Plugin is disabled"
    
    @abstractmethod
    def get_router(self) -> Optional["APIRouter"]:
        """Return FastAPI router for this plugin's endpoints.
        
        The router will be automatically mounted at /api/plugins/{plugin_name}/
        
        Returns:
            APIRouter with plugin-specific endpoints, or None if no API needed
            
        Example:
            from fastapi import APIRouter
            router = APIRouter()
            
            @router.post("/create")
            async def create_content(...):
                ...
            
            return router
        """
        pass
    
    @abstractmethod
    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        """Return CLI commands for this plugin.
        
        Commands will be automatically registered under: sbs plugin {plugin_name} {command}
        
        Returns:
            Dict mapping command names to Click/Typer command functions
            
        Example:
            import click
            
            @click.command()
            @click.option('--type', required=True)
            def create(type):
                ...
            
            return {"create": create, "list": list_items}
        """
        pass
    
    @abstractmethod
    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        """Return UI configuration for this plugin.
        
        The UI will automatically render plugin cards and actions based on this config.
        
        Returns:
            Dict with:
            - icon: Icon name (PatternFly icon)
            - color: Hex color for the plugin card
            - actions: List of {label, endpoint, method, params_schema}
            - settings_schema: JSON schema for plugin settings (optional)
            
        Example:
            return {
                "icon": "PlusIcon",
                "color": "#0066CC",
                "actions": [
                    {
                        "label": "Create Tool",
                        "endpoint": "/api/plugins/creator/create",
                        "method": "POST",
                        "params_schema": {...}
                    }
                ]
            }
        """
        pass
    
    def set_store_api(self, store_api: Any):
        """Called by plugin loader to provide store API access.
        
        Plugins can then use self.store to access content.
        """
        self._store_api = store_api
    
    @property
    def store(self) -> Any:
        """Access to store API for querying/updating content."""
        if self._store_api is None:
            raise RuntimeError("Store API not initialized. Plugin loader should call set_store_api().")
        return self._store_api

# Made with Bob
