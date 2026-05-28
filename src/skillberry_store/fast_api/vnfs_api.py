"""Virtual NFS Server API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import Counter

from skillberry_store.modules.object_handler import get_object_handler
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager
from skillberry_store.schemas.vnfs_schema import VnfsSchema
from skillberry_store.tools.configure import (
    get_vnfs_directory,
    get_vnfs_descriptions_directory,
)
from skillberry_store.utils.utils import (
    SKILLBERRY_CONTEXT,
    unflatten_keys,
    generate_or_validate_uuid,
)
from skillberry_store.fast_api.search_filters import apply_search_filters

logger = logging.getLogger(__name__)

prom_prefix = "sts_fastapi_vnfs_"
create_vnfs_counter = Counter(f"{prom_prefix}create_counter", "vNFS create operations")
list_vnfs_counter = Counter(f"{prom_prefix}list_counter", "vNFS list operations")
get_vnfs_counter = Counter(f"{prom_prefix}get_counter", "vNFS get operations")
delete_vnfs_counter = Counter(f"{prom_prefix}delete_counter", "vNFS delete operations")
update_vnfs_counter = Counter(f"{prom_prefix}update_counter", "vNFS update operations")
search_vnfs_counter = Counter(f"{prom_prefix}search_counter", "vNFS search operations")


def register_vnfs_api(
    app: FastAPI,
    sts_url: str,
    tags: str = "vnfs_servers",
    vnfs_descriptions: Optional[Description] = None,
):
    """Register virtual NFS server API endpoints with the FastAPI application."""
    vnfs_handler = get_object_handler("vnfs")

    vnfs_server_manager = VirtualNfsServerManager(sts_url=sts_url, app=app)
    app.state.vnfs_server_manager = vnfs_server_manager

    @app.post("/vnfs_servers/", tags=[tags], openapi_extra={"x-cli-name": "create-vnfs-server"})
    def create_vnfs_server(vnfs: Annotated[VnfsSchema, Query()], request: Request):
        """Create and start a new vNFS endpoint."""
        logger.info(f"Request to create vnfs server: {vnfs.name}")
        create_vnfs_counter.inc()

        vnfs.uuid = generate_or_validate_uuid(vnfs.uuid)
        logger.info(f"UUID for vNFS server '{vnfs.name}': {vnfs.uuid}")

        current_time = datetime.now(timezone.utc).isoformat()
        vnfs.created_at = current_time
        vnfs.modified_at = current_time

        # Check if vnfs server with this UUID already exists
        if vnfs_handler.object_exists(vnfs.uuid):
            raise HTTPException(
                status_code=409,
                detail=f"vNFS server with UUID '{vnfs.uuid}' already exists.",
            )

        # Determine correct parent for this VNFS server becoming HEAD
        if vnfs.name:
            vnfs.parent = vnfs_handler.get_cache_parent_for_head(vnfs.uuid, vnfs.name)
            logger.info(
                f"Setting parent for VNFS server '{vnfs.name}' to {vnfs.parent}"
            )

        try:
            server = vnfs_server_manager.add_server(vnfs)
            vnfs.port = server.port

            # Save using ObjectHandler with UUID
            vnfs_handler.write_dict(vnfs.uuid, vnfs.to_dict())

            # Update cache after create
            if vnfs.name:
                vnfs_handler.update_cache(vnfs.uuid, new_name=vnfs.name)

            # Write description indexed by UUID
            if vnfs_descriptions and vnfs.description:
                vnfs_descriptions.write_description(vnfs.uuid, vnfs.description)
                logger.info(f"vNFS server description saved for UUID: {vnfs.uuid}")

            logger.info(f"vNFS server '{vnfs.name}' created on port {server.port}")
            return {
                "message": f"vNFS server '{vnfs.name}' created successfully.",
                "name": vnfs.name,
                "uuid": vnfs.uuid,
                "port": server.port,
            }
        except HTTPException:
            raise
        except ValueError as exc:
            if "not available" in str(exc):
                raise HTTPException(status_code=409, detail=str(exc))
            raise HTTPException(status_code=500, detail=str(exc))
        except Exception as exc:
            logger.error(f"Error creating vnfs server '{vnfs.name}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error creating vNFS server: {exc}"
            )

    @app.get("/vnfs_servers/", tags=[tags], openapi_extra={"x-cli-name": "list-vnfs-servers"})
    def list_vnfs_servers():
        """List all vNFS endpoints."""
        logger.info("Request to list vnfs servers")
        list_vnfs_counter.inc()

        try:
            # Get all VNFS objects using ObjectHandler
            vnfs_resources = vnfs_handler.list_all_dicts()

            servers_list = []
            for vnfs_data in vnfs_resources:
                server_name = vnfs_data.get("name")
                server_uuid = vnfs_data.get("uuid")
                try:
                    # Get runtime server using name and UUID
                    runtime_server = None
                    try:
                        runtime_server = vnfs_server_manager.get_server(
                            server_name or "", server_uuid or ""
                        )
                    except Exception:
                        pass  # Server not running, which is fine

                    info = {
                        "uuid": vnfs_data.get("uuid"),
                        "name": vnfs_data.get("name"),
                        "description": vnfs_data.get("description"),
                        "version": vnfs_data.get("version"),
                        "state": vnfs_data.get("state"),
                        "tags": vnfs_data.get("tags", []),
                        "port": vnfs_data.get("port"),
                        "skill_uuid": vnfs_data.get("skill_uuid"),
                        "protocol": vnfs_data.get("protocol", "webdav"),
                        "modified_at": vnfs_data.get("modified_at", ""),
                        "running": runtime_server is not None
                        and runtime_server.running,
                        "export_path": (
                            str(runtime_server.export_path) if runtime_server else None
                        ),
                    }
                    servers_list.append(info)
                except Exception as exc:
                    logger.warning(f"Error loading vnfs server '{server_name}': {exc}")

            servers_list.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            # Convert to dict with server UUIDs as keys to avoid duplications
            servers_dict = {s["uuid"]: s for s in servers_list}
            return {"virtual_nfs_servers": servers_dict}
        except Exception as exc:
            logger.error(f"Error listing vnfs servers: {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error listing vNFS servers: {exc}"
            )

    @app.get("/vnfs_servers/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "get-vnfs-server"})
    def get_vnfs_server(uuid_or_name: str):
        """Get a specific vNFS endpoint by UUID or name."""
        logger.info(f"Request to get vnfs server: {uuid_or_name}")
        get_vnfs_counter.inc()

        try:
            # Resolve UUID or name to UUID and read dict
            vnfs_uuid = vnfs_handler.resolve_to_uuid_or_error(uuid_or_name)
            vnfs_dict = vnfs_handler.read_dict(vnfs_uuid)
            server_name = vnfs_dict.get("name")
            server_uuid = vnfs_dict.get("uuid")

            # Get runtime details from manager
            try:
                runtime_server = vnfs_server_manager.get_server(
                    server_name or "", server_uuid or ""
                )
                vnfs_dict["running"] = (
                    runtime_server is not None and runtime_server.running
                )
                vnfs_dict["export_path"] = (
                    str(runtime_server.export_path) if runtime_server else None
                )
            except Exception:
                vnfs_dict["running"] = False
                vnfs_dict["export_path"] = None

            logger.info(f"Retrieved vnfs server: {uuid_or_name}")
            return vnfs_dict
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error retrieving vnfs server '{uuid_or_name}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving vNFS server: {exc}"
            )

    @app.delete("/vnfs_servers/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "delete-vnfs-server"})
    def delete_vnfs_server(uuid_or_name: str):
        """Stop and delete a vNFS endpoint by UUID or name."""
        logger.info(f"Request to delete vnfs server: {uuid_or_name}")
        delete_vnfs_counter.inc()

        try:
            # Resolve UUID or name to UUID and read manifest
            server_uuid = vnfs_handler.resolve_to_uuid_or_error(uuid_or_name)
            vnfs_dict = vnfs_handler.read_dict(server_uuid)
            server_name = vnfs_dict.get("name")
            server_parent = vnfs_dict.get("parent")

            # Stop and remove the runtime server
            try:
                vnfs_server_manager.remove_server(server_name or "", server_uuid or "")
                logger.info(f"Stopped runtime server: {server_name}_{server_uuid}")
            except Exception as e:
                logger.warning(f"Could not stop runtime server: {e}")

            # Delete persistent data using ObjectHandler
            vnfs_handler.delete_object(server_uuid)

            # Update cache after delete
            if server_name and server_uuid:
                vnfs_handler.update_cache(
                    server_uuid,
                    new_name=None,
                    old_name=server_name,
                    old_parent=server_parent,
                )

            # Delete the description (indexed by UUID)
            if vnfs_descriptions:
                try:
                    vnfs_descriptions.delete_description(server_uuid or "")
                    logger.info(
                        f"vNFS server description deleted for UUID: {server_uuid}"
                    )
                except Exception as exc:
                    logger.warning(
                        f"Could not delete vnfs description for UUID '{server_uuid}': {exc}"
                    )

            logger.info(f"vNFS server '{id}' deleted successfully")
            return {"message": f"vNFS server '{id}' deleted successfully."}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error deleting vnfs server '{id}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting vNFS server: {exc}"
            )

    @app.put("/vnfs_servers/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "update-vnfs-server"})
    def update_vnfs_server(
        uuid_or_name: str, vnfs: Annotated[VnfsSchema, Query()], request: Request
    ):
        """Update metadata and restart a vNFS endpoint."""
        logger.info(f"Request to update vnfs server: {uuid_or_name}")
        update_vnfs_counter.inc()

        try:
            # Resolve UUID or name to UUID and read current data
            vnfs_uuid = vnfs_handler.resolve_to_uuid_or_error(uuid_or_name)
            existing_vnfs = vnfs_handler.read_dict(vnfs_uuid)
            old_name = existing_vnfs.get("name")
            old_parent = existing_vnfs.get("parent")
            server_uuid = existing_vnfs.get("uuid")

            # Update modified timestamp
            vnfs.modified_at = datetime.now(timezone.utc).isoformat()

            # Preserve UUID if not provided in update
            if not vnfs.uuid:
                vnfs.uuid = server_uuid

            # Determine new name and correct parent
            new_name = vnfs.name
            if new_name:
                # Determine correct parent for this VNFS server becoming HEAD
                vnfs.parent = vnfs_handler.get_cache_parent_for_head(
                    vnfs.uuid or "", new_name
                )
                logger.info(
                    f"Setting parent for VNFS server '{new_name}' to {vnfs.parent}"
                )

            # Stop the old runtime server
            try:
                vnfs_server_manager.remove_server(old_name or "", server_uuid or "")
                logger.info(f"Stopped old runtime server: {old_name}_{server_uuid}")
            except Exception as e:
                logger.warning(f"Could not stop old runtime server: {e}")

            # Start new runtime server
            server = vnfs_server_manager.add_server(vnfs)
            vnfs.port = server.port

            # Update persistent data using ObjectHandler
            vnfs_handler.write_dict(vnfs.uuid or "", vnfs.to_dict())

            # Update cache after update
            if vnfs.name and old_name:
                vnfs_handler.update_cache(
                    vnfs.uuid or "",
                    new_name=vnfs.name,
                    old_name=old_name,
                    old_parent=old_parent,
                )

            # Update description indexed by UUID
            if vnfs_descriptions and vnfs.description and vnfs.uuid:
                vnfs_descriptions.write_description(vnfs.uuid, vnfs.description)
                logger.info(f"vNFS server description updated for UUID: {vnfs.uuid}")

            logger.info(
                f"vNFS server '{vnfs.name}' updated successfully on port {server.port}"
            )
            return {
                "message": f"vNFS server '{vnfs.name}' updated successfully.",
                "port": server.port,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error updating vnfs server '{id}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error updating vNFS server: {exc}"
            )

    @app.post("/vnfs_servers/{uuid_or_name}/start", tags=[tags], openapi_extra={"x-cli-name": "start-vnfs-server"})
    def start_vnfs_server(uuid_or_name: str, request: Request):
        """Start or restart a vNFS endpoint."""
        logger.info(f"Request to start vnfs server: {uuid_or_name}")

        try:
            # Resolve UUID or name to UUID and read dict
            vnfs_uuid = vnfs_handler.resolve_to_uuid_or_error(uuid_or_name)
            vnfs_data = vnfs_handler.read_dict(vnfs_uuid)
            server_name = vnfs_data.get("name", "")
            server_uuid = vnfs_data.get("uuid", "")

            # Check if server already running
            try:
                existing_server = vnfs_server_manager.get_server(
                    server_name, server_uuid
                )
                if existing_server and existing_server.running:
                    return {
                        "message": f"vNFS server '{server_name}' is already running.",
                        "port": existing_server.port,
                    }
            except Exception:
                pass  # Server not running, proceed to start it

            from skillberry_store.schemas.vnfs_schema import VnfsSchema as _VnfsSchema

            schema = _VnfsSchema.from_dict(vnfs_data)
            server = vnfs_server_manager.add_server(schema)

            logger.info(
                f"vNFS server '{server_name}' started successfully on port {server.port}"
            )
            return {
                "message": f"vNFS server '{server_name}' started successfully.",
                "port": server.port,
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error starting vnfs server '{id}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error starting vNFS server: {exc}"
            )

    @app.get("/search/vnfs_servers", tags=[tags], openapi_extra={"x-cli-name": "search-vnfs-servers"})
    def search_vnfs_servers(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        """Semantic search for vNFS endpoints by description."""
        logger.info(f"Request to search vnfs servers for term: {search_term}")
        search_vnfs_counter.inc()

        if not vnfs_descriptions:
            raise HTTPException(
                status_code=503,
                detail="vNFS server search is not available — descriptions not initialized",
            )

        try:
            matched = vnfs_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )
            filtered = [
                m for m in matched if m["similarity_score"] <= similarity_threshold
            ]

            servers_to_filter = []
            for m in filtered:
                # The filename in matched entity is the UUID (since we index by UUID)
                vnfs_uuid = m.get("filename") or m.get("name")
                if not vnfs_uuid:
                    logger.warning(
                        f"Matched entity missing 'filename' or 'name' field: {m}"
                    )
                    continue
                try:
                    # Read dict by UUID
                    vnfs_dict = vnfs_handler.read_dict(vnfs_uuid)
                    vnfs_dict["similarity_score"] = m.get("similarity_score", 0.0)
                    servers_to_filter.append(vnfs_dict)
                except Exception as exc:
                    logger.warning(
                        f"Could not load vnfs server with UUID '{vnfs_uuid}': {exc}"
                    )

            filtered_servers = apply_search_filters(
                servers_to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            filtered_servers.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            return [
                {
                    "filename": s.get("name", ""),
                    "similarity_score": s.get("similarity_score", 0.0),
                }
                for s in filtered_servers
                if s.get("name")
            ]
        except Exception as exc:
            logger.error(f"Error searching vnfs servers: {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error searching vNFS servers: {exc}"
            )
