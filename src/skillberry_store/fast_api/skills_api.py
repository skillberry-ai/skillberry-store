"""Skills API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from typing import Optional, Annotated
from fastapi import FastAPI, HTTPException, Query
from prometheus_client import Counter

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.description import Description
from skillberry_store.schemas.skill_schema import SkillSchema
from skillberry_store.tools.configure import get_skills_directory, get_tools_directory, get_snippets_directory

logger = logging.getLogger(__name__)

# observability - metrics
prom_prefix = "sts_fastapi_skills_"
create_skill_counter = Counter(
    f"{prom_prefix}create_skill_counter", "Count number of skill create operations"
)
list_skills_counter = Counter(
    f"{prom_prefix}list_skills_counter", "Count number of skill list operations"
)
get_skill_counter = Counter(
    f"{prom_prefix}get_skill_counter", "Count number of skill get operations"
)
delete_skill_counter = Counter(
    f"{prom_prefix}delete_skill_counter", "Count number of skill delete operations"
)
update_skill_counter = Counter(
    f"{prom_prefix}update_skill_counter", "Count number of skill update operations"
)
search_skills_counter = Counter(
    f"{prom_prefix}search_skills_counter", "Count number of skill search operations"
)


def register_skills_api(
    app: FastAPI,
    tags: str = "skills",
    skills_descriptions: Optional[Description] = None,
):
    """Register skills API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
        skills_descriptions: Description instance for managing skill descriptions.
    """
    skills_directory = get_skills_directory()
    skill_handler = FileHandler(skills_directory)
    tools_handler = FileHandler(get_tools_directory())
    snippets_handler = FileHandler(get_snippets_directory())
    
    def populate_skill_objects(skill_dict):
        """Populate full tool and snippet objects from UUIDs."""
        # Populate tools
        if "tool_uuids" in skill_dict and skill_dict["tool_uuids"]:
            tools = []
            for tool_uuid in skill_dict["tool_uuids"]:
                # Find tool by UUID
                for filename in tools_handler.list_files():
                    if filename.endswith(".json"):
                        try:
                            content = tools_handler.read_file(filename, raw_content=True)
                            if isinstance(content, str):
                                tool_dict = json.loads(content)
                                if tool_dict.get("uuid") == tool_uuid:
                                    tools.append(tool_dict)
                                    break
                        except Exception as e:
                            logger.warning(f"Error reading tool file {filename}: {e}")
            skill_dict["tools"] = tools
        else:
            skill_dict["tools"] = []
            
        # Populate snippets
        if "snippet_uuids" in skill_dict and skill_dict["snippet_uuids"]:
            snippets = []
            for snippet_uuid in skill_dict["snippet_uuids"]:
                # Find snippet by UUID
                for filename in snippets_handler.list_files():
                    if filename.endswith(".json"):
                        try:
                            content = snippets_handler.read_file(filename, raw_content=True)
                            if isinstance(content, str):
                                snippet_dict = json.loads(content)
                                if snippet_dict.get("uuid") == snippet_uuid:
                                    snippets.append(snippet_dict)
                                    break
                        except Exception as e:
                            logger.warning(f"Error reading snippet file {filename}: {e}")
            skill_dict["snippets"] = snippets
        else:
            skill_dict["snippets"] = []
            
        return skill_dict

    @app.post("/skills/", tags=[tags])
    def create_skill(skill: Annotated[SkillSchema, Query()]):
        """Create a new skill.
        
        The form fields are dynamically generated from SkillSchema.
        Any changes to SkillSchema will automatically reflect in this API.

        Args:
            skill: The skill schema with tool_uuids and snippet_uuids (auto-generated from SkillSchema).
                   If uuid is not provided, it will be automatically generated.

        Returns:
            dict: Success message with the skill name and uuid.

        Raises:
            HTTPException: If skill already exists (409) or creation fails (500).
        """
        logger.info(f"Request to create skill: {skill.name}")
        create_skill_counter.inc()

        # Generate UUID if not provided
        if not skill.uuid:
            skill.uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for skill '{skill.name}': {skill.uuid}")

        # Check if skill already exists
        existing_skills = skill_handler.list_files()
        skill_filename = f"{skill.name}.json"

        if skill_filename in existing_skills:
            raise HTTPException(
                status_code=409, detail=f"Skill '{skill.name}' already exists."
            )

        try:
            # Convert skill to JSON and save
            skill_json = json.dumps(skill.to_dict(), indent=4)
            skill_handler.write_file_content(skill_filename, skill_json)

            # Write description for search capability
            if skills_descriptions and skill.description:
                skills_descriptions.write_description(skill.name, skill.description)
                logger.info(f"Skill description saved for: {skill.name}")

            logger.info(f"Skill '{skill.name}' created successfully")
            return {
                "message": f"Skill '{skill.name}' created successfully.",
                "name": skill.name,
                "uuid": skill.uuid,
            }
        except Exception as e:
            logger.error(f"Error creating skill '{skill.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating skill: {str(e)}"
            )

    @app.get("/skills/", tags=[tags])
    def list_skills():
        """List all skills with populated tool and snippet objects.

        Returns:
            list: A list of all skill objects with full tool and snippet details.

        Raises:
            HTTPException: If listing fails (500).
        """
        logger.info("Request to list skills")
        list_skills_counter.inc()

        try:
            skill_files = skill_handler.list_files()
            skills = []

            for filename in skill_files:
                if filename.endswith(".json"):
                    content = skill_handler.read_file(filename, raw_content=True)
                    if isinstance(content, str):
                        skill_dict = json.loads(content)
                        # Populate full tool and snippet objects
                        skill_dict = populate_skill_objects(skill_dict)
                    else:
                        continue
                    skills.append(skill_dict)

            logger.info(f"Listed {len(skills)} skills")
            return skills
        except Exception as e:
            logger.error(f"Error listing skills: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing skills: {str(e)}"
            )

    @app.get("/skills/{name}", tags=[tags])
    def get_skill(name: str):
        """Get a specific skill by name with populated tool and snippet objects.

        Args:
            name: The name of the skill.

        Returns:
            dict: The skill object with full tool and snippet details.

        Raises:
            HTTPException: If skill not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get skill: {name}")
        get_skill_counter.inc()

        try:
            skill_filename = f"{name}.json"
            content = skill_handler.read_file(skill_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for skill '{name}'"
                )
            skill_dict = json.loads(content)
            # Populate full tool and snippet objects
            skill_dict = populate_skill_objects(skill_dict)
            logger.info(f"Retrieved skill: {name}")
            return skill_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving skill '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving skill: {str(e)}"
            )

    @app.delete("/skills/{name}", tags=[tags])
    def delete_skill(name: str):
        """Delete a skill by name.

        Args:
            name: The name of the skill to delete.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If skill not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete skill: {name}")
        delete_skill_counter.inc()

        try:
            skill_filename = f"{name}.json"
            result = skill_handler.delete_file(skill_filename)

            # Delete the description for the skill
            if skills_descriptions:
                try:
                    skills_descriptions.delete_description(name)
                    logger.info(f"Skill description deleted for: {name}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete skill description for '{name}': {e}"
                    )

            logger.info(f"Skill '{name}' deleted successfully")
            return {"message": f"Skill '{name}' deleted successfully."}
        except HTTPException as e:
            # Re-raise HTTPException (like 404) without modification
            raise
        except Exception as e:
            logger.error(f"Error deleting skill '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting skill: {str(e)}"
            )

    @app.put("/skills/{name}", tags=[tags])
    def update_skill(name: str, skill: SkillSchema):
        """Update an existing skill.

        Args:
            name: The name of the skill to update.
            skill: The updated skill schema.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If skill not found (404) or update fails (500).
        """
        logger.info(f"Request to update skill: {name}")
        update_skill_counter.inc()

        try:
            skill_filename = f"{name}.json"

            # Check if skill exists
            existing_skills = skill_handler.list_files()
            if skill_filename not in existing_skills:
                raise HTTPException(
                    status_code=404, detail=f"Skill '{name}' not found."
                )

            # Update the skill
            skill_json = json.dumps(skill.to_dict(), indent=4)
            skill_handler.write_file_content(skill_filename, skill_json)
            logger.info(f"Skill '{name}' updated successfully")
            return {"message": f"Skill '{name}' updated successfully."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating skill '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating skill: {str(e)}"
            )

    @app.get("/search/skills", tags=[tags])
    def search_skills(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
    ):
        """Return a list of skills that are similar to the given search term.

        Returns skills that are below the similarity threshold.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.

        Returns:
            list: A list of matched skill names and similarity scores.
        """
        logger.info(f"Request to search skill descriptions for term: {search_term}")
        search_skills_counter.inc()

        if not skills_descriptions:
            raise HTTPException(
                status_code=503,
                detail="Skill search is not available - descriptions not initialized",
            )

        try:
            matched_entities = skills_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )

            filtered_matched_entities = [
                matched_entity
                for matched_entity in matched_entities
                if matched_entity["similarity_score"] <= similarity_threshold
            ]

            logger.info(f"Found {len(filtered_matched_entities)} matching skills")
            return filtered_matched_entities
        except Exception as e:
            logger.error(f"Error searching skills: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching skills: {str(e)}"
            )
