"""Snippets API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.description import Description
from skillberry_store.schemas.snippet_schema import SnippetSchema
from skillberry_store.tools.configure import get_snippets_directory

logger = logging.getLogger(__name__)


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
    def create_snippet(snippet: SnippetSchema):
        """Create a new snippet.

        Args:
            snippet: The snippet schema containing content and metadata.
                    If uuid is not provided, it will be automatically generated.

        Returns:
            dict: Success message with the snippet name and uuid.

        Raises:
            HTTPException: If snippet already exists (409) or creation fails (500).
        """
        logger.info(f"Request to create snippet: {snippet.name}")

        # Generate UUID if not provided
        if not snippet.uuid:
            snippet.uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for snippet '{snippet.name}': {snippet.uuid}")

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

        try:
            snippet_filename = f"{name}.json"

            # Check if snippet exists
            existing_snippets = snippet_handler.list_files()
            if snippet_filename not in existing_snippets:
                raise HTTPException(
                    status_code=404, detail=f"Snippet '{name}' not found."
                )

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
    ):
        """Return a list of snippets that are similar to the given search term.

        Returns snippets that are below the similarity threshold.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.

        Returns:
            list: A list of matched snippet names and similarity scores.
        """
        logger.info(f"Request to search snippet descriptions for term: {search_term}")

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
                if matched_entity["similarity_score"] <= similarity_threshold
            ]

            logger.info(f"Found {len(filtered_matched_entities)} matching snippets")
            return filtered_matched_entities
        except Exception as e:
            logger.error(f"Error searching snippets: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching snippets: {str(e)}"
            )
