"""Pydantic schema for virtual NFS server objects."""

from typing import Any, Dict, Optional
from pydantic import Field, model_validator

from .manifest_schema import ManifestSchema


class VnfsSchema(ManifestSchema):
    """Pydantic schema for a virtual NFS server.

    Extends ManifestSchema to represent a vNFS endpoint that exposes a single
    skill as a mountable filesystem (WebDAV or NFSv3).
    """

    port: Optional[int] = Field(
        default=None,
        description="Port for the vNFS server. Auto-assigned if None.",
        gt=0,
        lt=65536,
    )
    skill_uuid: Optional[str] = Field(
        default=None,
        description="UUID of the skill to expose as a filesystem",
    )
    protocol: str = Field(
        default="webdav",
        description="Network filesystem protocol: 'webdav' or 'nfs'",
    )
    npx_compat: bool = Field(
        default=False,
        description=(
            "When True and protocol is 'webdav', the vNFS also publishes a "
            "well-known agent-skills layout so 'npx skills add http://host:port' "
            "can install the skill. Only valid with protocol='webdav'."
        ),
    )

    @model_validator(mode="after")
    def _check_npx_compat_requires_webdav(self) -> "VnfsSchema":
        if self.npx_compat and self.protocol != "webdav":
            raise ValueError(
                "npx_compat=True requires protocol='webdav' "
                f"(got protocol='{self.protocol}'). "
                "The well-known agent-skills endpoint is HTTP-only; "
                "mount an NFS export locally and use 'npx skills add <path>' instead."
            )
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert the vnfs schema to a dictionary."""
        return self.model_dump(exclude_none=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VnfsSchema":
        """Create a VnfsSchema instance from a dictionary.

        Only passes known fields to avoid **kwargs issues.
        """
        valid_fields = cls.model_fields.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
