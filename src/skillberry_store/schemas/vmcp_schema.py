"""Pydantic schema for virtual MCP server objects."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from .manifest_schema import ManifestSchema


class VmcpSchema(ManifestSchema):
    """
    Pydantic schema for a virtual MCP server.
    
    This schema extends ManifestSchema and represents the structure of a virtual
    MCP server in the skillberry-store system. A virtual MCP server is a dynamically
    created MCP server that exposes a skill from the skillberry-store.
    """
    
    port: Optional[int] = Field(
        default=None,
        description="Port on which the virtual MCP server is running. If None, an available port will be auto-assigned.",
        gt=0,
        lt=65536
    )
    skill_uuid: Optional[str] = Field(
        default=None,
        description="UUID of the skill registered with the virtual MCP server"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the vmcp schema to a dictionary."""
        return self.model_dump(exclude_none=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VmcpSchema":
        """Create a VmcpSchema instance from a dictionary."""
        return cls(**data)