"""Plugins API endpoints for the Skillberry Store service."""

import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException

logger = logging.getLogger(__name__)


def register_plugins_api(app: FastAPI, plugin_loader: Any, tags: str = "plugins"):
    """Register plugin management API endpoints.

    Args:
        app: FastAPI application instance
        plugin_loader: PluginLoader instance
        tags: OpenAPI tags for these endpoints
    """

    @app.get(
        "/plugins/",
        tags=[tags],
        summary="List all plugins",
        response_model=List[Dict[str, Any]],
    )
    async def list_plugins():
        """List all discovered plugins with their metadata and status.

        Returns:
            List of plugin info dictionaries containing:
            - name: Display name
            - description: What the plugin does
            - version: Plugin version
            - plugin_type: Type of plugin (creator, evaluator, optimizer)
            - author: Plugin author (optional)
            - homepage: Plugin homepage URL (optional)
            - enabled: Whether plugin is enabled
            - has_router: Whether plugin provides API routes
            - has_cli: Whether plugin provides CLI commands
            - has_ui: Whether plugin provides UI configuration
        """
        try:
            plugins = plugin_loader.list_plugins()
            return plugins
        except Exception as e:
            logger.error(f"Failed to list plugins: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to list plugins: {str(e)}"
            )

    @app.get(
        "/plugins/{plugin_name}",
        tags=[tags],
        summary="Get plugin information",
        response_model=Dict[str, Any],
    )
    async def get_plugin_info(plugin_name: str):
        """Get detailed information about a specific plugin.

        Args:
            plugin_name: Name/slug of the plugin

        Returns:
            Plugin info dictionary with metadata and status

        Raises:
            HTTPException: 404 if plugin not found
        """
        try:
            plugin_info = plugin_loader.get_plugin_info(plugin_name)
            if plugin_info is None:
                raise HTTPException(
                    status_code=404, detail=f"Plugin '{plugin_name}' not found"
                )
            return plugin_info
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to get plugin info for '{plugin_name}': {e}", exc_info=True
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to get plugin info: {str(e)}"
            )


# Made with Bob
