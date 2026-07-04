"""Plugin manifest model + loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class RequiredEnv(BaseModel):
    name: str
    description: str = ""
    required: bool = True
    default: Optional[str] = None


class PluginManifest(BaseModel):
    name: str
    slug: str
    version: str
    description: str = ""
    plugin_type: str = "evaluator"
    author: Optional[str] = None
    homepage: Optional[str] = None
    sdk_version: str = "^0.1"
    has_api: bool = False
    required_env: List[RequiredEnv] = Field(default_factory=list)
    port_hint: Optional[int] = None
    ui_config: Optional[Dict[str, Any]] = None

    def missing_env(self, env: Dict[str, str]) -> List[str]:
        """Return names of required env vars missing (empty string counts as missing)."""
        missing = []
        for spec in self.required_env:
            if not spec.required:
                continue
            v = env.get(spec.name, "")
            if not v:
                missing.append(spec.name)
        return missing


def load_manifest(path: str | Path) -> PluginManifest:
    """Load and validate a manifest.yaml file."""
    p = Path(path)
    data = yaml.safe_load(p.read_text()) or {}
    return PluginManifest.model_validate(data)
