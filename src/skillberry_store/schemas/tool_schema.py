"""Pydantic schema for tool objects."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from .manifest_schema import ManifestSchema


class ToolType(str, Enum):
    """Enum for tool types."""
    CODE_PYTHON = "code/python"
    JSON_GENAI_LH = "json/genai-lh"


class ToolParamsSchema(BaseModel):
    """Schema for tool parameters."""
    
    type: str = Field(
        default="object",
        description="Type of the parameters object"
    )
    properties: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Dictionary of parameter properties with their types and descriptions"
    )
    required: List[str] = Field(
        default_factory=list,
        description="List of required parameter names"
    )
    optional: List[str] = Field(
        default_factory=list,
        description="List of optional parameter names"
    )


class ToolReturnsSchema(BaseModel):
    """Schema for tool return values."""
    
    type: Optional[str] = Field(
        None,
        description="Return type of the tool"
    )
    description: Optional[str] = Field(
        None,
        description="Description of the return value"
    )


class ToolSchema(ManifestSchema):
    """
    Pydantic schema for a tool.
    
    This schema extends ManifestSchema and represents the structure of a tool
    in the skillberry-store system, including programming language, parameters,
    and execution details.
    """
    
    module_name: Optional[str] = Field(
        None,
        description="Name of the module containing the tool"
    )
    programming_language: str = Field(
        default="python",
        description="Programming language of the tool"
    )
    packaging_format: str = Field(
        default="code",
        description="Packaging format of the tool"
    )
    mcp_url: Optional[str] = Field(
        default=None,
        description="MCP server URL (required when packaging_format is 'mcp')"
    )
    mcp_tool_name: Optional[str] = Field(
        default=None,
        description="Actual tool name on the MCP server (required when packaging_format is 'mcp')"
    )
    params: ToolParamsSchema = Field(
        default_factory=ToolParamsSchema,
        description="Parameters schema for the tool"
    )
    returns: Optional[ToolReturnsSchema] = Field(
        None,
        description="Return value schema for the tool"
    )
    dependencies: Optional[List[str]] = Field(
        default=None,
        description="List of tool names that this tool depends on"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the tool schema to a dictionary."""
        return self.model_dump(exclude_none=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolSchema":
        """Create a ToolSchema instance from a dictionary.
        
        Only passes known fields to avoid **kwargs issues.
        """
        # Get the model's field names to filter out unknown fields
        valid_fields = cls.model_fields.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)