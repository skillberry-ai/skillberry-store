"""AI-powered content creator plugin using llm-switchboard."""

import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import click

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType


class AICreatorPlugin(PluginBase):
    """AI-powered content creator using llm-switchboard for multi-LLM support.
    
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
            name="AI Content Creator",
            description=f"Generate tools, skills, and snippets using AI{provider_info}",
            version="0.2.0",
            plugin_type=PluginType.CREATOR,
            author="Skillberry Team",
            homepage="https://github.com/skillberry-ai/skillberry-plugin-creator"
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
        
        class CreateRequest(BaseModel):
            description: str
            name: Optional[str] = None
        
        @router.post("/create-tool")
        async def create_tool(request: CreateRequest = Body(...)):
            """Generate a Python tool from description."""
            if not self.is_enabled():
                raise HTTPException(
                    status_code=503,
                    detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
                )
            
            # TODO: Implement actual tool generation
            return {
                "success": True,
                "content_type": "tool",
                "message": f"Tool creation not yet implemented: {request.description}"
            }
        
        @router.post("/create-skill")
        async def create_skill(request: CreateRequest = Body(...)):
            """Generate a skill bundle from description."""
            if not self.is_enabled():
                raise HTTPException(
                    status_code=503,
                    detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
                )
            
            # TODO: Implement actual skill generation
            return {
                "success": True,
                "content_type": "skill",
                "message": f"Skill creation not yet implemented: {request.description}"
            }
        
        @router.post("/create-snippet")
        async def create_snippet(request: CreateRequest = Body(...)):
            """Generate a code snippet from description."""
            if not self.is_enabled():
                raise HTTPException(
                    status_code=503,
                    detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
                )
            
            # TODO: Implement actual snippet generation
            return {
                "success": True,
                "content_type": "snippet",
                "message": f"Snippet creation not yet implemented: {request.description}"
            }
        
        return router
    
    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        """Provide plugin's CLI commands."""
        
        @click.command()
        @click.option('--description', required=True, help='Description of tool to create')
        @click.option('--name', help='Optional name for the tool')
        def create_tool(description: str, name: Optional[str] = None):
            """Create a new tool using AI."""
            click.echo(f"Creating tool: {description}")
            # TODO: Implement actual creation
        
        @click.command()
        @click.option('--description', required=True, help='Description of skill to create')
        @click.option('--name', help='Optional name for the skill')
        def create_skill(description: str, name: Optional[str] = None):
            """Create a new skill using AI."""
            click.echo(f"Creating skill: {description}")
            # TODO: Implement actual creation
        
        @click.command()
        @click.option('--description', required=True, help='Description of snippet to create')
        @click.option('--name', help='Optional name for the snippet')
        def create_snippet(description: str, name: Optional[str] = None):
            """Create a new snippet using AI."""
            click.echo(f"Creating snippet: {description}")
            # TODO: Implement actual creation
        
        return {
            "create-tool": create_tool,
            "create-skill": create_skill,
            "create-snippet": create_snippet
        }
    
    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        """Provide plugin's UI configuration."""
        return {
            "icon": "PlusCircleIcon",
            "color": "#0066CC",
            "actions": [
                {
                    "label": "Create Tool",
                    "description": "Generate a Python tool from description",
                    "endpoint": "/plugins/creator/create-tool",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "What the tool should do"
                            },
                            "name": {
                                "type": "string",
                                "description": "Optional name for the tool"
                            }
                        },
                        "required": ["description"]
                    }
                },
                {
                    "label": "Create Skill",
                    "description": "Generate a skill bundle from description",
                    "endpoint": "/plugins/creator/create-skill",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "What the skill should do"
                            },
                            "name": {
                                "type": "string",
                                "description": "Optional name for the skill"
                            }
                        },
                        "required": ["description"]
                    }
                },
                {
                    "label": "Create Snippet",
                    "description": "Generate a code snippet from description",
                    "endpoint": "/plugins/creator/create-snippet",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "What the snippet should do"
                            },
                            "name": {
                                "type": "string",
                                "description": "Optional name for the snippet"
                            }
                        },
                        "required": ["description"]
                    }
                }
            ]
        }

# Made with Bob
