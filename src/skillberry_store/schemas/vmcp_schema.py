"""Pydantic schema for virtual MCP server objects."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from .manifest_schema import ManifestSchema
from .skill_schema import SkillSchema


class VmcpSchema(ManifestSchema):
    """
    Pydantic schema for a virtual MCP server.
    
    This schema extends ManifestSchema and represents the structure of a virtual
    MCP server in the skillberry-store system. A virtual MCP server is a dynamically
    created MCP server that exposes a skill from the skillberry-store.
    """
    
    port: int = Field(
        ...,
        description="Port on which the virtual MCP server is running",
        gt=0,
        lt=65536
    )
    skill: SkillSchema = Field(
        default=None,
        description="Skill registered with the virtual MCP server"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the vmcp schema to a dictionary."""
        return self.model_dump(exclude_none=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VmcpSchema":
        """Create a VmcpSchema instance from a dictionary."""
        return cls(**data)