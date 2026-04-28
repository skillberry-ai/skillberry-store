"""Admin API endpoints for the Skillberry Store service."""

import logging
import shutil
import os
import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from skillberry_store.tools.configure import (
    _default_sbs_dir,
    get_files_directory_path,
    get_tools_directory,
    get_skills_directory,
    get_snippets_directory,
    get_tools_descriptions_directory,
    get_skills_descriptions_directory,
    get_snippets_descriptions_directory,
    get_vmcp_directory,
    get_vmcp_descriptions_directory,
)

logger = logging.getLogger(__name__)

# VMCP servers persistent file location (uses cross-platform temp dir instead of /tmp/)
VMCP_SERVERS_FILE = os.environ.get(
    "VMCP_SERVERS_FILE",
    os.path.join(_default_sbs_dir(""), "vmcp_servers.json"),
)

# Prometheus metrics port
PROMETHEUS_METRICS_PORT = int(os.getenv("PROMETHEUS_METRICS_PORT", 8090))


def register_admin_api(app: FastAPI, tags: str = "admin"):
    """Register admin API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
    """
    @app.get("/admin/metrics", tags=[tags], response_class=PlainTextResponse)
    async def get_metrics():
        """Proxy endpoint to fetch Prometheus metrics.
        
        This endpoint proxies requests to the Prometheus metrics server
        to avoid CORS issues when accessing metrics from the UI.
        
        Returns:
            PlainTextResponse: The raw Prometheus metrics in text format.
            
        Raises:
            HTTPException: If metrics server is not accessible (503).
        """
        try:
            metrics_url = f"http://localhost:{PROMETHEUS_METRICS_PORT}/metrics"
            async with httpx.AsyncClient() as client:
                response = await client.get(metrics_url, timeout=5.0)
                if response.status_code == 200:
                    return PlainTextResponse(content=response.text, media_type="text/plain")
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Metrics server returned status {response.status_code}"
                    )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to metrics server on port {PROMETHEUS_METRICS_PORT}. "
                       f"Ensure PROMETHEUS_METRICS_PORT environment variable is set correctly."
            )
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Error fetching metrics: {str(e)}"
            )


    @app.delete("/admin/purge-all", tags=[tags])
    async def purge_all_data():
        """Delete all backend components including skills, tools, snippets, VMCP servers, and their descriptions.

        This endpoint performs a hard delete by:
        1. Stopping all running VMCP servers
        2. Clearing VMCP servers persistent storage
        3. Removing all data directories
        4. Recreating empty directories
        5. Resetting in-memory vector indexes

        Use with caution as this operation is irreversible.

        Returns:
            dict: Success message with details of deleted directories.

        Raises:
            HTTPException: If deletion fails (500 status code).
        """
        logger.warning("Admin purge-all endpoint called - deleting all backend data")

        # Step 1: Stop all VMCP servers using the existing manager from app.state
        vmcp_stopped = False
        vmcp_servers_count = 0
        try:
            # Use the existing vmcp_server_manager from app.state
            if hasattr(app, 'state') and hasattr(app.state, 'vmcp_server_manager'):
                vmcp_manager = app.state.vmcp_server_manager
                
                # Get list of all servers before stopping them
                server_names = vmcp_manager.list_servers()
                vmcp_servers_count = len(server_names)
                
                # Stop and remove all servers
                for server_name in server_names:
                    try:
                        vmcp_manager.remove_server(server_name)
                        logger.info(f"Stopped and removed VMCP server: {server_name}")
                    except Exception as e:
                        logger.warning(f"Failed to stop VMCP server {server_name}: {str(e)}")
                
                vmcp_stopped = True
                logger.info(f"All {vmcp_servers_count} VMCP servers stopped and removed")
            else:
                logger.warning("vmcp_server_manager not found in app.state")
        except Exception as e:
            logger.warning(f"Failed to stop VMCP servers: {str(e)}")

        # Step 2: Delete all data directories (including VMCP directory)
        directories_to_purge = [
            ("files", get_files_directory_path()),
            ("tools", get_tools_directory()),
            ("skills", get_skills_directory()),
            ("snippets", get_snippets_directory()),
            ("vmcp", get_vmcp_directory()),
            ("tools_descriptions", get_tools_descriptions_directory()),
            ("skills_descriptions", get_skills_descriptions_directory()),
            ("snippets_descriptions", get_snippets_descriptions_directory()),
            ("vmcp_descriptions", get_vmcp_descriptions_directory()),
        ]

        deleted_dirs = []
        failed_dirs = []

        for dir_name, dir_path in directories_to_purge:
            try:
                if os.path.exists(dir_path):
                    logger.info(f"Deleting directory: {dir_path}")
                    shutil.rmtree(dir_path)
                    deleted_dirs.append(dir_name)
                    logger.info(f"Successfully deleted: {dir_path}")
                else:
                    logger.info(f"Directory does not exist, skipping: {dir_path}")

                # Recreate the directory
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                logger.info(f"Recreated empty directory: {dir_path}")
                
                # For description directories, also recreate the /index/ subdirectory
                if "descriptions" in dir_name:
                    index_dir = os.path.join(dir_path, "index")
                    Path(index_dir).mkdir(parents=True, exist_ok=True)
                    logger.info(f"Recreated index subdirectory: {index_dir}")

            except Exception as e:
                error_msg = f"Failed to delete {dir_name} at {dir_path}: {str(e)}"
                logger.error(error_msg)
                failed_dirs.append({"name": dir_name, "path": dir_path, "error": str(e)})

        # Step 3: Reset in-memory vector indexes
        vector_indexes_reset = False
        try:
            if hasattr(app, 'state'):
                # Reinitialize all description instances with empty vector indexes
                if hasattr(app.state, 'descriptions'):
                    app.state.descriptions.load_index()
                    logger.info("Reset descriptions vector index")
                
                if hasattr(app.state, 'tools_descriptions'):
                    app.state.tools_descriptions.load_index()
                    logger.info("Reset tools_descriptions vector index")
                
                if hasattr(app.state, 'snippets_descriptions'):
                    app.state.snippets_descriptions.load_index()
                    logger.info("Reset snippets_descriptions vector index")
                
                if hasattr(app.state, 'skills_descriptions'):
                    app.state.skills_descriptions.load_index()
                    logger.info("Reset skills_descriptions vector index")
                
                if hasattr(app.state, 'vmcp_descriptions'):
                    app.state.vmcp_descriptions.load_index()
                    logger.info("Reset vmcp_descriptions vector index")
                
                vector_indexes_reset = True
                logger.info("All in-memory vector indexes reset successfully")
        except Exception as e:
            logger.warning(f"Failed to reset vector indexes: {str(e)}")

        if failed_dirs:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Some directories failed to delete",
                    "deleted": deleted_dirs,
                    "failed": failed_dirs,
                    "vmcp_servers_stopped": vmcp_stopped,
                    "vector_indexes_reset": vector_indexes_reset,
                },
            )

        logger.info(f"Successfully purged all data. Deleted directories: {deleted_dirs}, stopped {vmcp_servers_count} VMCP servers")
        return {
            "message": "All backend data successfully purged",
            "deleted_directories": deleted_dirs,
            "total_deleted": len(deleted_dirs),
            "vmcp_servers_stopped": vmcp_stopped,
            "vmcp_servers_count": vmcp_servers_count,
            "vector_indexes_reset": vector_indexes_reset,
        }

    @app.get("/admin/server-info", tags=[tags])
    def get_server_info():
        """Get server connection information for MCP clients.

        Returns:
            dict: Server host, port, MCP endpoint URLs, and API docs URL.
        """
        settings = app.settings
        host = settings.display_host
        port = settings.sbs_port
        agent_mcp_port = settings.agent_mcp_port

        agent_mcp_running = hasattr(app, 'agent_mcp') and app.agent_mcp is not None
        return {
            "host": host,
            "port": port,
            "agent_mcp_port": agent_mcp_port,
            "agent_mcp_url": f"http://{host}:{agent_mcp_port}/sse" if agent_mcp_running else None,
            "control_mcp_url": f"http://{host}:{port}/control_sse",
            "api_docs": f"http://{host}:{port}/docs",
        }

    @app.get("/health", tags=[tags])
    def health_check():
        """Health check endpoint.

        Returns:
            dict: Health status of the service.
        """
        return {"status": "healthy"}

    @app.get("/plugins", tags=[tags])
    def list_plugins():
        """List all installed plugins with their current enabled state and UI manifests."""
        from skillberry_store.plugins import installed_plugins, read_enabled

        enabled_ids = set(read_enabled())
        items = []
        for p in installed_plugins():
            is_enabled = p.id in enabled_ids
            items.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "enabled": is_enabled,
                "requires_restart": getattr(p, "requires_restart", False),
                "ui_manifest": p.ui_manifest.to_dict() if is_enabled else None,
            })
        return {"plugins": items}

    @app.post("/plugins/{plugin_id}/enable", tags=[tags])
    def enable_plugin(plugin_id: str):
        """Enable a plugin.

        For plugins with `requires_restart=False`, routes are mounted live.
        Otherwise `enabled.json` is updated but the response signals that a
        store restart is required for the change to take effect.
        """
        from skillberry_store.plugins import (
            get_plugin,
            is_enabled,
            mount_plugin,
            set_enabled,
        )

        plugin = get_plugin(plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not installed")

        already = is_enabled(plugin_id)
        set_enabled(plugin_id, True)

        if plugin.requires_restart:
            return {"plugin_id": plugin_id, "enabled": True, "restart_required": True}

        if not already:
            try:
                if hasattr(plugin, "bind_app"):
                    plugin.bind_app(app)
                mount_plugin(app, plugin)
            except Exception as e:
                logger.error(f"Failed to mount plugin '{plugin_id}': {e}")
                raise HTTPException(status_code=500, detail=f"Mount failed: {e}")

        return {"plugin_id": plugin_id, "enabled": True, "restart_required": False}

    @app.post("/plugins/{plugin_id}/disable", tags=[tags])
    def disable_plugin(plugin_id: str):
        """Disable a plugin.

        For plugins with `requires_restart=False`, routes are removed live.
        Otherwise `enabled.json` is updated but the response signals that a
        store restart is required for the change to take effect.
        """
        from skillberry_store.plugins import (
            get_plugin,
            is_enabled,
            set_enabled,
            unmount_plugin,
        )

        plugin = get_plugin(plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not installed")

        was_enabled = is_enabled(plugin_id)
        set_enabled(plugin_id, False)

        if plugin.requires_restart:
            return {"plugin_id": plugin_id, "enabled": False, "restart_required": True}

        if was_enabled:
            try:
                unmount_plugin(app, plugin)
            except Exception as e:
                logger.error(f"Failed to unmount plugin '{plugin_id}': {e}")
                raise HTTPException(status_code=500, detail=f"Unmount failed: {e}")

        return {"plugin_id": plugin_id, "enabled": False, "restart_required": False}

    @app.get("/health/ready", tags=[tags])
    def readiness_check():
        """Readiness check endpoint - verifies all description directories are initialized.

        Returns:
            dict: Readiness status with details about each directory (HTTP 200 when ready).
        
        Raises:
            HTTPException: 500 status when still initializing.
        """
        checks = {}
        
        # Check all known description objects in app.state
        description_attrs = [
            'tools_descriptions',
            'snippets_descriptions',
            'skills_descriptions',
            'vmcp_descriptions'
        ]
        
        for attr_name in description_attrs:
            desc_obj = getattr(app.state, attr_name, None)
            if desc_obj and hasattr(desc_obj, 'descriptions_directory'):
                dir_path = desc_obj.descriptions_directory
                checks[attr_name] = {
                    "path": dir_path,
                    "exists": os.path.exists(dir_path)
                }
            else:
                checks[attr_name] = {
                    "path": None,
                    "exists": False
                }
        
        # Server is ready if all checks pass
        all_ready = all(check["exists"] for check in checks.values())
        
        if not all_ready:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "initializing",
                    "checks": checks
                }
            )
        
        return {
            "status": "ready",
            "checks": checks
        }
