"""
Skillberry Plugin Creator - Minimal LLM-based snippet creation plugin.
Uses llm-switchboard for LLM integration.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from skillberry_plugin_sdk import PluginLifecycleBase

logger = logging.getLogger(__name__)


class SkillberryPluginCreator(PluginLifecycleBase):
    """Plugin for creating snippets using LLM."""

    manifest_path = "manifest.yaml"

    def __init__(self, manifest=None):
        super().__init__(manifest=manifest)
        self.llm_client = None
        self._status_message = "Initializing..."

    async def on_start(self) -> None:
        """Initialize the LLM client on startup."""
        try:
            from llm_switchboard import get_llm

            provider_name = os.getenv("LLM_PROVIDER", "openai.async")
            model_name = os.getenv("LLM_MODEL", "gpt-4")

            logger.info(f"Initializing LLM: provider={provider_name}, model={model_name}")

            LLMClientClass = get_llm(provider_name)
            self.llm_client = LLMClientClass(model_name=model_name)
            self._status_message = f"Ready (using {provider_name})"

            logger.info("LLM client initialized successfully")

        except ImportError:
            self._status_message = "Missing dependency: llm-switchboard not installed"
            logger.warning("llm-switchboard not installed, plugin will be disabled")
        except Exception as e:
            self._status_message = f"Configuration error: {str(e)}"
            logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)

    async def is_ready(self) -> Dict[str, Any]:
        """Reflect LLM readiness."""
        ready = self.llm_client is not None
        return {
            "ready": ready,
            "missing_config": [] if ready else [self._status_message],
        }

    def is_enabled(self) -> bool:
        """Plugin is enabled if LLM client is initialized."""
        return self.llm_client is not None

    def get_status_message(self) -> str:
        """Return current plugin status."""
        return self._status_message

    async def create_snippet(self, description: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a code snippet from a description using LLM.

        Args:
            description: Natural language description of the snippet
            name: Optional name for the snippet

        Returns:
            Dict with snippet details (uuid, name, content, etc.)
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")

        if self._store is None:
            raise RuntimeError("Store API not available")

        logger.info(f"Creating snippet from description: {description[:100]}...")

        # Generate snippet content using LLM
        prompt = f"""Generate a code snippet based on this description:

{description}

Return only the code, no explanations or markdown formatting."""

        logger.debug(f"Calling LLM with prompt: {prompt[:200]}...")
        content = await self.llm_client.generate_async(prompt=prompt)
        logger.info(f"Generated content ({len(content)} chars)")

        # Infer metadata using LLM
        metadata_prompt = f"""Analyze this code snippet and provide metadata in JSON format:

```
{content[:500]}
```

Return a JSON object with:
- language: programming language (e.g., "python", "javascript")
- tags: array of relevant tags (e.g., ["function", "utility"])
- description: brief description (one sentence)

Return ONLY the JSON, no other text."""

        logger.debug("Inferring metadata...")
        metadata_str = await self.llm_client.generate_async(prompt=metadata_prompt)

        # Parse metadata (simple extraction, could be improved)
        try:
            start = metadata_str.find("{")
            end = metadata_str.rfind("}") + 1
            if start >= 0 and end > start:
                metadata = json.loads(metadata_str[start:end])
            else:
                metadata = {"language": "text", "tags": [], "description": description[:100]}
        except Exception:
            logger.warning("Failed to parse metadata, using defaults")
            metadata = {"language": "text", "tags": [], "description": description[:100]}

        logger.info(f"Inferred metadata: {metadata}")

        snippet_name = name or metadata.get("description", "Generated snippet")[:50]

        snippet_data = {
            "name": snippet_name,
            "content": content,
            "language": metadata.get("language", "text"),
            "tags": metadata.get("tags", []),
            "description": metadata.get("description", description[:200]),
        }

        logger.info(f"Saving snippet: {snippet_name}")
        created_snippet = await self.store.post("/snippets/", json=snippet_data)
        logger.info(f"Snippet created with UUID: {created_snippet.get('uuid') if isinstance(created_snippet, dict) else '?'}")

        return created_snippet

    def get_router(self):
        """Register plugin routes."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        class CreateSnippetRequest(BaseModel):
            description: str
            name: Optional[str] = None

        @router.post("/create-snippet")
        async def create_snippet_endpoint(request: CreateSnippetRequest):
            """Create a code snippet from a description."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)

            try:
                result = await self.create_snippet(
                    description=request.description,
                    name=request.name,
                )
                return {
                    "success": True,
                    "message": f"Snippet '{result['name']}' created successfully.",
                    "name": result["name"],
                    "uuid": result["uuid"],
                }
            except Exception as e:
                logger.error(f"Failed to create snippet: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        return router
