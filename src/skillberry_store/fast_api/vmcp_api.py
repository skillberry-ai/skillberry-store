"""Virtual MCP Server API endpoints for the Skillberry Store service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import Counter, Histogram

from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.vmcp_schema import VmcpSchema
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys
from skillberry_store.services.vmcp_service import VmcpService

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description

logger = logging.getLogger(__name__)

prom_prefix = "sts_fastapi_vmcp_"
create_vmcp_counter = Counter(
    f"{prom_prefix}create_vmcp_counter", "Count number of vmcp create operations"
)
list_vmcp_counter = Counter(
    f"{prom_prefix}list_vmcp_counter", "Count number of vmcp list operations"
)
get_vmcp_counter = Counter(
    f"{prom_prefix}get_vmcp_counter", "Count number of vmcp get operations"
)
delete_vmcp_counter = Counter(
    f"{prom_prefix}delete_vmcp_counter", "Count number of vmcp delete operations"
)
update_vmcp_counter = Counter(
    f"{prom_prefix}update_vmcp_counter", "Count number of vmcp update operations"
)
search_vmcp_counter = Counter(
    f"{prom_prefix}search_vmcp_counter", "Count number of vmcp search operations"
)
invoke_vmcp_tool_counter = Counter(
    f"{prom_prefix}invoke_vmcp_tool_counter",
    "Count number of vmcp tool invoke operations",
    ["server_name", "tool_name"],
)
invoke_successfully_vmcp_tool_counter = Counter(
    f"{prom_prefix}invoke_successfully_vmcp_tool_counter",
    "Count number of vmcp tool invoked successfully operations",
    ["server_name", "tool_name"],
)
invoke_successfully_vmcp_tool_latency = Histogram(
    f"{prom_prefix}invoke_successfully_vmcp_tool_latency",
    "Histogram of invoke vmcp tool successfully latencies",
    ["server_name", "tool_name"],
)


def register_vmcp_api(
    app: FastAPI,
    sts_url: str,
    tags: str = "vmcp_servers",
    vmcp_descriptions: Optional[Description] = None,
    service: Optional[VmcpService] = None,
):
    if service is None:
        from skillberry_store.modules.object_handler import get_object_handler
        from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager

        service = VmcpService(
            get_object_handler("vmcp"),
            VirtualMcpServerManager(sts_url=sts_url, app=app),
            get_object_handler("skill"),
            vmcp_descriptions,
        )
    app.state.vmcp_server_manager = service.server_manager

    def _extract_env_id(request: Request) -> str:
        ctx = unflatten_keys(dict(request.headers)).get(SKILLBERRY_CONTEXT.lower())
        return ctx.get("env_id") if ctx else ""

    @app.post(
        "/vmcp_servers/",
        tags=[tags],
        openapi_extra={"x-cli-name": "create-vmcp-server"},
    )
    def create_vmcp_server(vmcp: Annotated[VmcpSchema, Query()], request: Request):
        logger.info(f"Request to create vmcp server: {vmcp.name}")
        create_vmcp_counter.inc()
        try:
            result = service.create(vmcp.to_dict(), env_id=_extract_env_id(request))
            return {
                "message": f"VMCP server '{result['name']}' created successfully.",
                "name": result["name"],
                "uuid": result["uuid"],
                "port": result["port"],
            }
        except ValueError as e:
            error_msg = str(e)
            if "already exists" in error_msg:
                raise HTTPException(status_code=409, detail=error_msg)
            if "port" in error_msg.lower() and (
                "not available" in error_msg.lower()
                or "already in use" in error_msg.lower()
                or "in use" in error_msg.lower()
            ):
                raise HTTPException(
                    status_code=409, detail=f"Port conflict: {error_msg}"
                )
            raise HTTPException(status_code=500, detail=error_msg)
        except Exception as e:
            logger.error(f"Error creating vmcp server '{vmcp.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating vmcp server: {str(e)}"
            )

    @app.get(
        "/vmcp_servers/", tags=[tags], openapi_extra={"x-cli-name": "list-vmcp-servers"}
    )
    def list_vmcp_servers():
        logger.info("Request to list vmcp servers")
        list_vmcp_counter.inc()
        try:
            return service.list_all()
        except Exception as e:
            logger.error(f"Error listing vmcp servers: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing vmcp servers: {str(e)}"
            )

    @app.get(
        "/vmcp_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "get-vmcp-server"},
    )
    def get_vmcp_server(uuid_or_name: str):
        logger.info(f"Request to get vmcp server: {uuid_or_name}")
        get_vmcp_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving vmcp server: {str(e)}"
            )

    @app.delete(
        "/vmcp_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-vmcp-server"},
    )
    def delete_vmcp_server(uuid_or_name: str):
        logger.info(f"Request to delete vmcp server: {uuid_or_name}")
        delete_vmcp_counter.inc()
        try:
            service.delete(uuid_or_name)
            return {"message": f"VMCP server '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting vmcp server: {str(e)}"
            )

    @app.put(
        "/vmcp_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-vmcp-server"},
    )
    def update_vmcp_server(
        uuid_or_name: str, vmcp: Annotated[VmcpSchema, Query()], request: Request
    ):
        logger.info(f"Request to update vmcp server: {uuid_or_name}")
        update_vmcp_counter.inc()
        try:
            result = service.update(
                uuid_or_name, vmcp.to_dict(), env_id=_extract_env_id(request)
            )
            return {
                "message": f"VMCP server '{result.get('name')}' updated successfully.",
                "port": result["port"],
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating vmcp server: {str(e)}"
            )

    @app.post(
        "/vmcp_servers/{uuid_or_name}/start",
        tags=[tags],
        openapi_extra={"x-cli-name": "start-vmcp-server"},
    )
    def start_vmcp_server(uuid_or_name: str, request: Request):
        """Start or restart a virtual MCP server."""
        logger.info(f"Request to start vmcp server: {uuid_or_name}")
        try:
            vmcp_uuid = service._resolve_uuid(uuid_or_name)
            vmcp_data = service.handler.read_dict(vmcp_uuid)
            server_name = vmcp_data.get("name", "")
            server_uuid = vmcp_data.get("uuid", "")
            try:
                existing = service.server_manager.get_server(server_name, server_uuid)
                if existing:
                    return {
                        "message": f"VMCP server '{server_name}' is already running.",
                        "port": existing.port,
                    }
            except Exception:
                pass
            env_id = _extract_env_id(request)
            tool_uuids, snippet_uuids = service._resolve_skill_uuids(
                vmcp_data.get("skill_uuid")
            )
            server = service.server_manager.add_server(
                name=server_name,
                uuid=server_uuid,
                description=vmcp_data.get("description", ""),
                port=vmcp_data.get("port"),
                tools=tool_uuids,
                snippets=snippet_uuids,
                env_id=env_id,
            )
            logger.info(f"VMCP server '{server_name}' started on port {server.port}")
            return {
                "message": f"VMCP server '{server_name}' started successfully.",
                "port": server.port,
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error starting vmcp server: {str(e)}"
            )

    @app.get(
        "/search/vmcp_servers",
        tags=[tags],
        openapi_extra={"x-cli-name": "search-vmcp-servers"},
    )
    def search_vmcp_servers(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
        include_simulation: bool = False,
    ):
        logger.info(f"Request to search vmcp servers for: {search_term}")
        search_vmcp_counter.inc()
        if not vmcp_descriptions:
            raise HTTPException(
                status_code=503, detail="VMCP server search is not available"
            )
        try:
            matched_entities = vmcp_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )
            filtered = [
                m
                for m in matched_entities
                if float(m.get("similarity_score", 0)) <= similarity_threshold
            ]
            to_filter = []
            for m in filtered:
                vmcp_uuid = m.get("filename") or m.get("name")
                if not vmcp_uuid:
                    continue
                try:
                    d = service.handler.read_dict(vmcp_uuid)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    to_filter.append(d)
                except Exception as exc:
                    logger.warning(f"Could not load vmcp '{vmcp_uuid}': {exc}")
            result_items = apply_search_filters(
                to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            if not include_simulation:
                from skillberry_store.fast_api.search_filters import exclude_simulation
                result_items = exclude_simulation(result_items)
            result_items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [
                {
                    "filename": s.get("name", ""),
                    "similarity_score": s.get("similarity_score", 0.0),
                }
                for s in result_items
                if s.get("name")
            ]
        except Exception as e:
            logger.error(f"Error searching vmcp servers: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching vmcp servers: {str(e)}"
            )
