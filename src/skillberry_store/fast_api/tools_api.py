"""Tools API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from typing import Optional, Type, TypeVar, Annotated, Dict, Any
from inspect import Parameter, Signature
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Query, Request
from pydantic import BaseModel

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.file_executor import FileExecutor
from skillberry_store.modules.description import Description
from skillberry_store.schemas.tool_schema import ToolSchema
from skillberry_store.tools.configure import (
    get_tools_directory,
    get_files_directory_path,
)
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys

logger = logging.getLogger(__name__)


def register_tools_api(
    app: FastAPI, tags: str = "tools", tools_descriptions: Optional[Description] = None
):
    """Register tools API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
        tools_descriptions: Description instance for managing tool descriptions.
    """
    tools_directory = get_tools_directory()
    tool_handler = FileHandler(tools_directory)

    # File handler for storing tool module files
    files_directory = get_files_directory_path()
    file_handler = FileHandler(files_directory)

    @app.post("/tools/", tags=[tags])
    async def create_tool(
        tool: Annotated[ToolSchema, Query()],
        module: UploadFile = File(...),
    ):
        """Create a new tool with required file upload.

        The form fields are dynamically generated from ToolSchema.
        Any changes to ToolSchema will automatically reflect in this API.

        Args:
            tool: Tool schema with all fields (auto-generated from ToolSchema).
            module: Required file upload for the tool module (e.g., Python file).

        Returns:
            dict: Success message with the tool name and uuid.

        Raises:
            HTTPException: If tool already exists (409) or creation fails (500).
        """
        logger.info(f"Request to create tool: {tool.name}")

        # Generate UUID if not provided
        if not tool.uuid:
            tool.uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for tool '{tool.name}': {tool.uuid}")

        # Check if tool already exists
        existing_tools = tool_handler.list_files()
        tool_filename = f"{tool.name}.json"

        if tool_filename in existing_tools:
            raise HTTPException(
                status_code=409, detail=f"Tool '{tool.name}' already exists."
            )

        try:
            # Save the module file and automatically set module_name from the uploaded filename
            file_content = await module.read()
            module_filename = module.filename if module.filename else f"{tool.name}.py"

            file_handler.write_file(file_content, filename=module_filename)
            tool.module_name = module_filename
            logger.info(f"Saved module file: {module_filename}")

            # Convert tool to JSON and save
            tool_json = json.dumps(tool.to_dict(), indent=4)
            tool_handler.write_file_content(tool_filename, tool_json)

            # Write description for search capability
            if tools_descriptions and tool.description:
                tools_descriptions.write_description(tool.name, tool.description)
                logger.info(f"Tool description saved for: {tool.name}")

            logger.info(f"Tool '{tool.name}' created successfully")
            return {
                "message": f"Tool '{tool.name}' created successfully.",
                "name": tool.name,
                "uuid": tool.uuid,
                "module_name": tool.module_name,
            }
        except Exception as e:
            logger.error(f"Error creating tool '{tool.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating tool: {str(e)}"
            )

    @app.get("/tools/", tags=[tags])
    def list_tools():
        """List all tools.

        Returns:
            list: A list of all tool objects.

        Raises:
            HTTPException: If listing fails (500).
        """
        logger.info("Request to list tools")

        try:
            tool_files = tool_handler.list_files()
            tools = []

            for filename in tool_files:
                if filename.endswith(".json"):
                    content = tool_handler.read_file(filename, raw_content=True)
                    if isinstance(content, str):
                        tool_dict = json.loads(content)
                    else:
                        continue
                    tools.append(tool_dict)

            logger.info(f"Listed {len(tools)} tools")
            return tools
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing tools: {str(e)}"
            )

    @app.get("/tools/{name}", tags=[tags])
    def get_tool(name: str):
        """Get a specific tool by name.

        Args:
            name: The name of the tool.

        Returns:
            dict: The tool object.

        Raises:
            HTTPException: If tool not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get tool: {name}")

        try:
            tool_filename = f"{name}.json"
            content = tool_handler.read_file(tool_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for tool '{name}'"
                )
            tool_dict = json.loads(content)
            logger.info(f"Retrieved tool: {name}")
            return tool_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving tool '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving tool: {str(e)}"
            )

    @app.get("/tools/{name}/module", tags=[tags])
    def get_tool_module(name: str):
        """Get the module file for a specific tool.

        Args:
            name: The name of the tool.

        Returns:
            FileResponse: The module file content.

        Raises:
            HTTPException: If tool not found (404), module not specified (404),
                          module file not found (404), or retrieval fails (500).
        """
        logger.info(f"Request to get module file for tool: {name}")

        try:
            # First, get the tool to find the module_name
            tool_filename = f"{name}.json"
            content = tool_handler.read_file(tool_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for tool '{name}'"
                )
            tool_dict = json.loads(content)

            # Check if module_name exists
            module_name = tool_dict.get("module_name")
            if not module_name:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool '{name}' does not have a module file specified",
                )

            # Return the module file
            logger.info(f"Retrieving module file: {module_name}")
            return file_handler.read_file(module_name, raw_content=False)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving module file for tool '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving module file: {str(e)}"
            )

    @app.delete("/tools/{name}", tags=[tags])
    def delete_tool(name: str):
        """Delete a tool by name.

        Args:
            name: The name of the tool to delete.
                  Also deletes the associated module file if it exists.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If tool not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete tool: {name}")

        try:
            tool_filename = f"{name}.json"

            # Read tool to get module_name before deletion
            try:
                content = tool_handler.read_file(tool_filename, raw_content=True)
                if isinstance(content, str):
                    tool_dict = json.loads(content)
                    module_name = tool_dict.get("module_name")

                    # Delete the module file if it exists
                    if module_name:
                        try:
                            file_handler.delete_file(module_name)
                            logger.info(f"Deleted module file: {module_name}")
                        except Exception as e:
                            logger.warning(
                                f"Could not delete module file '{module_name}': {e}"
                            )
            except Exception as e:
                logger.warning(f"Could not read tool before deletion: {e}")

            # Delete the tool JSON file
            result = tool_handler.delete_file(tool_filename)

            # Delete the description for the tool
            if tools_descriptions:
                try:
                    tools_descriptions.delete_description(name)
                    logger.info(f"Tool description deleted for: {name}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete tool description for '{name}': {e}"
                    )

            logger.info(f"Tool '{name}' deleted successfully")
            return {"message": f"Tool '{name}' deleted successfully."}
        except HTTPException as e:
            # Re-raise HTTPException (like 404) without modification
            raise
        except Exception as e:
            logger.error(f"Error deleting tool '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting tool: {str(e)}"
            )

    @app.put("/tools/{name}", tags=[tags])
    def update_tool(name: str, tool: ToolSchema):
        """Update an existing tool.

        Args:
            name: The name of the tool to update.
            tool: The updated tool schema.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If tool not found (404) or update fails (500).
        """
        logger.info(f"Request to update tool: {name}")

        try:
            tool_filename = f"{name}.json"

            # Check if tool exists
            existing_tools = tool_handler.list_files()
            if tool_filename not in existing_tools:
                raise HTTPException(status_code=404, detail=f"Tool '{name}' not found.")

            # Update the tool
            tool_json = json.dumps(tool.to_dict(), indent=4)
            tool_handler.write_file_content(tool_filename, tool_json)
            logger.info(f"Tool '{name}' updated successfully")
            return {"message": f"Tool '{name}' updated successfully."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating tool '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating tool: {str(e)}"
            )

    @app.post("/tools/{name}/execute", tags=[tags])
    async def execute_tool(
        name: str, request: Request, parameters: Optional[Dict[str, Any]] = None
    ):
        """Execute a tool by name with the provided parameters.

        This endpoint mirrors the functionality of /manifests/execute/{uid} but works
        with tool names instead of manifest UIDs.

        Args:
            name: The name of the tool to execute.
            request: Represents an incoming fast api request object.
            parameters: Dictionary of key/value pairs to be passed to the tool execution (Optional).

        Returns:
            dict: Tool execution output.

        Raises:
            HTTPException: If tool not found (404) or execution fails (500).
        """
        logger.info(f"Request to execute tool: {name} with parameters: {parameters}")

        try:
            # Get the tool metadata
            tool_filename = f"{name}.json"
            content = tool_handler.read_file(tool_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for tool '{name}'"
                )
            tool_dict = json.loads(content)

            # Extract skillberry context from headers (similar to manifest execution)
            headers = request.headers
            logger.info(f"Request headers: {headers}")

            # Convert headers to dict for unflatten_keys
            headers_dict = dict(headers.items())
            skillberry_context = unflatten_keys(headers_dict).get(
                SKILLBERRY_CONTEXT.lower()
            )
            logger.info(f"Skillberry context: {skillberry_context}")

            env_id = (
                skillberry_context.get("env_id")
                if skillberry_context is not None
                else None
            )

            # Check if module_name exists
            module_name = tool_dict.get("module_name")
            if not module_name:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool '{name}' does not have a module file specified",
                )

            # Get the module file content
            module_content = file_handler.read_file(module_name, raw_content=True)
            if not isinstance(module_content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid module content for tool '{name}'"
                )

            # Execute the tool using FileExecutor
            file_executor = FileExecutor(
                name=name,
                file_content=module_content,
                file_manifest=tool_dict,
                dependent_file_contents=[],
                dependent_manifests_as_dict=[],
            )

            # Ensure parameters is not None
            exec_parameters = parameters if parameters is not None else {}
            result = await file_executor.execute_file(
                parameters=exec_parameters, env_id=env_id
            )
            logger.info(f"Tool '{name}' executed successfully with result: {result}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error executing tool: {str(e)}"
            )

    @app.get("/search/tools", tags=[tags])
    def search_tools(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
    ):
        """Return a list of tools that are similar to the given search term.

        Returns tools that are below the similarity threshold.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.

        Returns:
            list: A list of matched tool names and similarity scores.
        """
        logger.info(f"Request to search tool descriptions for term: {search_term}")

        if not tools_descriptions:
            raise HTTPException(
                status_code=503,
                detail="Tool search is not available - descriptions not initialized",
            )

        try:
            matched_entities = tools_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )

            filtered_matched_entities = [
                matched_entity
                for matched_entity in matched_entities
                if matched_entity["similarity_score"] <= similarity_threshold
            ]

            logger.info(f"Found {len(filtered_matched_entities)} matching tools")
            return filtered_matched_entities
        except Exception as e:
            logger.error(f"Error searching tools: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching tools: {str(e)}"
            )
