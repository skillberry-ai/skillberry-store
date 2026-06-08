"""Admin API endpoints for the Skillberry Store service."""

import logging
import shutil
import os
import httpx
import json
import zipfile
import io
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse, StreamingResponse

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
    get_vnfs_directory,
    get_vnfs_descriptions_directory,
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
            ("vnfs", get_vnfs_directory()),
            ("vnfs_descriptions", get_vnfs_descriptions_directory()),
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
                failed_dirs.append(
                    {"name": dir_name, "path": dir_path, "error": str(e)}
                )

        # Step 2.5: Clear ObjectHandler in-memory caches
        caches_cleared = False
        try:
            from skillberry_store.modules.object_handler import get_object_handler

            for object_type in ["tool", "snippet", "skill", "vmcp", "vnfs"]:
                try:
                    handler = get_object_handler(object_type)
                    # Clear dict cache
                    if handler.dict_cache:
                        handler.dict_cache.clear()
                        logger.info(f"Cleared dict cache for {object_type}")
                    # Clear name cache
                    if handler.name_cache:
                        handler.name_cache.clear()
                        logger.info(f"Cleared name cache for {object_type}")
                except Exception as e:
                    logger.warning(
                        f"Failed to clear caches for {object_type}: {str(e)}"
                    )

            caches_cleared = True
            logger.info("All ObjectHandler caches cleared")
        except Exception as e:
            logger.warning(f"Failed to clear ObjectHandler caches: {str(e)}")

        # Step 3: Reset in-memory vector indexes
        vector_indexes_reset = False
        try:
            if hasattr(app, "state"):
                # Reinitialize all description instances with empty vector indexes
                if hasattr(app.state, "descriptions"):
                    app.state.descriptions.load_index()
                    logger.info("Reset descriptions vector index")

                if hasattr(app.state, "tools_descriptions"):
                    app.state.tools_descriptions.load_index()
                    logger.info("Reset tools_descriptions vector index")

                if hasattr(app.state, "snippets_descriptions"):
                    app.state.snippets_descriptions.load_index()
                    logger.info("Reset snippets_descriptions vector index")

                if hasattr(app.state, "skills_descriptions"):
                    app.state.skills_descriptions.load_index()
                    logger.info("Reset skills_descriptions vector index")

                if hasattr(app.state, "vmcp_descriptions"):
                    app.state.vmcp_descriptions.load_index()
                    logger.info("Reset vmcp_descriptions vector index")

                if hasattr(app.state, "vnfs_descriptions"):
                    app.state.vnfs_descriptions.load_index()
                    logger.info("Reset vnfs_descriptions vector index")

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
            from skillberry_store.modules.object_handler import get_object_handler
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

            # Rebuild caches for all object types
            logger.info("Rebuilding caches after restore...")
            for object_type in ["tool", "snippet", "skill", "vmcp", "vnfs"]:
                try:
                    handler = get_object_handler(object_type)
                    # Iterate through all objects to populate caches
                    for obj_dict in handler.iter_dicts():
                        obj_uuid = obj_dict.get("uuid")
                        obj_name = obj_dict.get("name")
                        if obj_uuid and obj_name:
                            handler.update_cache(obj_uuid, new_name=obj_name)
                    logger.info(f"Rebuilt cache for {object_type}")
                except Exception as e:
                    logger.warning(f"Failed to rebuild cache for {object_type}: {e}")

            # Rebuild description indexes
            logger.info("Rebuilding description indexes after restore...")
            if hasattr(app, "state"):
                # Rebuild tools descriptions
                if hasattr(app.state, "tools_descriptions"):
                    tool_handler = get_object_handler("tool")
                    for tool_dict in tool_handler.iter_dicts():
                        if tool_dict.get("description") and tool_dict.get("uuid"):
                            try:
                                app.state.tools_descriptions.write_description(
                                    tool_dict["uuid"], tool_dict["description"]
                                )
                            except Exception as e:
                                logger.warning(f"Failed to write tool description: {e}")
                    logger.info("Rebuilt tools descriptions index")

                # Rebuild snippets descriptions
                if hasattr(app.state, "snippets_descriptions"):
                    snippet_handler = get_object_handler("snippet")
                    for snippet_dict in snippet_handler.iter_dicts():
                        if snippet_dict.get("description") and snippet_dict.get("uuid"):
                            try:
                                app.state.snippets_descriptions.write_description(
                                    snippet_dict["uuid"], snippet_dict["description"]
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to write snippet description: {e}"
                                )
                    logger.info("Rebuilt snippets descriptions index")

                # Rebuild skills descriptions
                if hasattr(app.state, "skills_descriptions"):
                    skill_handler = get_object_handler("skill")
                    for skill_dict in skill_handler.iter_dicts():
                        if skill_dict.get("description") and skill_dict.get("uuid"):
                            try:
                                app.state.skills_descriptions.write_description(
                                    skill_dict["uuid"], skill_dict["description"]
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to write skill description: {e}"
                                )
                    logger.info("Rebuilt skills descriptions index")

                # Rebuild VMCP descriptions
                if hasattr(app.state, "vmcp_descriptions"):
                    vmcp_handler = get_object_handler("vmcp")
                    for vmcp_dict in vmcp_handler.iter_dicts():
                        if vmcp_dict.get("description") and vmcp_dict.get("uuid"):
                            try:
                                app.state.vmcp_descriptions.write_description(
                                    vmcp_dict["uuid"], vmcp_dict["description"]
                                )
                            except Exception as e:
                                logger.warning(f"Failed to write VMCP description: {e}")
                    logger.info("Rebuilt VMCP descriptions index")

                # Rebuild vNFS descriptions
                if hasattr(app.state, "vnfs_descriptions"):
                    vnfs_handler = get_object_handler("vnfs")
                    for vnfs_dict in vnfs_handler.iter_dicts():
                        if vnfs_dict.get("description") and vnfs_dict.get("uuid"):
                            try:
                                app.state.vnfs_descriptions.write_description(
                                    vnfs_dict["uuid"], vnfs_dict["description"]
                                )
                            except Exception as e:
                                logger.warning(f"Failed to write vNFS description: {e}")
                    logger.info("Rebuilt vNFS descriptions index")

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
        """Return the global mutation counter. Used by the UI to detect data changes."""
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
        checks = {}

        # Check all known description objects in app.state
        description_attrs = [
            "tools_descriptions",
            "snippets_descriptions",
            "skills_descriptions",
            "vmcp_descriptions",
        ]

        for attr_name in description_attrs:
            desc_obj = getattr(app.state, attr_name, None)
            if desc_obj and hasattr(desc_obj, "descriptions_directory"):
                dir_path = desc_obj.descriptions_directory
                checks[attr_name] = {
                    "path": dir_path,
                    "exists": os.path.exists(dir_path),
                }
            else:
                checks[attr_name] = {"path": None, "exists": False}

        # Server is ready if all checks pass
        all_ready = all(check["exists"] for check in checks.values())

        if not all_ready:
            raise HTTPException(
                status_code=500, detail={"status": "initializing", "checks": checks}
            )

        return {"status": "ready", "checks": checks}
