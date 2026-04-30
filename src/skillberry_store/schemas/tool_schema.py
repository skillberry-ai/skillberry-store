"""Pydantic schema for tool objects."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
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
        description="Packaging format of the tool (e.g., 'code', 'mcp')"
    )
    packaging_params: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Parameters specific to the packaging format.For 'mcp' format, should contain 'mcp_url' and 'mcp_tool_name'."
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
    
    @model_validator(mode='after')
    def validate_packaging_params(self) -> 'ToolSchema':
        """Validate packaging_params based on packaging_format.
        
        For MCP packaging format, ensures that packaging_params contains
        the required 'mcp_url' and 'mcp_tool_name' fields.
        
        Returns:
            ToolSchema: The validated schema instance
            
        Raises:
            ValueError: If packaging_params is missing or incomplete for MCP format
        """
        if self.packaging_format == "mcp":
            if not self.packaging_params:
                raise ValueError(
                    "packaging_params is required when packaging_format is 'mcp'. "
                    "It should contain 'mcp_url' and 'mcp_tool_name'."
                )
            
            required_keys = {"mcp_url", "mcp_tool_name"}
            missing_keys = required_keys - set(self.packaging_params.keys())
            if missing_keys:
                raise ValueError(
                    f"MCP packaging requires these params in packaging_params: {missing_keys}. "
                    f"Expected: {required_keys}"
                )
        
        return self
    
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