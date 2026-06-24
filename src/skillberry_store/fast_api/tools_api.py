"""Tools API endpoints for the Skillberry Store service."""

from __future__ import annotations

import logging
import time
import traceback
from typing import Optional, Annotated, Dict, Any, List
from fastapi import FastAPI, HTTPException, File, UploadFile, Query, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram

from skillberry_store.plugins.events import (
    emit_content_added,
    emit_content_updated,
    emit_content_deleted,
)
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.tool_schema import ToolSchema
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys
from skillberry_store.services.exceptions import ObjectAlreadyExistsError
from skillberry_store.services.tools_service import ToolsService

logger = logging.getLogger(__name__)


# observability - metrics
prom_prefix = "sts_fastapi_tools_"
create_tool_counter = Counter(
    f"{prom_prefix}create_tool_counter", "Count number of tool create operations"
)
list_tools_counter = Counter(
    f"{prom_prefix}list_tools_counter", "Count number of tool list operations"
)
get_tool_counter = Counter(
    f"{prom_prefix}get_tool_counter", "Count number of tool get operations"
)
get_tool_module_counter = Counter(
    f"{prom_prefix}get_tool_module_counter",
    "Count number of tool module get operations",
)
delete_tool_counter = Counter(
    f"{prom_prefix}delete_tool_counter", "Count number of tool delete operations"
)
update_tool_counter = Counter(
    f"{prom_prefix}update_tool_counter", "Count number of tool update operations"
)
execute_tool_counter = Counter(
    f"{prom_prefix}execute_tool_counter",
    "Count number of tool execute operations",
    ["name"],
)
execute_successfully_tool_counter = Counter(
    f"{prom_prefix}execute_successfully_tool_counter",
    "Count number of tool executed successfully operations",
    ["name"],
)
execute_successfully_tool_latency = Histogram(
    f"{prom_prefix}execute_successfully_tool_latency",
    "Histogram of execute tool successfully latencies",
    ["name"],
)
search_tools_counter = Counter(
    f"{prom_prefix}search_tools_counter", "Count number of tool search operations"
)
add_tool_from_python_counter = Counter(
    f"{prom_prefix}add_tool_from_python_counter",
    "Count number of tool add from Python operations",
)


def register_tools_api(
    app: FastAPI,
    tags: str = "tools",
    service: Optional[ToolsService] = None,
):
    """Register all tools-related API endpoints with the FastAPI application.

    This function sets up all REST API endpoints for managing tools including
    create, read, update, delete, execute, and search operations.

    Args:
        app: The FastAPI application instance to register routes with.
        tags: OpenAPI tag for grouping these endpoints (default: "tools").
        service: Optional ToolsService instance. When ``None``, the singleton
            from :func:`skillberry_store.services.registry.get_service` is used.

    Returns:
        None. Endpoints are registered directly on the app instance.
    """
    if service is None:
        from skillberry_store.services.registry import get_service

        service = get_service("tool")
    assert service is not None  # narrowed for type checker

    @app.post("/tools/", tags=[tags], openapi_extra={"x-cli-name": "create-tool"})
    async def create_tool(
        tool: Annotated[ToolSchema, Query()],
        module: UploadFile = File(...),
    ) -> Dict[str, Any]:
        """Create a new tool with its module file.

        Creates a new tool entry in the store along with its associated Python module file.
        The tool metadata is validated against the ToolSchema and stored as a manifest.

        Args:
            tool: Tool metadata conforming to ToolSchema (name, description, params, etc.).
            module: Python module file to upload for the tool.

        Returns:
            dict: Contains success message, tool name, UUID, and module_name.

        Raises:
            HTTPException: 409 if tool already exists, 500 for other errors.
        """
        logger.info(f"Request to create tool: {tool.name}")
        create_tool_counter.inc()
        try:
            file_content = await module.read()
            module_filename = module.filename if module.filename else f"{tool.name}.py"
            result = service.create(
                tool.to_dict(),
                module_content=file_content,
                module_filename=module_filename,
            )
            emit_content_added("tool", result["uuid"])
            return {
                "message": f"Tool '{result['name']}' created successfully.",
                "name": result["name"],
                "uuid": result["uuid"],
                "module_name": result["module_name"],
            }
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating tool '{tool.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating tool: {str(e)}"
            )

    @app.get("/tools/", tags=[tags], openapi_extra={"x-cli-name": "list-tools"})
    def list_tools() -> List[Dict[str, Any]]:
        """List all tools in the store.

        Retrieves metadata for all tools currently stored in the system.

        Args:
            None.

        Returns:
            list: List of dictionaries, each containing tool metadata (name, uuid, description, etc.).

        Raises:
            HTTPException: 500 if listing fails.
        """
        logger.info("Request to list tools")
        list_tools_counter.inc()
        try:
            return service.list_all()
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Error listing tools: {e}\n{error_traceback}")
            raise HTTPException(
                status_code=500,
                detail=f"Error listing tools: {str(e)}\n{error_traceback}",
            )

    @app.get(
        "/tools/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "get-tool"}
    )
    def get_tool(uuid_or_name: str) -> Dict[str, Any]:
        """Get metadata for a specific tool by UUID or name.

        Retrieves the complete manifest/metadata for a tool identified by either
        its UUID or its unique name.

        Args:
            uuid_or_name: The UUID or name of the tool to retrieve.

        Returns:
            dict: Tool metadata including name, uuid, description, parameters, dependencies, etc.

        Raises:
            HTTPException: 404 if tool not found, 500 for other errors.
        """
        logger.info(f"Request to get tool: {uuid_or_name}")
        get_tool_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving tool '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving tool: {str(e)}"
            )

    @app.get(
        "/tools/{uuid_or_name}/module",
        tags=[tags],
        response_class=PlainTextResponse,
        openapi_extra={"x-cli-name": "get-tool-module"},
    )
    async def get_tool_module(uuid_or_name: str) -> PlainTextResponse:
        """Get the module file content for a specific tool.

        Retrieves the Python source code or MCP content for a tool. For MCP-packaged
        tools, returns the MCP manifest stub. For code-packaged tools, returns
        the Python module source.

        Args:
            uuid_or_name: The UUID or name of the tool whose module to retrieve.

        Returns:
            PlainTextResponse: The module file content as plain text.

        Raises:
            HTTPException: 404 if tool not found, 500 for other errors.
        """
        logger.info(f"Request to get module file for tool: {uuid_or_name}")
        get_tool_module_counter.inc()
        try:
            return PlainTextResponse(
                content=service.get_module(uuid_or_name),
                media_type="text/plain",
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving module for '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving module file: {str(e)}"
            )

    @app.delete(
        "/tools/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-tool"},
    )
    async def delete_tool(uuid_or_name: str) -> Dict:
        """Delete a tool from the store.

        Removes a tool and its associated files from the store. This operation
        also triggers a content deletion event for plugin processing.

        Args:
            uuid_or_name: The UUID or name of the tool to delete.

        Returns:
            dict: Success message confirming deletion.

        Raises:
            HTTPException: 404 if tool not found, 500 for other errors.
        """
        logger.info(f"Request to delete tool: {uuid_or_name}")
        delete_tool_counter.inc()
        try:
            result = service.delete(uuid_or_name)
            emit_content_deleted("tool", result["uuid"])
            return {
                "message": f"Tool with UUID or name '{uuid_or_name}' deleted successfully."
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting tool '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting tool: {str(e)}"
            )

    @app.put(
        "/tools/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-tool"},
    )
    async def update_tool(uuid_or_name: str, tool: ToolSchema) -> Dict:
        """Update an existing tool's metadata.

        Updates the manifest/metadata for an existing tool. The module file is not
        updated by this endpoint. This operation triggers a content update event
        for plugin processing.

        Args:
            uuid_or_name: The UUID or name of the tool to update.
            tool: Updated tool metadata conforming to ToolSchema.

        Returns:
            dict: Success message confirming update.

        Raises:
            HTTPException: 404 if tool not found, 500 for other errors.
        """
        logger.info(f"Request to update tool: {uuid_or_name}")
        update_tool_counter.inc()
        try:
            result = service.update(uuid_or_name, tool.to_dict())
            emit_content_updated("tool", result["uuid"])
            return {
                "message": f"Tool with UUID or name '{uuid_or_name}' updated successfully."
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating tool '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating tool: {str(e)}"
            )

    @app.post(
        "/tools/{uuid_or_name}/execute",
        tags=[tags],
        openapi_extra={"x-cli-name": "execute-tool"},
    )
    async def execute_tool(
        uuid_or_name: str, request: Request, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """Execute a tool by UUID or name with the provided parameters.

        This endpoint mirrors the functionality of /manifests/execute/{uid} but works
        with tool UUIDs or names instead of manifest UIDs.

        Args:
            uuid_or_name: The UUID or name of the tool to execute.
            request: Represents an incoming fast api request object.
            parameters: Dictionary of key/value pairs to be passed to the tool execution (Optional).

        Returns:
            dict: Tool execution output.

        Raises:
            HTTPException: If tool not found (404) or execution fails (500).
        """
        logger.info(
            f"[execute_tool] Received execute tool: {uuid_or_name} with parameters: {parameters}"
        )
        try:
            tool_dict = service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        tool_uuid = tool_dict["uuid"]
        execute_tool_counter.labels(name=tool_uuid).inc()
        headers_dict = dict(request.headers.items())
        skillberry_context = unflatten_keys(headers_dict).get(
            SKILLBERRY_CONTEXT.lower()
        )
        env_id = (
            skillberry_context.get("env_id")
            if skillberry_context is not None
            else None
        )
        start_time = time.time()
        try:
            result = await service.execute(
                uuid_or_name, parameters=parameters, env_id=env_id
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Error executing tool '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error executing tool: {str(e)}"
            )
        duration = time.time() - start_time
        execute_successfully_tool_counter.labels(name=tool_uuid).inc()
        execute_successfully_tool_latency.labels(name=tool_uuid).observe(duration)
        return result

    @app.get("/search/tools", tags=[tags], openapi_extra={"x-cli-name": "search-tools"})
    def search_tools(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ) -> List:
        """Return a list of tools that are similar to the given search term.

        Returns tools that are below the similarity threshold and match the filters.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.
            manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
            lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).

        Returns:
            list: A list of matched tool names and similarity scores.
        """
        logger.info(f"Request to search tool descriptions for term: {search_term}")
        search_tools_counter.inc()
        try:
            return service.search(
                search_term=search_term,
                max_number_of_results=max_number_of_results,
                similarity_threshold=similarity_threshold,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            logger.error(f"Error searching tools: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching tools: {str(e)}"
            )

    @app.post("/tools/add", tags=[tags], openapi_extra={"x-cli-name": "add-tool"})
    async def add_tool_from_python(
        tool: UploadFile = File(...),
        selected_func: Optional[str] = None,
        update: bool = False,
    ) -> Dict[str, Any]:
        """Add a tool by automatically extracting parameters from Python code docstring.

        This endpoint uploads a Python file and automatically generates a tool manifest
        by parsing the function's docstring. The docstring must follow standard Python
        documentation conventions (Google, NumPy, or Sphinx style).

        Args:
            tool: The Python file to upload containing the function.
            selected_func: Optional name of the specific function to extract. If not provided,
                      the first function in the file will be used.
            update: Whether to update if a tool with the same name already exists.

        Returns:
            dict: Success message with the tool name, uuid, and module_name.

        Raises:
            HTTPException: If file is not Python (400), tool already exists (409),
                          or any other error occurs (500).
        """
        logger.info(f"Request to add tool from Python file: {tool.filename}")
        add_tool_from_python_counter.inc()

        if not tool.filename or not tool.filename.endswith(".py"):
            raise HTTPException(
                status_code=400,
                detail="Only Python (.py) files are supported. Please upload a valid Python file.",
            )
        tool_bytes = await tool.read()

        try:
            result = service.add_from_python(
                file_bytes=tool_bytes,
                file_name=tool.filename,
                selected_func=selected_func,
                update_existing=update,
            )
        except ObjectAlreadyExistsError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error adding tool: {e}")
            raise HTTPException(status_code=500, detail=f"Error adding tool: {str(e)}")

        if result.get("action") == "updated":
            emit_content_updated("tool", result["uuid"])
        else:
            emit_content_added("tool", result["uuid"])
        return result
