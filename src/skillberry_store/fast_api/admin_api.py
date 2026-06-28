"""Admin API endpoints for the Skillberry Store service."""

import logging
import shutil
import os
import httpx
import json
import zipfile
import io
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse, StreamingResponse

from skillberry_store.tools.configure import _default_sbs_dir

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

    @app.get(
        "/admin/metrics",
        tags=[tags],
        response_class=PlainTextResponse,
        openapi_extra={"x-cli-name": "metrics"},
    )
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
                    return PlainTextResponse(
                        content=response.text, media_type="text/plain"
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Metrics server returned status {response.status_code}",
                    )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to metrics server on port {PROMETHEUS_METRICS_PORT}. "
                f"Ensure PROMETHEUS_METRICS_PORT environment variable is set correctly.",
            )
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            raise HTTPException(
                status_code=503, detail=f"Error fetching metrics: {str(e)}"
            )

    @app.delete(
        "/admin/purge-all", tags=[tags], openapi_extra={"x-cli-name": "purge-all"}
    )
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
            if hasattr(app, "state") and hasattr(app.state, "vmcp_server_manager"):
                from skillberry_store.modules.object_handler import get_object_handler

                vmcp_manager = app.state.vmcp_server_manager
                vmcp_handler = get_object_handler("vmcp")
                # Iterate over all vmcp objects to get name and UUID
                for vmcp_obj in vmcp_handler.iter_dicts():
                    name = vmcp_obj.get("name", "unknown")
                    uuid = vmcp_obj.get("uuid", "unknown")
                    try:
                        if name != "unknown" and uuid != "unknown":
                            vmcp_manager.remove_server(name, uuid)
                            logger.info(
                                f"Stopped and removed VMCP server: {name} ({uuid})"
                            )
                            vmcp_servers_count += 1
                        else:
                            logger.warning(
                                f"VMCP object missing name or uuid: {vmcp_obj}"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to stop VMCP server {name}: {str(e)}")
                vmcp_stopped = True
                logger.info(
                    f"All {vmcp_servers_count} VMCP servers stopped and removed"
                )
            else:
                logger.warning("vmcp_server_manager not found in app.state")
        except Exception as e:
            logger.warning(f"Failed to stop VMCP servers: {str(e)}")

        # Step 1b: Stop all vNFS servers
        vnfs_stopped = False
        vnfs_servers_count = 0
        try:
            if hasattr(app, "state") and hasattr(app.state, "vnfs_server_manager"):
                from skillberry_store.modules.object_handler import get_object_handler

                vnfs_manager = app.state.vnfs_server_manager
                vnfs_handler = get_object_handler("vnfs")
                # Iterate over all vnfs objects to get name and UUID
                for vnfs_obj in vnfs_handler.iter_dicts():
                    name = vnfs_obj.get("name", "unknown")
                    uuid = vnfs_obj.get("uuid", "unknown")
                    try:
                        if name != "unknown" and uuid != "unknown":
                            vnfs_manager.remove_server(name, uuid)
                            logger.info(
                                f"Stopped and removed vNFS server: {name} ({uuid})"
                            )
                            vnfs_servers_count += 1
                        else:
                            logger.warning(
                                f"vNFS object missing name or uuid: {vnfs_obj}"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to stop vNFS server {name}: {str(e)}")
                vnfs_stopped = True
                logger.info(
                    f"All {vnfs_servers_count} vNFS servers stopped and removed"
                )
            else:
                logger.warning("vnfs_server_manager not found in app.state")
        except Exception as e:
            logger.warning(f"Failed to stop vNFS servers: {str(e)}")

        # Step 2: Purge all ObjectHandler data and clear in-memory state
        deleted_dirs = []
        failed_dirs = []

        caches_cleared = False
        try:
            from skillberry_store.modules.object_handler import get_object_handler

            for object_type in ["tool", "snippet", "skill", "vmcp", "vnfs"]:
                try:
                    get_object_handler(object_type).purge_all()
                    deleted_dirs.append(object_type)
                except Exception as e:
                    logger.warning(f"Failed to purge {object_type}: {str(e)}")
                    failed_dirs.append({"name": object_type, "error": str(e)})

            caches_cleared = True
            logger.info("All ObjectHandler data and caches purged")
        except Exception as e:
            logger.warning(f"Failed to purge ObjectHandler data: {str(e)}")

        # Step 3: Vector indexes are reset inside purge_all() — no separate step needed.
        vector_indexes_reset = caches_cleared

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

        logger.info(
            f"Successfully purged all data. Deleted directories: {deleted_dirs}, "
            f"stopped {vmcp_servers_count} VMCP servers, stopped {vnfs_servers_count} vNFS servers, "
            f"cleared caches: {caches_cleared}"
        )
        return {
            "message": "All backend data successfully purged",
            "deleted_directories": deleted_dirs,
            "total_deleted": len(deleted_dirs),
            "vmcp_servers_stopped": vmcp_stopped,
            "vmcp_servers_count": vmcp_servers_count,
            "vnfs_servers_stopped": vnfs_stopped,
            "vnfs_servers_count": vnfs_servers_count,
            "caches_cleared": caches_cleared,
            "vector_indexes_reset": vector_indexes_reset,
        }

    @app.get(
        "/admin/backup",
        tags=[tags],
        openapi_extra={"x-cli-name": "backup"},
        response_class=StreamingResponse,
    )
    async def backup_all_data():
        """Create a backup of all data (skills, tools, snippets, VMCP servers, vNFS servers).

        Returns a compressed JSON file (.json.zip) containing all data.
        The UI should download this file directly.

        Returns:
            StreamingResponse: A ZIP file containing the backup JSON.

        Raises:
            HTTPException: If backup creation fails (500 status code).
        """
        logger.info("Admin backup endpoint called - creating backup of all data")

        try:
            from skillberry_store.modules.object_handler import get_object_handler

            # Collect all data
            backup_data = {
                "skills": [],
                "tools": [],
                "snippets": [],
                "vmcp_servers": [],
                "vnfs_servers": [],
                "exported_at": datetime.utcnow().isoformat(),
            }

            # Export skills
            skill_handler = get_object_handler("skill")
            for skill_dict in skill_handler.iter_dicts():
                backup_data["skills"].append(skill_dict)

            # Export tools with their module content
            tool_handler = get_object_handler("tool")
            for tool_dict in tool_handler.iter_dicts():
                tool_uuid = tool_dict.get("uuid")
                module_name = tool_dict.get("module_name")

                # Get module content if it exists
                if tool_uuid and module_name:
                    try:
                        # Use ObjectHandler's read_file method to get module content from UUID subfolder
                        module_content = tool_handler.read_file(
                            tool_uuid, module_name, raw_content=True
                        )
                        tool_dict["module_content"] = module_content
                    except Exception as e:
                        logger.warning(
                            f"Failed to get module content for tool {tool_dict.get('name')}: {e}"
                        )

                backup_data["tools"].append(tool_dict)

            # Export snippets
            snippet_handler = get_object_handler("snippet")
            for snippet_dict in snippet_handler.iter_dicts():
                backup_data["snippets"].append(snippet_dict)

            # Export VMCP servers
            vmcp_handler = get_object_handler("vmcp")
            for vmcp_dict in vmcp_handler.iter_dicts():
                # Remove runtime fields that shouldn't be backed up
                vmcp_backup = {
                    k: v
                    for k, v in vmcp_dict.items()
                    if k not in ["running", "runtime"]
                }
                backup_data["vmcp_servers"].append(vmcp_backup)

            # Export vNFS servers
            vnfs_handler = get_object_handler("vnfs")
            for vnfs_dict in vnfs_handler.iter_dicts():
                # Remove runtime fields that shouldn't be backed up
                vnfs_backup = {
                    k: v
                    for k, v in vnfs_dict.items()
                    if k not in ["running", "export_path"]
                }
                backup_data["vnfs_servers"].append(vnfs_backup)

            # Create compressed JSON
            json_string = json.dumps(backup_data, indent=2)

            # Create ZIP file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                filename = (
                    f"skillberry-backup-{datetime.utcnow().strftime('%Y-%m-%d')}.json"
                )
                zip_file.writestr(filename, json_string)

            zip_buffer.seek(0)

            logger.info(
                f"Backup created successfully: {len(backup_data['skills'])} skills, "
                f"{len(backup_data['tools'])} tools, {len(backup_data['snippets'])} snippets, "
                f"{len(backup_data['vmcp_servers'])} VMCP servers, {len(backup_data['vnfs_servers'])} vNFS servers"
            )

            # Return as streaming response
            return StreamingResponse(
                iter([zip_buffer.getvalue()]),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=skillberry-backup-{datetime.utcnow().strftime('%Y-%m-%d')}.json.zip"
                },
            )

        except Exception as e:
            logger.error(f"Backup failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

    @app.post(
        "/admin/restore",
        tags=[tags],
        openapi_extra={"x-cli-name": "restore"},
    )
    async def restore_all_data(backup_file: UploadFile = File(...)):
        """Restore all data from a backup file.

        This endpoint:
        1. Purges all existing data (calls purge_all_data internally)
        2. Restores data from the uploaded backup file
        3. Imports in order: tools, snippets, skills, VMCP servers, vNFS servers
        4. Starts VMCP/vNFS servers that are in approved state
        5. Rebuilds caches and description indexes

        Args:
            backup_file: The backup ZIP file to restore from.

        Returns:
            dict: Success message with counts of restored items.

        Raises:
            HTTPException: If restore fails (400 or 500 status code).
        """
        logger.warning("Admin restore endpoint called - restoring all data from backup")

        try:
            # Read and decompress the backup file
            content = await backup_file.read()

            try:
                with zipfile.ZipFile(io.BytesIO(content), "r") as zip_file:
                    # Find the first JSON file in the ZIP
                    json_files = [
                        name for name in zip_file.namelist() if name.endswith(".json")
                    ]
                    if not json_files:
                        raise HTTPException(
                            status_code=400,
                            detail="No JSON file found in the ZIP archive",
                        )

                    # Extract and parse the JSON content
                    json_content = zip_file.read(json_files[0])
                    backup_data = json.loads(json_content)
            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail="Invalid ZIP file format")
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, detail="Invalid JSON format in backup file"
                )

            # Validate backup data structure
            if not isinstance(backup_data, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid backup file format: expected JSON object",
                )

            # First, purge all existing data by calling the existing purge endpoint
            logger.info("Purging existing data before restore...")
            try:
                purge_result = await purge_all_data()
                logger.info(f"Purge completed: {purge_result}")
            except Exception as e:
                logger.error(f"Failed to purge data before restore: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to purge existing data before restore: {str(e)}",
                )

            logger.info("Purge completed, starting restore...")

            # Now restore data
            from skillberry_store.modules.object_handler import (
                get_object_handler,
                clear_object_handlers,
                initialize_object_handlers,
            )
            from skillberry_store.schemas.vmcp_schema import VmcpSchema
            from skillberry_store.schemas.vnfs_schema import VnfsSchema

            imported_counts = {
                "tools": 0,
                "snippets": 0,
                "skills": 0,
                "vmcp_servers": 0,
                "vnfs_servers": 0,
            }

            # Import tools first (with their modules)
            if "tools" in backup_data and isinstance(backup_data["tools"], list):
                tool_handler = get_object_handler("tool")
                for tool_data in backup_data["tools"]:
                    try:
                        module_content = tool_data.pop("module_content", None)
                        tool_uuid = tool_data.get("uuid")
                        module_name = tool_data.get("module_name")

                        # Save the tool metadata
                        tool_handler.write_dict(tool_data.get("uuid"), tool_data)

                        # Save the module content if present using ObjectHandler's write_file
                        if module_content and tool_uuid and module_name:
                            tool_handler.write_file(
                                tool_uuid,
                                module_name,
                                (
                                    module_content.encode("utf-8")
                                    if isinstance(module_content, str)
                                    else module_content
                                ),
                            )

                        imported_counts["tools"] += 1
                    except Exception as e:
                        logger.error(f"Failed to import tool: {e}")

            # Import snippets
            if "snippets" in backup_data and isinstance(backup_data["snippets"], list):
                snippet_handler = get_object_handler("snippet")
                for snippet_data in backup_data["snippets"]:
                    try:
                        snippet_handler.write_dict(
                            snippet_data.get("uuid"), snippet_data
                        )
                        imported_counts["snippets"] += 1
                    except Exception as e:
                        logger.error(f"Failed to import snippet: {e}")

            # Import skills (after tools and snippets)
            if "skills" in backup_data and isinstance(backup_data["skills"], list):
                skill_handler = get_object_handler("skill")
                for skill_data in backup_data["skills"]:
                    try:
                        skill_handler.write_dict(skill_data.get("uuid"), skill_data)
                        imported_counts["skills"] += 1
                    except Exception as e:
                        logger.error(f"Failed to import skill: {e}")

            # Import VMCP servers and start them if in approved state
            if "vmcp_servers" in backup_data and isinstance(
                backup_data["vmcp_servers"], list
            ):
                vmcp_handler = get_object_handler("vmcp")
                vmcp_manager = (
                    app.state.vmcp_server_manager
                    if hasattr(app.state, "vmcp_server_manager")
                    else None
                )

                for vmcp_data in backup_data["vmcp_servers"]:
                    try:
                        # Save the VMCP metadata first
                        vmcp_handler.write_dict(vmcp_data.get("uuid"), vmcp_data)

                        # Start the server if it's in approved state and we have a manager
                        if vmcp_manager and vmcp_data.get("state") == "approved":
                            try:
                                # Get tool and snippet UUIDs from the skill if present
                                tool_uuids = []
                                snippet_uuids = []
                                skill_uuid = vmcp_data.get("skill_uuid")

                                if skill_uuid:
                                    skill_handler = get_object_handler("skill")
                                    try:
                                        skill_dict = skill_handler.read_dict(skill_uuid)
                                        tool_uuids = skill_dict.get("tool_uuids", [])
                                        snippet_uuids = skill_dict.get(
                                            "snippet_uuids", []
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"Error loading skill {skill_uuid} for VMCP server: {e}"
                                        )

                                # Start the runtime server
                                server = vmcp_manager.add_server(
                                    name=vmcp_data.get("name", ""),
                                    uuid=vmcp_data.get("uuid", ""),
                                    description=vmcp_data.get("description", ""),
                                    port=vmcp_data.get("port"),
                                    tools=tool_uuids,
                                    snippets=snippet_uuids,
                                    env_id="",
                                )
                                logger.info(
                                    f"Started VMCP server '{vmcp_data.get('name')}' on port {server.port}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to start VMCP server '{vmcp_data.get('name')}': {e}"
                                )

                        imported_counts["vmcp_servers"] += 1
                    except Exception as e:
                        logger.error(f"Failed to import VMCP server: {e}")

            # Import vNFS servers and start them if in approved state
            if "vnfs_servers" in backup_data and isinstance(
                backup_data["vnfs_servers"], list
            ):
                vnfs_handler = get_object_handler("vnfs")
                vnfs_manager = (
                    app.state.vnfs_server_manager
                    if hasattr(app.state, "vnfs_server_manager")
                    else None
                )

                for vnfs_data in backup_data["vnfs_servers"]:
                    try:
                        # Save the vNFS metadata first
                        vnfs_handler.write_dict(vnfs_data.get("uuid"), vnfs_data)

                        # Start the server if it's in approved state and we have a manager
                        if vnfs_manager and vnfs_data.get("state") == "approved":
                            try:
                                # Create VnfsSchema from dict
                                vnfs_schema = VnfsSchema(**vnfs_data)
                                server = vnfs_manager.add_server(vnfs_schema)
                                logger.info(
                                    f"Started vNFS server '{vnfs_data.get('name')}' on port {server.port}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to start vNFS server '{vnfs_data.get('name')}': {e}"
                                )

                        imported_counts["vnfs_servers"] += 1
                    except Exception as e:
                        logger.error(f"Failed to import vNFS server: {e}")

            # Simulate a server reboot: reinitialise all object handlers from the
            # now-populated data directories. This rebuilds name/dict caches,
            # parent chains, description vector indexes, and the full dependency
            # graph in one shot — identical to what happens at startup.
            # Note: plugin emit_content_added events are intentionally not fired;
            # a restore is not semantically equivalent to a series of creates.
            logger.info("Reinitialising object handlers from restored data...")
            clear_object_handlers()
            initialize_object_handlers()
            logger.info("Object handlers reinitialised")

            logger.info(
                f"Restore completed successfully: {imported_counts['skills']} skills, "
                f"{imported_counts['tools']} tools, {imported_counts['snippets']} snippets, "
                f"{imported_counts['vmcp_servers']} VMCP servers, {imported_counts['vnfs_servers']} vNFS servers"
            )

            return {
                "message": "All data successfully restored from backup",
                "imported_counts": imported_counts,
                "total_imported": sum(imported_counts.values()),
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

    @app.get("/health", tags=[tags], openapi_extra={"x-cli-name": "health"})
    def health_check():
        """Health check endpoint.

        Returns:
            dict: Health status of the service.
        """
        return {"status": "healthy"}

    @app.get("/changes", tags=[tags], openapi_extra={"x-cli-name": "changes-count"})
    def get_changes_count():
        """Get the global mutation counter for detecting data changes.

        Returns a counter that increments whenever data is modified (create, update, delete).
        The UI uses this to detect when to refresh data without polling individual endpoints.

        Args:
            None.

        Returns:
            dict: Contains 'count' key with the current mutation counter value.
        """
        from skillberry_store.fast_api.changes import get as get_count

        return {"count": get_count()}

    @app.get("/health/ready", tags=[tags], openapi_extra={"x-cli-name": "health-ready"})
    def readiness_check():
        """Readiness check endpoint - verifies all description directories are initialized.

        Returns:
            dict: Readiness status with details about each directory (HTTP 200 when ready).

        Raises:
            HTTPException: 500 status when still initializing.
        """
        from skillberry_store.modules.object_handler import get_object_handler

        checks = {}

        for object_type in ["tool", "snippet", "skill", "vmcp"]:
            handler = get_object_handler(object_type)
            desc = handler.descriptions
            if desc is not None:
                dir_path = desc.descriptions_directory
                checks[f"{object_type}_descriptions"] = {
                    "path": dir_path,
                    "exists": os.path.exists(dir_path),
                }
            # else: descriptions not configured for this handler — skip check

        # Server is ready only when every configured descriptions directory exists
        all_ready = all(check["exists"] for check in checks.values())

        if not all_ready:
            raise HTTPException(
                status_code=500, detail={"status": "initializing", "checks": checks}
            )

        return {"status": "ready", "checks": checks}
