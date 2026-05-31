# Plugin Installation Guide

## Overview

The skillberry-store supports a flexible plugin architecture that allows extending functionality without modifying core code. Plugins can be installed individually or all at once.

## Installation Options

### 1. Install All Plugins (Default)

When you install skillberry-store without any extras, all plugins are included by default:

```bash
pip install skillberry-store
```

This installs:
- Core skillberry-store functionality
- skillberry-plugin-creator (AI-powered content generation)
- skillberry-plugin-evaluator (AI-powered content evaluation and tagging)

### 2. Install Specific Plugins

If you want to install only specific plugins, use the optional dependency syntax:

#### Creator Plugin Only
```bash
pip install skillberry-store[plugin-creator]
```

#### Evaluator Plugin Only
```bash
pip install skillberry-store[plugin-evaluator]
```

#### Multiple Specific Plugins
```bash
pip install skillberry-store[plugin-creator,plugin-evaluator]
```

### 3. Install All Plugins Explicitly

You can also explicitly request all plugins:

```bash
pip install skillberry-store[plugins-all]
```

### 4. Install Without Plugins

If you want to install skillberry-store without any plugins (minimal installation), you would need to:

1. Clone the repository
2. Modify `pyproject.toml` to remove plugin dependencies from the main `dependencies` list
3. Install with `pip install -e .`

Alternatively, wait for a future release that may support a `minimal` extra.

## Available Plugins

### Creator Plugin (`skillberry-plugin-creator`)

**Purpose:** AI-powered content generation for skills, tools, and snippets.

**Features:**
- Generate new skills from natural language descriptions
- Create tools with proper schemas and implementations
- Generate code snippets with context-aware suggestions
- Supports 100+ LLM providers via llm-switchboard

**Configuration:**
```bash
export LLM_PROVIDER="openai.async"  # or azure, watsonx, litellm, etc.
export LLM_API_KEY="your-api-key"
export LLM_MODEL="gpt-4"  # optional, provider-specific default used otherwise
```

**API Endpoints:**
- `POST /api/plugins/creator/generate-skill`
- `POST /api/plugins/creator/generate-tool`
- `POST /api/plugins/creator/generate-snippet`

### Evaluator Plugin (`skillberry-plugin-evaluator`)

**Purpose:** AI-powered content evaluation and automatic tagging.

**Features:**
- Evaluate content quality and completeness
- Automatically generate relevant tags
- Assess documentation quality
- Identify potential improvements
- Supports 100+ LLM providers via llm-switchboard

**Configuration:**
```bash
export LLM_PROVIDER="openai.async"  # or azure, watsonx, litellm, etc.
export LLM_API_KEY="your-api-key"
export LLM_MODEL="gpt-4"  # optional, provider-specific default used otherwise
```

**API Endpoints:**
- `POST /api/plugins/evaluator/evaluate`
- `POST /api/plugins/evaluator/suggest-tags`

**Event Hooks:**
- Automatically evaluates content when added/updated (if configured)

## Plugin Development

### Creating a New Plugin

Plugins are separate Python packages that follow this structure:

```
my-plugin/
├── pyproject.toml
├── src/
│   └── my_plugin/
│       ├── __init__.py
│       └── plugin.py
└── tests/
    └── test_plugin.py
```

**Key Requirements:**

1. **Entry Point Declaration** in `pyproject.toml`:
```toml
[project.entry-points."skillberry_store.plugins"]
my-plugin = "my_plugin.plugin:MyPlugin"
```

2. **Plugin Class** inheriting from `PluginBase`:
```python
from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType

class MyPlugin(PluginBase):
    def __init__(self):
        super().__init__(
            metadata=PluginMetadata(
                name="my-plugin",
                version="0.1.0",
                description="My custom plugin",
                author="Your Name",
                plugin_type=PluginType.PROCESSOR
            )
        )
    
    def get_router(self):
        # Return FastAPI router for API endpoints
        pass
    
    def get_cli_commands(self):
        # Return CLI commands
        pass
    
    def get_ui_config(self):
        # Return UI configuration
        pass
```

3. **Event Handlers** (optional):
```python
from skillberry_store.plugins.events import on_content_added

@on_content_added("skill")
async def handle_skill_added(content_type: str, content_id: str, content: dict, store_api):
    # Process newly added skill
    pass
```

### Adding Plugin to Store

1. Create plugin package in `plugins/` directory
2. Add to `pyproject.toml`:
   - Add to main `dependencies` for default installation
   - Add to `[project.optional-dependencies]` for optional installation
   - Add to `[tool.uv.sources]` for local development

Example:
```toml
[project]
dependencies = [
    # ... other deps ...
    "my-plugin>=0.1.0",
]

[project.optional-dependencies]
plugin-my-plugin = ["my-plugin>=0.1.0"]

[tool.uv.sources]
my-plugin = { path = "plugins/my-plugin", editable = true }
```

## LLM Provider Support

Both creator and evaluator plugins use `llm-switchboard` for multi-provider LLM support.

### Supported Providers

- **OpenAI**: `openai.async`, `openai.sync`
- **Azure OpenAI**: `azure.async`, `azure.sync`
- **IBM WatsonX**: `watsonx.async`, `watsonx.sync`
- **LiteLLM**: `litellm.async`, `litellm.sync` (supports 100+ providers)
- **Anthropic**: `anthropic.async`, `anthropic.sync`
- **Google**: `google.async`, `google.sync`
- And many more...

### Configuration Examples

#### OpenAI
```bash
export LLM_PROVIDER="openai.async"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4"
```

#### Azure OpenAI
```bash
export LLM_PROVIDER="azure.async"
export LLM_API_KEY="your-azure-key"
export AZURE_ENDPOINT="https://your-resource.openai.azure.com/"
export LLM_MODEL="gpt-4"
```

#### IBM WatsonX
```bash
export LLM_PROVIDER="watsonx.async"
export LLM_API_KEY="your-watsonx-key"
export WATSONX_URL="https://us-south.ml.cloud.ibm.com"
export WATSONX_PROJECT_ID="your-project-id"
export LLM_MODEL="ibm/granite-13b-chat-v2"
```

#### LiteLLM (Universal Proxy)
```bash
export LLM_PROVIDER="litellm.async"
export LLM_API_KEY="your-api-key"
export LLM_MODEL="gpt-4"  # or any model supported by LiteLLM
```

## Troubleshooting

### Plugin Not Loading

1. Check plugin is installed: `pip list | grep skillberry-plugin`
2. Verify entry point: `python -c "from importlib.metadata import entry_points; print([ep for ep in entry_points().get('skillberry_store.plugins', [])])"`
3. Check logs for import errors
4. Ensure all plugin dependencies are installed

### LLM Configuration Issues

1. Verify environment variables are set: `echo $LLM_PROVIDER`
2. Check API key is valid
3. Test provider connection independently
4. Review plugin logs for detailed error messages

### Development Mode

For local plugin development:

```bash
# Install in editable mode
cd plugins/my-plugin
pip install -e .

# Verify installation
python -c "from my_plugin.plugin import MyPlugin; print(MyPlugin().metadata)"
```

## Future Enhancements

Planned improvements to the plugin system:

1. **Plugin Marketplace**: Central registry for community plugins
2. **Hot Reload**: Dynamic plugin loading without restart
3. **Plugin Dependencies**: Plugins that depend on other plugins
4. **Minimal Installation**: `pip install skillberry-store[minimal]` without any plugins
5. **Plugin Versioning**: Better version compatibility checking
6. **Plugin Configuration UI**: Web interface for plugin settings
7. **Plugin Metrics**: Usage statistics and performance monitoring

## Contributing

To contribute a new plugin:

1. Create plugin following the structure above
2. Add comprehensive tests
3. Document configuration and usage
4. Submit PR to skillberry-store repository
5. Plugin will be reviewed and potentially included in default installation

## Support

For plugin-related issues:
- GitHub Issues: https://github.com/skillberry-ai/skillberry-store/issues
- Documentation: https://github.com/skillberry-ai/skillberry-store/tree/main/docs
- Examples: See `plugins/` directory for reference implementations