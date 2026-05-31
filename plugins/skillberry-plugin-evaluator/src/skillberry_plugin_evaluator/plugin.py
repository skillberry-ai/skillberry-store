"""AI-powered content evaluator plugin using llm-switchboard."""

import os
from typing import Optional, Dict, Any, List
from fastapi import APIRouter
from pydantic import BaseModel
import click

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType


class EvaluateRequest(BaseModel):
    """Request to evaluate content."""
    uuid: str
    content_type: str  # "tool", "skill", or "snippet"
    force: bool = False  # Re-evaluate even if already evaluated


class EvaluateResponse(BaseModel):
    """Response from evaluation."""
    success: bool
    uuid: str
    suggested_tags: List[str]
    confidence_scores: Dict[str, float]
    evaluation_summary: str
    applied: bool  # Whether tags were applied


class BatchEvaluateRequest(BaseModel):
    """Request to batch evaluate content."""
    content_type: str
    filter: Optional[Dict] = None
    max_items: int = 100


class EvaluatorPlugin(PluginBase):
    """AI-powered content evaluator using llm-switchboard for multi-LLM support.
    
    Supports multiple LLM providers via llm-switchboard:
    - OpenAI (openai.async)
    - Azure OpenAI (azure_openai.async)
    - WatsonX (watsonx)
    - LiteLLM (litellm) - supports 100+ providers
    - Auto-detection from environment (auto_from_env)
    
    Configuration via environment variables:
    - LLM_PROVIDER: Provider name (default: "openai.async")
    - LLM_API_KEY: API key for the provider
    - LLM_MODEL: Model name (optional, provider-specific default used)
    - LLM_BASE_URL: Custom base URL (optional)
    """
    
    def __init__(self):
        super().__init__()
        self.llm_client = None
        self.provider_name = None
        self._status_message = "Initializing..."
        
        # Try to initialize llm-switchboard client
        try:
            from llm_switchboard import get_llm
            
            # Get provider from environment (default to async OpenAI)
            provider_name = os.getenv("LLM_PROVIDER", "openai.async")
            api_key = os.getenv("LLM_API_KEY")
            
            if not api_key:
                self._status_message = "Missing LLM_API_KEY environment variable. Set it to enable this plugin."
            else:
                # Get the LLM client class
                LLMClientClass = get_llm(provider_name)
                
                # Build provider kwargs
                provider_kwargs = {"api_key": api_key}
                
                # Add optional parameters
                model = os.getenv("LLM_MODEL")
                if model:
                    provider_kwargs["model"] = model
                
                base_url = os.getenv("LLM_BASE_URL")
                if base_url:
                    provider_kwargs["base_url"] = base_url
                
                # Initialize the client
                # Type ignore: LLMClient subclasses have different signatures
                self.llm_client = LLMClientClass(**provider_kwargs)  # type: ignore
                self.provider_name = provider_name
                self._status_message = f"Ready (using {provider_name})"
                
        except ImportError:
            # llm-switchboard not installed, plugin will be disabled
            self._status_message = "Missing dependency: llm-switchboard package not installed. Install it to enable this plugin."
        except Exception as e:
            # Configuration error, plugin will be disabled
            self._status_message = f"Configuration error: {str(e)}"
            print(f"Failed to initialize LLM client: {e}")
    
    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        provider_info = f" (using {self.provider_name})" if self.provider_name else ""
        return PluginMetadata(
            name="AI Content Evaluator",
            description=f"Automatically evaluate and tag content using AI{provider_info}",
            version="0.2.0",
            plugin_type=PluginType.EVALUATOR,
            author="Skillberry Team",
            homepage="https://github.com/skillberry-ai/skillberry-plugin-evaluator"
        )
    
    def is_enabled(self) -> bool:
        """Plugin is enabled if LLM client is configured."""
        return self.llm_client is not None
    
    def get_status_message(self) -> str:
        """Get human-readable status message."""
        return self._status_message
    
    def get_router(self) -> Optional[APIRouter]:
        """Provide plugin's API routes."""
        router = APIRouter()
        
        @router.post("/evaluate", response_model=EvaluateResponse)
        async def evaluate_content(request: EvaluateRequest):
            """Evaluate a single piece of content."""
            if not self.is_enabled():
                return EvaluateResponse(
                    success=False,
                    uuid=request.uuid,
                    suggested_tags=[],
                    confidence_scores={},
                    evaluation_summary="LLM not configured. Set LLM_API_KEY environment variable.",
                    applied=False
                )
            
            # TODO: Implement actual evaluation logic
            return EvaluateResponse(
                success=True,
                uuid=request.uuid,
                suggested_tags=["python", "utility"],
                confidence_scores={"python": 0.95, "utility": 0.80},
                evaluation_summary="Evaluation not yet implemented",
                applied=False
            )
        
        @router.post("/batch-evaluate")
        async def batch_evaluate(request: BatchEvaluateRequest):
            """Evaluate multiple items."""
            if not self.is_enabled():
                return {
                    "success": False,
                    "message": "LLM not configured"
                }
            
            # TODO: Implement batch evaluation
            return {
                "evaluated": 0,
                "results": [],
                "message": "Batch evaluation not yet implemented"
            }
        
        @router.get("/stats")
        async def get_evaluation_stats():
            """Get evaluation statistics."""
            # TODO: Implement stats collection
            return {
                "total": 0,
                "success_rate": 0.0,
                "avg_tags_per_item": 0.0,
                "most_common_tags": []
            }
        
        return router
    
    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        """Provide plugin's CLI commands."""
        
        @click.command()
        @click.option('--uuid', required=True, help='UUID of content to evaluate')
        @click.option('--type', 'content_type', required=True,
                     type=click.Choice(['tool', 'skill', 'snippet']))
        @click.option('--force', is_flag=True, help='Re-evaluate even if already done')
        def evaluate(uuid: str, content_type: str, force: bool):
            """Evaluate a single item."""
            click.echo(f"Evaluating {content_type} {uuid}")
            # TODO: Implement actual evaluation
        
        @click.command()
        @click.option('--type', 'content_type', required=True,
                     type=click.Choice(['tool', 'skill', 'snippet']))
        @click.option('--filter', help='Filter criteria (JSON)')
        @click.option('--max-items', default=100, help='Maximum items to evaluate')
        def batch(content_type: str, filter: Optional[str], max_items: int):
            """Batch evaluate multiple items."""
            click.echo(f"Batch evaluating {content_type}s")
            # TODO: Implement batch evaluation
        
        @click.command()
        def stats():
            """Show evaluation statistics."""
            click.echo("Evaluation statistics:")
            # TODO: Implement stats display
        
        return {
            "evaluate": evaluate,
            "batch": batch,
            "stats": stats
        }
    
    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        """Provide plugin's UI configuration."""
        return {
            "icon": "CheckCircleIcon",
            "color": "#3E8635",
            "actions": [
                {
                    "label": "Evaluate Content",
                    "description": "Analyze and tag content using AI",
                    "endpoint": "/plugins/evaluator/evaluate",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "uuid": {
                                "type": "string",
                                "description": "Content UUID"
                            },
                            "content_type": {
                                "type": "string",
                                "enum": ["tool", "skill", "snippet"],
                                "description": "Type of content"
                            },
                            "force": {
                                "type": "boolean",
                                "default": False,
                                "description": "Re-evaluate even if already done"
                            }
                        },
                        "required": ["uuid", "content_type"]
                    }
                },
                {
                    "label": "Batch Evaluate",
                    "description": "Evaluate multiple items at once",
                    "endpoint": "/plugins/evaluator/batch-evaluate",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "content_type": {
                                "type": "string",
                                "enum": ["tool", "skill", "snippet"],
                                "description": "Type of content"
                            },
                            "max_items": {
                                "type": "integer",
                                "default": 100,
                                "description": "Maximum items to evaluate"
                            }
                        },
                        "required": ["content_type"]
                    }
                },
                {
                    "label": "View Statistics",
                    "description": "See evaluation statistics",
                    "endpoint": "/plugins/evaluator/stats",
                    "method": "GET"
                }
            ],
            "settings_schema": {
                "type": "object",
                "properties": {
                    "auto_evaluate": {
                        "type": "boolean",
                        "default": True,
                        "description": "Automatically evaluate new content"
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "default": 0.7,
                        "description": "Minimum confidence to apply tags"
                    }
                }
            }
        }

# Made with Bob
