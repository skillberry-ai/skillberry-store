"""Admin API endpoints for the Skillberry Store service."""

import logging
import shutil
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException

from skillberry_store.tools.configure import (
    get_files_directory_path,
    get_tools_directory,
    get_skills_directory,
    get_snippets_directory,
    get_manifest_directory,
    get_descriptions_directory,
    get_tools_descriptions_directory,
    get_skills_descriptions_directory,
    get_snippets_descriptions_directory,
)

logger = logging.getLogger(__name__)

# VMCP servers persistent file location
VMCP_SERVERS_FILE = os.environ.get("VMCP_SERVERS_FILE", "/tmp/vmcp_servers.json")


def register_admin_api(app: FastAPI, tags: str = "admin"):
    """Register admin API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
    """

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

        # Step 1: Stop all VMCP servers and clear in-memory state
        # Access the VMCP server manager from the app if it exists
        vmcp_stopped = False
        try:
            # Get the vmcp_server_manager from the app's virtual_mcp_server_api
            # Since it's created per-request, we need to stop servers manually
            from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager
            
            # Create a temporary manager to access and stop all servers
            bts_url = f"http://{app.state.settings.bts_host if hasattr(app, 'state') and hasattr(app.state, 'settings') else '0.0.0.0'}:8000"
            temp_manager = VirtualMcpServerManager(bts_url=bts_url, app=app)
            
            # Stop all servers
            server_names = temp_manager.list_servers()
            for server_name in server_names:
                try:
                    temp_manager.remove_server(server_name)
                    logger.info(f"Stopped VMCP server: {server_name}")
                except Exception as e:
                    logger.warning(f"Failed to stop VMCP server {server_name}: {str(e)}")
            
            vmcp_stopped = True
            logger.info("All VMCP servers stopped")
        except Exception as e:
            logger.warning(f"Failed to stop VMCP servers: {str(e)}")

        # Step 2: Delete VMCP servers persistent file
        try:
            if os.path.exists(VMCP_SERVERS_FILE):
                os.remove(VMCP_SERVERS_FILE)
                logger.info(f"Deleted VMCP servers file: {VMCP_SERVERS_FILE}")
        except Exception as e:
            logger.warning(f"Failed to delete VMCP servers file: {str(e)}")

        # Step 3: Delete all data directories
        directories_to_purge = [
            ("files", get_files_directory_path()),
            ("tools", get_tools_directory()),
            ("skills", get_skills_directory()),
            ("snippets", get_snippets_directory()),
            ("manifest", get_manifest_directory()),
            ("descriptions", get_descriptions_directory()),
            ("tools_descriptions", get_tools_descriptions_directory()),
            ("skills_descriptions", get_skills_descriptions_directory()),
            ("snippets_descriptions", get_snippets_descriptions_directory()),
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

        # Step 4: Reset in-memory vector indexes
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

        logger.info(f"Successfully purged all data. Deleted directories: {deleted_dirs}")
        return {
            "message": "All backend data successfully purged",
            "deleted_directories": deleted_dirs,
            "total_deleted": len(deleted_dirs),
            "vmcp_servers_stopped": vmcp_stopped,
            "vector_indexes_reset": vector_indexes_reset,
        }

    @app.get("/health", tags=[tags])
    def health_check():
        """Health check endpoint.

        Returns:
            dict: Health status of the service.
        """
        return {"status": "healthy"}