"""Virtual NFS Server API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import Counter

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager
from skillberry_store.schemas.vnfs_schema import VnfsSchema
from skillberry_store.tools.configure import (
    get_vnfs_directory,
    get_vnfs_descriptions_directory,
)
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys
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
    vnfs_directory = get_vnfs_directory()
    vnfs_handler = FileHandler(vnfs_directory)

    vnfs_server_manager = VirtualNfsServerManager(sts_url=sts_url, app=app)
    app.state.vnfs_server_manager = vnfs_server_manager

    @app.post("/vnfs_servers/", tags=[tags])
    def create_vnfs_server(vnfs: Annotated[VnfsSchema, Query()], request: Request):
        """Create and start a new vNFS endpoint."""
        logger.info(f"Request to create vnfs server: {vnfs.name}")
        create_vnfs_counter.inc()

        if not vnfs.uuid:
            vnfs.uuid = str(uuid.uuid4())

        current_time = datetime.now(timezone.utc).isoformat()
        vnfs.created_at = current_time
        vnfs.modified_at = current_time

        vnfs_filename = f"{vnfs.name}.json"
        if vnfs_filename in vnfs_handler.list_files():
            raise HTTPException(
                status_code=409, detail=f"vNFS server '{vnfs.name}' already exists."
            )

        try:
            server = vnfs_server_manager.add_server(vnfs)
            vnfs.port = server.port

            vnfs_handler.write_file_content(vnfs_filename, json.dumps(vnfs.to_dict(), indent=4))

            if vnfs_descriptions and vnfs.description:
                vnfs_descriptions.write_description(vnfs.name, vnfs.description)

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
            raise HTTPException(status_code=500, detail=f"Error creating vNFS server: {exc}")

    @app.get("/vnfs_servers/", tags=[tags])
    def list_vnfs_servers():
        """List all vNFS endpoints."""
        logger.info("Request to list vnfs servers")
        list_vnfs_counter.inc()

        try:
            all_files = vnfs_handler.list_files()
            servers_list = []
            for filename in all_files:
                if not filename.endswith(".json"):
                    continue
                server_name = filename[:-5]
                try:
                    content = vnfs_handler.read_file(filename, raw_content=True)
                    if not isinstance(content, str):
                        continue
                    data = json.loads(content)

                    runtime_server = vnfs_server_manager.get_server(server_name)
                    info = {
                        "uuid": data.get("uuid"),
                        "name": data.get("name"),
                        "description": data.get("description"),
                        "version": data.get("version"),
                        "state": data.get("state"),
                        "tags": data.get("tags", []),
                        "port": data.get("port"),
                        "skill_uuid": data.get("skill_uuid"),
                        "protocol": data.get("protocol", "webdav"),
                        "modified_at": data.get("modified_at", ""),
                        "running": runtime_server is not None and runtime_server.running,
                        "export_path": (
                            str(runtime_server.export_path) if runtime_server else None
                        ),
                    }
                    servers_list.append(info)
                except Exception as exc:
                    logger.warning(f"Error loading vnfs server '{server_name}': {exc}")

            servers_list.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            servers_dict = {s["name"]: s for s in servers_list}
            return {"virtual_nfs_servers": servers_dict}
        except Exception as exc:
            logger.error(f"Error listing vnfs servers: {exc}")
            raise HTTPException(status_code=500, detail=f"Error listing vNFS servers: {exc}")

    @app.get("/vnfs_servers/{name}", tags=[tags])
    def get_vnfs_server(name: str):
        """Get a specific vNFS endpoint by name."""
        logger.info(f"Request to get vnfs server: {name}")
        get_vnfs_counter.inc()

        try:
            content = vnfs_handler.read_file(f"{name}.json", raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(status_code=500, detail="Invalid content type")
            data = json.loads(content)

            runtime_server = vnfs_server_manager.get_server(name)
            data["running"] = runtime_server is not None and runtime_server.running
            data["export_path"] = (
                str(runtime_server.export_path) if runtime_server else None
            )
            return data
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error retrieving vnfs server '{name}': {exc}")
            raise HTTPException(status_code=500, detail=f"Error retrieving vNFS server: {exc}")

    @app.delete("/vnfs_servers/{name}", tags=[tags])
    def delete_vnfs_server(name: str):
        """Stop and delete a vNFS endpoint."""
        logger.info(f"Request to delete vnfs server: {name}")
        delete_vnfs_counter.inc()

        try:
            vnfs_server_manager.remove_server(name)
            vnfs_handler.delete_file(f"{name}.json")

            if vnfs_descriptions:
                try:
                    vnfs_descriptions.delete_description(name)
                except Exception as exc:
                    logger.warning(f"Could not delete vnfs description for '{name}': {exc}")

            return {"message": f"vNFS server '{name}' deleted successfully."}
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error deleting vnfs server '{name}': {exc}")
            raise HTTPException(status_code=500, detail=f"Error deleting vNFS server: {exc}")

    @app.put("/vnfs_servers/{name}", tags=[tags])
    def update_vnfs_server(
        name: str, vnfs: Annotated[VnfsSchema, Query()], request: Request
    ):
        """Update metadata and restart a vNFS endpoint."""
        logger.info(f"Request to update vnfs server: {name}")
        update_vnfs_counter.inc()

        vnfs_filename = f"{name}.json"
        if vnfs_filename not in vnfs_handler.list_files():
            raise HTTPException(status_code=404, detail=f"vNFS server '{name}' not found.")

        try:
            vnfs.modified_at = datetime.now(timezone.utc).isoformat()
            vnfs_server_manager.remove_server(name)
            server = vnfs_server_manager.add_server(vnfs)
            vnfs.port = server.port

            vnfs_handler.write_file_content(vnfs_filename, json.dumps(vnfs.to_dict(), indent=4))

            return {
                "message": f"vNFS server '{name}' updated successfully.",
                "port": server.port,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error updating vnfs server '{name}': {exc}")
            raise HTTPException(status_code=500, detail=f"Error updating vNFS server: {exc}")

    @app.post("/vnfs_servers/{name}/start", tags=[tags])
    def start_vnfs_server(name: str, request: Request):
        """Start or restart a vNFS endpoint."""
        logger.info(f"Request to start vnfs server: {name}")

        try:
            existing = vnfs_server_manager.get_server(name)
            if existing and existing.running:
                return {
                    "message": f"vNFS server '{name}' is already running.",
                    "port": existing.port,
                }

            content = vnfs_handler.read_file(f"{name}.json", raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(status_code=500, detail="Invalid content type")
            data = json.loads(content)

            from skillberry_store.schemas.vnfs_schema import VnfsSchema as _VnfsSchema

            schema = _VnfsSchema.from_dict(data)
            server = vnfs_server_manager.add_server(schema)

            return {
                "message": f"vNFS server '{name}' started successfully.",
                "port": server.port,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error starting vnfs server '{name}': {exc}")
            raise HTTPException(status_code=500, detail=f"Error starting vNFS server: {exc}")

    @app.get("/search/vnfs_servers", tags=[tags])
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
            filtered = [m for m in matched if m["similarity_score"] <= similarity_threshold]

            servers_to_filter = []
            for m in filtered:
                vnfs_name = m.get("filename") or m.get("name")
                if not vnfs_name:
                    continue
                try:
                    content = vnfs_handler.read_file(f"{vnfs_name}.json", raw_content=True)
                    if isinstance(content, str):
                        d = json.loads(content)
                        d["similarity_score"] = m.get("similarity_score", 0.0)
                        servers_to_filter.append(d)
                except Exception as exc:
                    logger.warning(f"Could not load vnfs server '{vnfs_name}': {exc}")

            filtered_servers = apply_search_filters(
                servers_to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            filtered_servers.sort(
                key=lambda x: x.get("modified_at", ""), reverse=True
            )

            return [
                {"filename": s.get("name", ""), "similarity_score": s.get("similarity_score", 0.0)}
                for s in filtered_servers
                if s.get("name")
            ]
        except Exception as exc:
            logger.error(f"Error searching vnfs servers: {exc}")
            raise HTTPException(status_code=500, detail=f"Error searching vNFS servers: {exc}")
