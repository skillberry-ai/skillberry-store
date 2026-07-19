"""Tools API endpoints for the Skillberry Store service."""

from __future__ import annotations

import traceback
from typing import Optional, Annotated, Dict, Any, List
from fastapi import FastAPI, HTTPException, File, UploadFile, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.tool_schema import ToolSchema
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys
from skillberry_store.services.exceptions import (
    ObjectAlreadyExistsError,
    ObjectInUseError,
)
from skillberry_store.services.tools_service import ToolsService


class AddToolFromCodeRequest(BaseModel):
    """Body for ``POST /tools/add_code`` — Python source as a string, not a file."""

    code: str
    selected_func: Optional[str] = None
    update: bool = False
    module_name: Optional[str] = None


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
        try:
            file_content = await module.read()
            module_filename = module.filename if module.filename else f"{tool.name}.py"
            result = service.create(
                tool.to_dict(),
                module_content=file_content,
                module_filename=module_filename,
            )
            return {
                "message": f"Tool '{result['name']}' created successfully.",
                "name": result["name"],
                "uuid": result["uuid"],
                "module_name": result["module_name"],
            }
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error creating tool: {str(e)}"
            )

    @app.get(
        "/tools/",
        tags=[tags],
        openapi_extra={"x-cli-name": "list-tools", "x-mcp-tool": True},
    )
    def list_tools(
        fields: Optional[str] = Query(
            "narrow",
            description=(
                "Field selection. 'minimal' returns uuid only. Omit or "
                "'narrow' for the UI listing set (default). 'wide' "
                "returns every persisted manifest field. 'full' returns "
                "the complete object, including flag fields that "
                "trigger bundling mechanisms. Or supply a comma-"
                "separated allowlist of field names."
            ),
        ),
    ) -> List[Dict[str, Any]]:
        """List all tools in the store.

        Retrieves metadata for all tools currently stored in the system.

        Args:
            fields: Optional field-selection spec (see query-param description).

        Returns:
            list: List of dictionaries, each containing tool metadata
                (subset when ``fields`` narrows the field selection).

        Raises:
            HTTPException: 400 if ``fields`` is invalid, 500 if listing fails.
        """
        try:
            return service.list_all(fields=fields)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error listing tools: {str(e)}\n{traceback.format_exc()}",
            )

    @app.get(
        "/tools/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "get-tool", "x-mcp-tool": True},
    )
    def get_tool(
        uuid_or_name: str,
        fields: Optional[str] = Query(
            "narrow",
            description=(
                "Field selection. 'minimal' returns uuid only. Omit or "
                "'narrow' for the UI listing set (default). 'wide' "
                "returns every persisted manifest field. 'full' returns "
                "the complete object, including flag fields that "
                "trigger bundling mechanisms. Or supply a comma-"
                "separated allowlist of field names."
            ),
        ),
    ) -> Dict[str, Any]:
        """Get metadata for a specific tool by UUID or name.

        Retrieves the manifest/metadata for a tool identified by either
        its UUID or its unique name.

        Args:
            uuid_or_name: The UUID or name of the tool to retrieve.
            fields: Optional field-selection spec (see query-param description).

        Returns:
            dict: Tool metadata (subset when ``fields`` narrows the
                field selection).

        Raises:
            HTTPException: 400 if ``fields`` is invalid, 404 if tool
                not found, 500 for other errors.
        """
        try:
            return service.get(uuid_or_name, fields=fields)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error retrieving tool: {str(e)}"
            )

    @app.get(
        "/tools/{uuid_or_name}/module",
        tags=[tags],
        response_class=PlainTextResponse,
        openapi_extra={"x-cli-name": "get-tool-module", "x-mcp-tool": True},
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
        try:
            return PlainTextResponse(
                content=service.get_module(uuid_or_name),
                media_type="text/plain",
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error retrieving module file: {str(e)}"
            )

    @app.delete(
        "/tools/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-tool", "x-mcp-tool": True},
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
        try:
            service.delete(uuid_or_name)
            return {
                "message": f"Tool with UUID or name '{uuid_or_name}' deleted successfully."
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ObjectInUseError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error deleting tool: {str(e)}"
            )

    @app.put(
        "/tools/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-tool", "x-mcp-tool": True},
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
        try:
            service.update(uuid_or_name, tool.to_dict())
            return {
                "message": f"Tool with UUID or name '{uuid_or_name}' updated successfully."
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error updating tool: {str(e)}"
            )

    @app.post(
        "/tools/{uuid_or_name}/execute",
        tags=[tags],
        openapi_extra={"x-cli-name": "execute-tool", "x-mcp-tool": True},
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
        headers_dict = dict(request.headers.items())
        skillberry_context = unflatten_keys(headers_dict).get(
            SKILLBERRY_CONTEXT.lower()
        )
        env_id = (
            skillberry_context.get("env_id") if skillberry_context is not None else None
        )
        try:
            return await service.execute(
                uuid_or_name, parameters=parameters, env_id=env_id
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error executing tool: {str(e)}"
            )

    @app.get(
        "/search/tools",
        tags=[tags],
        openapi_extra={"x-cli-name": "search-tools", "x-mcp-tool": True},
    )
    def search_tools(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
        fields: Optional[str] = Query(
            "narrow",
            description=(
                "Field selection over each match. Same grammar as the "
                "list endpoint ('minimal' for uuid-only search "
                "results that cross-reference a loaded listing; omit "
                "or 'narrow' for the UI listing set — default; 'wide' "
                "for every persisted manifest field; 'full' for the "
                "complete object; CSV allowlist). Each match is a "
                "field-selected tool dict with 'similarity_score' "
                "merged in."
            ),
        ),
    ) -> List:
        """Return a list of tools that are similar to the given search term.

        Returns tools that are below the similarity threshold and match the filters.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.
            manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
            lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).
            fields: Optional field-selection spec (see query-param description).

        Returns:
            list: Field-selected tool dicts with ``similarity_score``
                merged in.
        """
        try:
            return service.search(
                search_term=search_term,
                max_number_of_results=max_number_of_results,
                similarity_threshold=similarity_threshold,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
                fields=fields,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
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
        if not tool.filename or not tool.filename.endswith(".py"):
            raise HTTPException(
                status_code=400,
                detail="Only Python (.py) files are supported. Please upload a valid Python file.",
            )
        tool_bytes = await tool.read()

        try:
            return service.add_from_python(
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
            raise HTTPException(status_code=500, detail=f"Error adding tool: {str(e)}")

    @app.post(
        "/tools/add_code",
        tags=[tags],
        openapi_extra={"x-cli-name": "add-tool-code", "x-mcp-tool": True},
    )
    async def add_tool_from_code(req: AddToolFromCodeRequest) -> Dict[str, Any]:
        """Add a tool from Python source passed as a string (MCP-friendly).

        Same behavior as ``POST /tools/add`` (auto-extracts the manifest from the
        function docstring) but takes the source as a normal JSON ``code`` field
        instead of a file upload — so it works over the MCP bridge, which cannot
        transmit ``multipart``/octet-stream file bodies.

        Args:
            req: ``code`` (the Python source), optional ``selected_func`` (which
                function to extract; defaults to the first), ``update`` (update an
                existing tool of the same name), and ``module_name`` (stored file
                name; defaults to ``tool.py``).

        Returns:
            dict: Success message with the tool name, uuid, and module_name.

        Raises:
            HTTPException: tool already exists (409), parse/validation error
                (400), or any other error (500).
        """
        module_name = req.module_name or "tool.py"
        if not module_name.endswith(".py"):
            module_name += ".py"

        try:
            return service.add_from_python(
                file_bytes=req.code.encode("utf-8"),
                file_name=module_name,
                selected_func=req.selected_func,
                update_existing=req.update,
            )
        except ObjectAlreadyExistsError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error adding tool: {str(e)}")
