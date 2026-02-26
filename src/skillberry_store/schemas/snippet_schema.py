"""Pydantic schema for snippet objects."""

from typing import Any, Dict, Optional
from pydantic import Field
from enum import Enum

from .manifest_schema import ManifestSchema


class ContentType(str, Enum):
    """Enum for snippet content types."""
    TEXT_PLAIN = "text/plain"
    TEXT_MARKDOWN = "text/markdown"
    TEXT_HTML = "text/html"
    TEXT_XML = "text/xml"
    TEXT_CSS = "text/css"

class SnippetSchema(ManifestSchema):
    """
    Pydantic schema for a snippet.
    
    This schema extends ManifestSchema and represents the structure of a text snippet
    in the skillberry-store system.
    """
    
    content: str = Field(
        ...,
        description="The text content of the snippet"
    )
    content_type: ContentType = Field(
        default=ContentType.TEXT_PLAIN,
        description="MIME type of the snippet content"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the snippet schema to a dictionary."""
        return self.model_dump(exclude_none=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnippetSchema":
        """Create a SnippetSchema instance from a dictionary.
        
        Only passes known fields to avoid **kwargs issues.
        """
        # Get the model's field names to filter out unknown fields
        valid_fields = cls.model_fields.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)