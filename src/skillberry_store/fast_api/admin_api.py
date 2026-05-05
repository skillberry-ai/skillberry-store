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
    @app.get("/admin/server-info", tags=[tags])
    async def get_server_info():
        """Return connection info for the backend and its MCP endpoints.

        Used by the Connect Your Agent UI to render copy-ready
        `claude mcp add` commands and to know which SSE URL to test.
        `agent_mcp_url` is None when the curated agent MCP failed to start.
        """
        settings = app.settings
        host = settings.display_host
        port = settings.sbs_port
        agent_mcp_port = getattr(settings, "agent_mcp_port", None)
        agent_mcp_url = None
        if agent_mcp_port is not None and getattr(app, "agent_mcp", None) is not None:
            agent_mcp_url = f"http://{host}:{agent_mcp_port}/sse"
        return {
            "host": host,
            "port": port,
            "agent_mcp_port": agent_mcp_port,
            "agent_mcp_url": agent_mcp_url,
            "control_mcp_url": f"http://{host}:{port}/control_sse",
            "api_docs": f"http://{host}:{port}/docs",
        }

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

    @app.get("/health", tags=[tags])
    def health_check():
        """Health check endpoint.

        Returns:
            dict: Health status of the service.
        """
        return {"status": "healthy"}

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