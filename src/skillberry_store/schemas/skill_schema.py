"""Pydantic schema for skill objects."""

from typing import Any, Dict, List
from pydantic import Field

from .manifest_schema import ManifestSchema


class SkillSchema(ManifestSchema):
    """
    Pydantic schema for a skill.
    
    This schema extends ManifestSchema and represents the structure of a skill
    in the skillberry-store system. A skill is an ordered collection of tools
    and snippets referenced by their UUIDs.
    """
    
    tool_uuids: List[str] = Field(
        default_factory=list,
        description="Ordered list of tool UUIDs that comprise this skill"
    )
    snippet_uuids: List[str] = Field(
        default_factory=list,
        description="Ordered list of snippet UUIDs that comprise this skill"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the skill schema to a dictionary."""
        return self.model_dump(exclude_none=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillSchema":
        """Create a SkillSchema instance from a dictionary.
        
        Only passes known fields to avoid **kwargs issues.
        """
        # Get the model's field names to filter out unknown fields
        valid_fields = cls.model_fields.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)