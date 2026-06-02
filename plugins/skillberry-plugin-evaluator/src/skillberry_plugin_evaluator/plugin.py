"""
Skillberry Plugin Evaluator - Minimal LLM-based content evaluation plugin.
Uses llm-switchboard for LLM integration.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class SkillberryPluginEvaluator(PluginBase):
    """Plugin for evaluating content and suggesting tags using LLM."""

    def __init__(self):
        super().__init__()
        
        self._metadata = PluginMetadata(
            name="Content Evaluator",
            version="0.1.0",
            description="Evaluate content and suggest tags using LLM",
            plugin_type=PluginType.EVALUATOR,
        )
        
        self.llm_client = None
        self._status_message = "Initializing..."
        
        # Try to initialize LLM client
        try:
            from llm_switchboard import get_llm
            
            # Get provider from environment (llm-switchboard reads its own env vars)
            provider_name = os.getenv("LLM_PROVIDER", "openai.async")
            model_name = os.getenv("LLM_MODEL", "gpt-4")
            
            logger.info(f"Initializing LLM: provider={provider_name}, model={model_name}")
            
            # Get the LLM client class
            LLMClientClass = get_llm(provider_name)
            
            # Instantiate the client (llm-switchboard reads env vars automatically)
            self.llm_client = LLMClientClass(model_name=model_name)
            self._status_message = f"Ready (using {provider_name})"
            
            logger.info(f"LLM client initialized successfully")
                
        except ImportError:
            self._status_message = "Missing dependency: llm-switchboard not installed"
            logger.warning("llm-switchboard not installed, plugin will be disabled")
        except Exception as e:
            self._status_message = f"Configuration error: {str(e)}"
            logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return self._metadata
    
    def get_status_message(self) -> str:
        """Return current plugin status."""
        return self._status_message

    def is_enabled(self) -> bool:
        """Plugin is enabled if LLM client is initialized."""
        return self.llm_client is not None

    async def evaluate_content(
        self, 
        uuid: str, 
        content_type: str,
        content: str,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate content and suggest tags using LLM.
        
        Args:
            uuid: Content UUID
            content_type: Type of content ("tool", "skill", "snippet")
            content: The actual content to evaluate
            name: Optional name of the content
            
        Returns:
            Dict with suggested_tags, confidence_scores, and summary
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")
        
        logger.info(f"Evaluating {content_type} {uuid}: {name or 'unnamed'}")
        
        # Build evaluation prompt
        prompt = f"""Analyze this {content_type} and suggest relevant tags.

Content name: {name or 'N/A'}
Content:
```
{content[:1000]}
```

Provide your analysis as JSON with:
- suggested_tags: array of 3-5 relevant tags (lowercase, hyphenated)
- confidence_scores: object mapping each tag to confidence (0.0-1.0)
- summary: brief one-sentence evaluation

Return ONLY the JSON, no other text."""
        
        logger.debug(f"Calling LLM with prompt: {prompt[:200]}...")
        response = await self.llm_client.generate_async(prompt=prompt)
        logger.info(f"Received response ({len(response)} chars)")
        
        # Parse response
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(response[start:end])
            else:
                # Fallback if no JSON found
                result = {
                    "suggested_tags": [],
                    "confidence_scores": {},
                    "summary": "Failed to parse LLM response"
                }
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            result = {
                "suggested_tags": [],
                "confidence_scores": {},
                "summary": f"Parse error: {str(e)}"
            }
        
        logger.info(f"Evaluation complete: {len(result.get('suggested_tags', []))} tags suggested")
        return result

    def get_router(self):
        """Register plugin routes."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        
        router = APIRouter()
        
        class EvaluateRequest(BaseModel):
            uuid: str
            content_type: str  # "tool", "skill", or "snippet"
            content: str
            name: Optional[str] = None
        
        @router.post("/evaluate")
        async def evaluate_endpoint(request: EvaluateRequest):
            """Evaluate content and suggest tags."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)
            
            try:
                result = await self.evaluate_content(
                    uuid=request.uuid,
                    content_type=request.content_type,
                    content=request.content,
                    name=request.name
                )
                return {
                    "success": True,
                    "uuid": request.uuid,
                    **result
                }
            except Exception as e:
                logger.error(f"Failed to evaluate content: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        return router
    
    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        """No CLI commands for this plugin."""
        return None
    
    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        """Return UI configuration for the plugin."""
        return {
            "icon": "CheckCircleIcon",
            "color": "#28A745",
            "actions": [
                {
                    "label": "Evaluate Content",
                    "endpoint": "/api/plugins/evaluator/evaluate",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "uuid": {
                                "type": "string",
                                "description": "UUID of the content to evaluate"
                            },
                            "content_type": {
                                "type": "string",
                                "enum": ["tool", "skill", "snippet"],
                                "description": "Type of content"
                            },
                            "content": {
                                "type": "string",
                                "description": "The content to evaluate"
                            },
                            "name": {
                                "type": "string",
                                "description": "Optional name of the content"
                            }
                        },
                        "required": ["uuid", "content_type", "content"]
                    }
                }
            ]
        }

# Made with Bob
