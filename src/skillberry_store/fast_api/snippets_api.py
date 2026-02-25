"""Snippets API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Annotated
from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from prometheus_client import Counter

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.snippet_schema import SnippetSchema
from skillberry_store.tools.configure import get_snippets_directory
from skillberry_store.fast_api.search_filters import apply_search_filters

logger = logging.getLogger(__name__)

# observability - metrics
prom_prefix = "sts_fastapi_snippets_"
create_snippet_counter = Counter(
    f"{prom_prefix}create_snippet_counter", "Count number of snippet create operations"
)
list_snippets_counter = Counter(
    f"{prom_prefix}list_snippets_counter", "Count number of snippet list operations"
)
get_snippet_counter = Counter(
    f"{prom_prefix}get_snippet_counter", "Count number of snippet get operations"
)
delete_snippet_counter = Counter(
    f"{prom_prefix}delete_snippet_counter", "Count number of snippet delete operations"
)
update_snippet_counter = Counter(
    f"{prom_prefix}update_snippet_counter", "Count number of snippet update operations"
)
search_snippets_counter = Counter(
    f"{prom_prefix}search_snippets_counter", "Count number of snippet search operations"
)


def register_snippets_api(
    app: FastAPI,
    tags: str = "snippets",
    snippets_descriptions: Optional[Description] = None,
):
    """Register snippets API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
        snippets_descriptions: Description instance for managing snippet descriptions.
    """
    snippets_directory = get_snippets_directory()
    snippet_handler = FileHandler(snippets_directory)

    @app.post("/snippets/", tags=[tags])
    async def create_snippet(
        snippet: Annotated[SnippetSchema, Query()],
        file: Optional[UploadFile] = File(None)
    ):
        """Create a new snippet.
        
        The form fields are dynamically generated from SnippetSchema.
        Any changes to SnippetSchema will automatically reflect in this API.

        Args:
            snippet: The snippet schema containing content and metadata (auto-generated from SnippetSchema).
                    If uuid is not provided, it will be automatically generated.
            file: Optional file upload for large content. If provided, overrides snippet.content.

        Returns:
            dict: Success message with the snippet name and uuid.

        Raises:
            HTTPException: If snippet already exists (409) or creation fails (500).
        """
        logger.info(f"Request to create snippet: {snippet.name}")
        create_snippet_counter.inc()

        # Generate UUID if not provided
        if not snippet.uuid:
            snippet.uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for snippet '{snippet.name}': {snippet.uuid}")

        # Set timestamps
        current_time = datetime.now(timezone.utc).isoformat()
        snippet.created_at = current_time
        snippet.modified_at = current_time

        # If file is provided, read its content and override snippet.content
        if file:
            try:
                content_bytes = await file.read()
                snippet.content = content_bytes.decode('utf-8')
                logger.info(f"Read {len(snippet.content)} characters from uploaded file")
            except Exception as e:
                logger.error(f"Error reading uploaded file: {e}")
                raise HTTPException(
                    status_code=400, detail=f"Error reading uploaded file: {str(e)}"
                )

        # Check if snippet already exists
        existing_snippets = snippet_handler.list_files()
        snippet_filename = f"{snippet.name}.json"

        if snippet_filename in existing_snippets:
            raise HTTPException(
                status_code=409, detail=f"Snippet '{snippet.name}' already exists."
            )

        try:
            # Convert snippet to JSON and save
            snippet_json = json.dumps(snippet.to_dict(), indent=4)
            snippet_handler.write_file_content(snippet_filename, snippet_json)

            # Write description for search capability
            if snippets_descriptions and snippet.description:
                snippets_descriptions.write_description(
                    snippet.name, snippet.description
                )
                logger.info(f"Snippet description saved for: {snippet.name}")

            logger.info(f"Snippet '{snippet.name}' created successfully")
            return {
                "message": f"Snippet '{snippet.name}' created successfully.",
                "name": snippet.name,
                "uuid": snippet.uuid,
            }
        except Exception as e:
            logger.error(f"Error creating snippet '{snippet.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating snippet: {str(e)}"
            )

    @app.get("/snippets/", tags=[tags])
    def list_snippets():
        """List all snippets.

        Returns:
            list: A list of all snippet objects.

        Raises:
            HTTPException: If listing fails (500).
        """
        logger.info("Request to list snippets")
        list_snippets_counter.inc()

        try:
            snippet_files = snippet_handler.list_files()
            snippets = []

            for filename in snippet_files:
                if filename.endswith(".json"):
                    content = snippet_handler.read_file(filename, raw_content=True)
                    if isinstance(content, str):
                        snippet_dict = json.loads(content)
                    else:
                        continue
                    snippets.append(snippet_dict)

            # Sort by modified_at in descending order (most recent first)
            snippets.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            logger.info(f"Listed {len(snippets)} snippets")
            return snippets
        except Exception as e:
            logger.error(f"Error listing snippets: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing snippets: {str(e)}"
            )

    @app.get("/snippets/{name}", tags=[tags])
    def get_snippet(name: str):
        """Get a specific snippet by name.

        Args:
            name: The name of the snippet.

        Returns:
            dict: The snippet object.

        Raises:
            HTTPException: If snippet not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get snippet: {name}")
        get_snippet_counter.inc()

        try:
            snippet_filename = f"{name}.json"
            content = snippet_handler.read_file(snippet_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for snippet '{name}'"
                )
            snippet_dict = json.loads(content)
            logger.info(f"Retrieved snippet: {name}")
            return snippet_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving snippet '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving snippet: {str(e)}"
            )

    @app.delete("/snippets/{name}", tags=[tags])
    def delete_snippet(name: str):
        """Delete a snippet by name.

        Args:
            name: The name of the snippet to delete.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If snippet not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete snippet: {name}")
        delete_snippet_counter.inc()

        try:
            snippet_filename = f"{name}.json"
            result = snippet_handler.delete_file(snippet_filename)

            # Delete the description for the snippet
            if snippets_descriptions:
                try:
                    snippets_descriptions.delete_description(name)
                    logger.info(f"Snippet description deleted for: {name}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete snippet description for '{name}': {e}"
                    )

            logger.info(f"Snippet '{name}' deleted successfully")
            return {"message": f"Snippet '{name}' deleted successfully."}
        except HTTPException as e:
            # Re-raise HTTPException (like 404) without modification
            raise
        except Exception as e:
            logger.error(f"Error deleting snippet '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting snippet: {str(e)}"
            )

    @app.put("/snippets/{name}", tags=[tags])
    def update_snippet(name: str, snippet: SnippetSchema):
        """Update an existing snippet.

        Args:
            name: The name of the snippet to update.
            snippet: The updated snippet schema.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If snippet not found (404) or update fails (500).
        """
        logger.info(f"Request to update snippet: {name}")
        update_snippet_counter.inc()

        try:
            snippet_filename = f"{name}.json"

            # Check if snippet exists
            existing_snippets = snippet_handler.list_files()
            if snippet_filename not in existing_snippets:
                raise HTTPException(
                    status_code=404, detail=f"Snippet '{name}' not found."
                )

            # Update modified timestamp
            snippet.modified_at = datetime.now(timezone.utc).isoformat()

            # Update the snippet
            snippet_json = json.dumps(snippet.to_dict(), indent=4)
            snippet_handler.write_file_content(snippet_filename, snippet_json)
            logger.info(f"Snippet '{name}' updated successfully")
            return {"message": f"Snippet '{name}' updated successfully."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating snippet '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating snippet: {str(e)}"
            )

    @app.get("/search/snippets", tags=[tags])
    def search_snippets(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        """Return a list of snippets that are similar to the given search term.

        Returns snippets that are below the similarity threshold and match the filters.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.
            manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
            lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).

        Returns:
            list: A list of matched snippet names and similarity scores.
        """
        logger.info(f"Request to search snippet descriptions for term: {search_term}")
        search_snippets_counter.inc()

        if not snippets_descriptions:
            raise HTTPException(
                status_code=503,
                detail="Snippet search is not available - descriptions not initialized",
            )

        try:
            matched_entities = snippets_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )

            # filtered_matched_entities = [
            #     matched_entity
            #     for matched_entity in matched_entities
            #     if matched_entity["similarity_score"] <= similarity_threshold
            # ]
            filtered_matched_entities = matched_entities

            # Get full snippet objects for filtering
            snippets_to_filter = []
            for matched_entity in filtered_matched_entities:
                snippet_name = matched_entity.get("filename") or matched_entity.get("name")
                if not snippet_name:
                    logger.warning(f"Matched entity missing 'filename' or 'name' field: {matched_entity}")
                    continue
                try:
                    snippet_filename = f"{snippet_name}.json"
                    content = snippet_handler.read_file(snippet_filename, raw_content=True)
                    if isinstance(content, str):
                        snippet_dict = json.loads(content)
                        snippet_dict["similarity_score"] = matched_entity.get("similarity_score", 0.0)
                        snippets_to_filter.append(snippet_dict)
                except Exception as e:
                    logger.warning(f"Could not load snippet {snippet_name} for filtering: {e}")

            # Apply manifest and lifecycle filters
            filtered_snippets = apply_search_filters(
                snippets_to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )

            # Sort by modified_at in descending order (most recent first)
            filtered_snippets.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            # Return only filename and similarity_score (filename is the snippet name)
            result = [
                {"filename": snippet.get("name", ""), "similarity_score": snippet.get("similarity_score", 0.0)}
                for snippet in filtered_snippets
                if snippet.get("name")  # Only include if name exists
            ]

            logger.info(f"Found {len(result)} matching snippets after filtering")
            return result
        except Exception as e:
            logger.error(f"Error searching snippets: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching snippets: {str(e)}"
            )
