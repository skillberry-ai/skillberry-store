"""Pydantic schema for manifest objects."""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from enum import Enum


class ManifestState(str, Enum):
    """Enum for manifest lifecycle states."""
    UNKNOWN = "unknown"
    ANY = "any"
    NEW = "new"
    CHECKED = "checked"
    APPROVED = "approved"
    BROKEN = "broken"


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
    extra: Dict[str, Any] | str = Field(
        default_factory=dict,
        description="Optional dictionary for additional flexible information"
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when created"
    )
    modified_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when last modified"
    )

    @field_validator("extra", mode="before")
    @classmethod
    def parse_extra_json_string(cls, value):
        """Accept JSON-encoded query values for flexible metadata."""
        if value in (None, ""):
            return {}
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("extra must be a dictionary or JSON object string") from exc
            if not isinstance(parsed, dict):
                raise ValueError("extra must be a dictionary or JSON object string")
            return parsed
        return value
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the manifest schema to a dictionary."""
        return self.model_dump(exclude_none=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManifestSchema":
        """Create a ManifestSchema instance from a dictionary.
        
        Only passes known fields to avoid **kwargs issues.
        """
        # Get the model's field names to filter out unknown fields
        valid_fields = cls.model_fields.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
