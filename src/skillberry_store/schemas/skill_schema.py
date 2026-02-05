"""Pydantic schema for skill objects."""

from typing import Any, Dict, List
from pydantic import Field

from .manifest_schema import ManifestSchema
from .tool_schema import ToolSchema
from .snippet_schema import SnippetSchema


class SkillSchema(ManifestSchema):
    """
    Pydantic schema for a skill.
    
    This schema extends ManifestSchema and represents the structure of a skill
    in the skillberry-store system. A skill is an ordered collection of tools 
    and snippets that work together provide the agent a skill.
    """
    
    tools: List[ToolSchema] = Field(
        default_factory=list,
        description="Ordered list of tools that comprise this skill"
    )
    snippets: List[SnippetSchema] = Field(
        default_factory=list,
        description="Ordered list of snippets that comprise this skill"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the skill schema to a dictionary."""
        return self.model_dump(exclude_none=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillSchema":
        """Create a SkillSchema instance from a dictionary."""
        return cls(**data)