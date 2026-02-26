"""Pydantic schema for manifest objects."""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum


class ManifestState(str, Enum):
    """Enum for manifest lifecycle states."""
    UNKNOWN = "unknown"
    ANY = "any"
    NEW = "new"
    CHECKED = "checked"
    APPROVED = "approved"


class ManifestSchema(BaseModel):
    """
    Pydantic schema for a manifest.
    
    This schema represents the structure of a manifest that describes
    a manifest in the skillberry-store system.
    """
    
    name: None|str = Field(
        None,
        description="Name"
    )
    uuid: None|str = Field(
        None,
        description="A UUID. If not provided, a UUID will be automatically generated."
    )
    version: None|str = Field(
        None,
        description="Version"
    )
    description: Optional[str] = Field(
        None,
        description="Short description"
    )
    state: ManifestState = Field(
        default=ManifestState.APPROVED,
        description="Lifecycle state"
    )
    tags: Optional[list[str]] = Field(
        default_factory=list,
        description="List of tags for categorizing"
    )
    extra: Optional[str] = Field(
        default=None,
        description="Optional JSON string for additional flexible information (e.g., '{\"key\": \"value\"}')"
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when created"
    )
    modified_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when last modified"
    )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the manifest schema to a dictionary.
        
        Parses the extra field from JSON string to dict if present.
        """
        result = self.model_dump(exclude_none=False)
        # Parse extra from JSON string to dict if present
        if result.get("extra") and isinstance(result["extra"], str):
            try:
                result["extra"] = json.loads(result["extra"])
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, keep as string
                pass
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManifestSchema":
        """Create a ManifestSchema instance from a dictionary.
        
        Converts the extra field from dict to JSON string if present.
        """
        # Make a copy to avoid modifying the original
        data_copy = data.copy()
        # Convert extra from dict to JSON string if present
        if "extra" in data_copy and isinstance(data_copy["extra"], dict):
            data_copy["extra"] = json.dumps(data_copy["extra"])
        return cls(**data_copy)