"""Snippets API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Annotated
from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from prometheus_client import Counter

from skillberry_store.modules.object_handler import get_object_handler
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.snippet_schema import SnippetSchema
from skillberry_store.tools.configure import get_snippets_directory
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.utils.utils import normalize_uuid, generate_or_validate_uuid

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
    snippet_handler = get_object_handler("snippet")

    @app.post("/snippets/", tags=[tags], openapi_extra={"x-cli-name": "create-snippet"})
    async def create_snippet(
        snippet: Annotated[SnippetSchema, Query()],
        file: Optional[UploadFile] = File(None),
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

        # Generate or validate UUID
        snippet.uuid = generate_or_validate_uuid(snippet.uuid)
        logger.info(f"UUID for snippet '{snippet.name}': {snippet.uuid}")

        # Set timestamps
        current_time = datetime.now(timezone.utc).isoformat()
        snippet.created_at = current_time
        snippet.modified_at = current_time

        # If file is provided, read its content and override snippet.content
        if file:
            try:
                content_bytes = await file.read()
                snippet.content = content_bytes.decode("utf-8")
                logger.info(
                    f"Read {len(snippet.content)} characters from uploaded file"
                )
            except Exception as e:
                logger.error(f"Error reading uploaded file: {e}")
                raise HTTPException(
                    status_code=400, detail=f"Error reading uploaded file: {str(e)}"
                )

        # Check if snippet with this UUID already exists
        try:
            snippet_handler.read_dict(snippet.uuid)
            # If we get here, the snippet exists - raise 409 Conflict
            raise HTTPException(
                status_code=409,
                detail=f"Snippet with UUID '{snippet.uuid}' already exists",
            )
        except HTTPException as e:
            # If it's a 404, that's good - snippet doesn't exist yet
            if e.status_code != 404:
                raise

        try:
            # Determine correct parent for this snippet becoming HEAD
            if snippet.name:
                snippet.parent = snippet_handler.get_cache_parent_for_head(
                    snippet.uuid, snippet.name
                )
                logger.info(
                    f"Setting parent for snippet '{snippet.name}' to {snippet.parent}"
                )

            # Save snippet dict to UUID subfolder
            snippet_handler.write_dict(snippet.uuid, snippet.to_dict())

            # Update cache - this becomes new HEAD
            if snippet.name:
                snippet_handler.update_cache(snippet.uuid, new_name=snippet.name)

            # Write description for search capability (indexed by UUID)
            if snippets_descriptions and snippet.description:
                snippets_descriptions.write_description(
                    snippet.uuid, snippet.description
                )
                logger.info(f"Snippet description saved for UUID: {snippet.uuid}")

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

    @app.get("/snippets/", tags=[tags], openapi_extra={"x-cli-name": "list-snippets"})
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
            snippets = snippet_handler.list_all_dicts()

            # Sort by modified_at in descending order (most recent first)
            snippets.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            logger.info(f"Listed {len(snippets)} snippets")
            return snippets
        except Exception as e:
            logger.error(f"Error listing snippets: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing snippets: {str(e)}"
            )

    @app.get("/snippets/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "get-snippet"})
    def get_snippet(uuid_or_name: str):
        """Get a specific snippet by UUID or name.

        Args:
            uuid_or_name: The UUID or name of the snippet.

        Returns:
            dict: The snippet object.

        Raises:
            HTTPException: If snippet not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get snippet: {uuid_or_name}")
        get_snippet_counter.inc()

        try:
            # Resolve UUID or name to UUID and read manifest
            snippet_uuid = snippet_handler.resolve_to_uuid_or_error(uuid_or_name)
            snippet_dict = snippet_handler.read_dict(snippet_uuid)
            logger.info(f"Retrieved snippet: {uuid_or_name}")
            return snippet_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving snippet '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving snippet: {str(e)}"
            )

    @app.delete("/snippets/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "delete-snippet"})
    def delete_snippet(uuid_or_name: str):
        """Delete a snippet by UUID or name.

        Args:
            uuid_or_name: The UUID or name of the snippet to delete.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If snippet not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete snippet: {uuid_or_name}")
        delete_snippet_counter.inc()

        try:
            # Read snippet to get UUID, name, and parent before deletion
            snippet_uuid = None
            snippet_name = None
            snippet_parent = None
            # Resolve UUID or name to UUID
            snippet_uuid = snippet_handler.resolve_to_uuid_or_error(uuid_or_name)

            # Read snippet metadata before deletion
            try:
                snippet_dict = snippet_handler.read_dict(snippet_uuid)
                snippet_name = snippet_dict.get("name")
                snippet_parent = snippet_dict.get("parent")
            except Exception as e:
                logger.warning(f"Could not read snippet before deletion: {e}")

            # Delete the snippet using ObjectHandler
            result = snippet_handler.delete_object(snippet_uuid)

            # Update cache after deletion
            if snippet_uuid and snippet_name:
                snippet_handler.update_cache(
                    snippet_uuid,
                    new_name=None,
                    old_name=snippet_name,
                    old_parent=snippet_parent,
                )

            # Delete the description for the snippet (indexed by UUID)
            if snippets_descriptions and snippet_uuid:
                try:
                    snippets_descriptions.delete_description(snippet_uuid)
                    logger.info(f"Snippet description deleted for UUID: {snippet_uuid}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete snippet description for UUID '{snippet_uuid}': {e}"
                    )

            logger.info(
                f"Snippet with UUID or name '{uuid_or_name}' deleted successfully"
            )
            return {
                "message": f"Snippet with UUID or name '{uuid_or_name}' deleted successfully."
            }
        except HTTPException as e:
            # Re-raise HTTPException (like 404) without modification
            raise
        except Exception as e:
            logger.exception(f"Error deleting snippet '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting snippet: {str(e)}"
            )

    @app.put("/snippets/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "update-snippet"})
    def update_snippet(uuid_or_name: str, snippet: SnippetSchema):
        """Update an existing snippet by UUID or name.

        Args:
            uuid_or_name: The UUID or name of the snippet to update.
            snippet: The updated snippet schema.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If snippet not found (404) or update fails (500).
        """
        logger.info(f"Request to update snippet: {uuid_or_name}")
        update_snippet_counter.inc()

        try:
            # Resolve UUID or name to UUID (raises 404 if not found)
            snippet_uuid = snippet_handler.resolve_to_uuid_or_error(uuid_or_name)

            # Read existing dict to preserve uuid and created_at
            existing_dict = snippet_handler.read_dict(snippet_uuid)
            old_name = existing_dict.get("name")
            old_parent = existing_dict.get("parent")

            # Convert update data to dict
            update_data = snippet.to_dict()

            # Determine new name
            new_name = snippet.name if snippet.name else old_name

            # Determine correct parent for this snippet becoming HEAD
            if new_name:
                new_parent = snippet_handler.get_cache_parent_for_head(
                    snippet_uuid, new_name
                )
                update_data["parent"] = new_parent
                logger.info(f"Setting parent for snippet '{new_name}' to {new_parent}")

            # Merge: preserve uuid and created_at from existing, update modified_at
            merged_dict = {**existing_dict, **update_data}
            merged_dict["uuid"] = existing_dict.get("uuid", snippet_uuid)
            merged_dict["created_at"] = existing_dict.get("created_at")
            merged_dict["modified_at"] = datetime.now(timezone.utc).isoformat()

            # Write the merged dict using ObjectHandler
            snippet_handler.write_dict(snippet_uuid, merged_dict)

            # Update cache - this becomes HEAD for its (possibly new) name
            if new_name:
                snippet_handler.update_cache(
                    snippet_uuid,
                    new_name=new_name,
                    old_name=old_name,
                    old_parent=old_parent,
                )

            # Update description for search capability (indexed by UUID)
            if snippets_descriptions and merged_dict.get("description"):
                snippets_descriptions.write_description(
                    snippet_uuid, merged_dict["description"]
                )
                logger.info(f"Snippet description updated for UUID: {snippet_uuid}")

            logger.info(
                f"Snippet with UUID or name '{uuid_or_name}' (UUID: {snippet_uuid}) updated successfully"
            )
            return {
                "message": f"Snippet with UUID or name '{uuid_or_name}' updated successfully."
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating snippet '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating snippet: {str(e)}"
            )

    @app.get("/search/snippets", tags=[tags], openapi_extra={"x-cli-name": "search-snippets"})
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

            filtered_matched_entities = [
                matched_entity
                for matched_entity in matched_entities
                if float(matched_entity["similarity_score"]) <= similarity_threshold
            ]

            # Get full snippet objects for filtering
            snippets_to_filter = []
            for matched_entity in filtered_matched_entities:
                # The matched entity filename is actually the UUID (since descriptions are indexed by UUID)
                snippet_uuid = matched_entity.get("filename") or matched_entity.get(
                    "name"
                )
                if not snippet_uuid:
                    logger.warning(
                        f"Matched entity missing 'filename' or 'name' field: {matched_entity}"
                    )
                    continue
                try:
                    # Read snippet manifest by UUID
                    snippet_dict = snippet_handler.read_dict(snippet_uuid)
                    snippet_dict["similarity_score"] = matched_entity.get(
                        "similarity_score", 0.0
                    )
                    snippets_to_filter.append(snippet_dict)
                except Exception as e:
                    logger.warning(
                        f"Could not load snippet {snippet_uuid} for filtering: {e}"
                    )

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
                {
                    "filename": snippet.get("name", ""),
                    "similarity_score": snippet.get("similarity_score", 0.0),
                }
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
