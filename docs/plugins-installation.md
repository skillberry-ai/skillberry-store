# Plugin Installation Guide

## Overview

The skillberry-store supports a flexible plugin architecture that allows extending functionality without modifying core code. Plugins can be installed individually or all at once.

## Installation Options

### 1. Install Without Plugins (Minimal Installation)

When you install skillberry-store, two plugins are included by default:

```bash
pip install skillberry-store
```

This installs:
- Core skillberry-store functionality
- skillberry-plugin-dedupe (AI-powered duplicate skill detection) — **default**
- skillberry-plugin-kagenti-approver (automatic kagenti-approved labeling) — **default**

Both default plugins can be uninstalled individually if not needed:
```bash
pip uninstall skillberry-plugin-dedupe
pip uninstall skillberry-plugin-kagenti-approver
```

### 2. Install All Plugins

To install all available plugins:

```bash
pip install skillberry-store[plugins-all]
```

This installs:
- Core skillberry-store functionality
- skillberry-plugin-creator (AI-powered content creation)
- skillberry-plugin-evaluator (AI-powered content evaluation and tagging)
- skillberry-plugin-security (AI-powered security evaluation)
- skillberry-plugin-dedupe (AI-powered duplicate skill detection) — also a default plugin
- skillberry-plugin-mcp-importer (import tools from any MCP SSE server)
- skillberry-plugin-anthropic-skill-generator (generate Anthropic skills from descriptions using Claude Code)
- skillberry-plugin-kagenti-approver (automatic kagenti-approved labeling) — also a default plugin

### 3. Install Specific Plugins

If you want to install only specific plugins, use the optional dependency syntax:

#### Creator Plugin Only
```bash
pip install skillberry-store[plugin-creator]
```

#### Evaluator Plugin Only
```bash
pip install skillberry-store[plugin-evaluator]
```

#### Dedupe Plugin Only
```bash
pip install skillberry-store[plugin-dedupe]
```

#### MCP Importer Plugin Only
```bash
pip install skillberry-store[plugin-mcp-importer]
```

#### Anthropic Skill Generator Plugin Only
```bash
pip install skillberry-store[plugin-anthropic-skill-generator]
```

#### Kagenti Approver Plugin Only
```bash
pip install skillberry-store[plugin-kagenti-approver]
```

#### Multiple Specific Plugins
```bash
pip install skillberry-store[plugin-creator,plugin-evaluator,plugin-mcp-importer,plugin-anthropic-skill-generator]
```

### 4. Adding Plugins Later

If you initially installed skillberry-store without plugins, you can add them later:

```bash
# Add all plugins to existing installation
pip install skillberry-plugin-creator skillberry-plugin-evaluator skillberry-plugin-security skillberry-plugin-dedupe skillberry-plugin-mcp-importer skillberry-plugin-anthropic-skill-generator

# Or reinstall with plugins
pip install --upgrade skillberry-store[plugins-all]
```

The store will automatically discover and load newly installed plugins on the next restart.

## Development Workflow

### Running Without Plugins (Development)

When developing skillberry-store from source:

```bash
# Clone the repository
git clone https://github.com/skillberry-ai/skillberry-store.git
cd skillberry-store

# Run without plugins (default)
make run
```

This runs `uv pip install -e .` which installs only the core dependencies (no plugins).

### Running With Plugins (Development)

To run with plugins during development:

```bash
# Install with all plugins
make install-requirements ODEPS=plugins-all

# Or install specific plugins
make install-requirements ODEPS=plugin-creator
make install-requirements ODEPS=plugin-evaluator

# Then run
make run
```

The `ODEPS` variable specifies optional dependencies (extras) to install.

## Available Plugins

### Creator Plugin (`skillberry-plugin-creator`)

**Purpose:** AI-powered snippet creation using LLM.

**Features:**
- Generate code snippets from natural language descriptions
- Automatic metadata inference (language, tags)
- Supports multiple LLM providers via llm-switchboard

**Configuration:**
```bash
export LLM_PROVIDER=openai.async  # or litellm, etc.
export LLM_MODEL=gpt-4
# Provider-specific variables (e.g., OPENAI_API_KEY)
```

**API Endpoints:**
- `POST /api/plugins/skillberry-plugin-creator/create-snippet`

**Example:**
```bash
curl -X POST http://localhost:8000/api/plugins/skillberry-plugin-creator/create-snippet \
  -H "Content-Type: application/json" \
  -d '{"description": "Python fibonacci function", "name": "fibonacci"}'
```

### Evaluator Plugin (`skillberry-plugin-evaluator`)

**Purpose:** AI-powered content evaluation and automatic tagging.

**Features:**
- Evaluate content and suggest relevant tags
- Confidence scores for each tag
- Supports multiple LLM providers via llm-switchboard

**Configuration:**
```bash
export LLM_PROVIDER=openai.async  # or litellm, etc.
export LLM_MODEL=gpt-4
# Provider-specific variables (e.g., OPENAI_API_KEY)
```

**API Endpoints:**
- `POST /api/plugins/skillberry-plugin-evaluator/evaluate`

**Example:**
```bash
curl -X POST http://localhost:8000/api/plugins/skillberry-plugin-evaluator/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "abc-123",
    "content_type": "snippet",
    "content": "def hello():\n    print(\"Hello\")",
    "name": "Hello World"
  }'
```

### Dedupe Plugin (`skillberry-plugin-dedupe`)

**Purpose:** AI-powered duplicate skill detection using LLM.

**Features:**
- Automatically detects semantically duplicate skills when a skill is created or updated
- Compares descriptions (not names) against all existing original skills in a single LLM call
- Tags duplicate skills with `duplicate:{skill-name}` (additive — never removes existing tags)
- Records similarity explanations in `extra["duplicate_analysis"]`
- Handles multiple duplicates: adds one tag per match found

**Configuration:**
```bash
export LLM_PROVIDER=openai.async  # or litellm, etc.
export LLM_MODEL=gpt-4
# Provider-specific variables (e.g., OPENAI_API_KEY)
```

**Trigger events:** `content_added:skill`, `content_updated:skill`

**No API endpoints** — the plugin operates automatically in the background via event handlers.

**Example output on a duplicate skill:**

Tags added:
```
duplicate:web-search-tool
```

Metadata added to `extra`:
```json
{
  "duplicate_analysis": {
    "web-search-tool": "Both skills describe performing web searches and returning ranked results."
  }
}
```

### MCP Importer Plugin (`skillberry-plugin-mcp-importer`)

**Purpose:** Import tools from any customer MCP server into the store via SSE — no LLM required.

**Features:**
- Connects to a customer's MCP server via SSE and lists all exposed tools
- Creates each tool in the store with `packaging_format="mcp"`, preserving the original tool's schema and description
- Tools are immediately executable via the store's existing MCP execution path (VMCP tunnel)
- Each import call produces fresh UUIDs — duplicate names are allowed
- Invalid or unreachable URLs return a clear error immediately

**Configuration:** None required. The MCP server URL is supplied per-request.

**API Endpoints:**
- `POST /plugins/mcp-importer/import-tools`

**Request body:**
```json
{ "mcp_url": "http://your-mcp-server/sse" }
```

**Response:**
```json
{
  "imported": 2,
  "tools": [
    { "name": "echo", "uuid": "abc-123" },
    { "name": "add_numbers", "uuid": "def-456" }
  ],
  "failed": []
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/plugins/mcp-importer/import-tools \
  -H "Content-Type: application/json" \
  -d '{"mcp_url": "http://my-mcp-server:8080/sse"}'
```

**Error responses:**
- `400` — `mcp_url` is missing or does not start with `http://` / `https://`
- `502` — Could not connect to the MCP server (unreachable, refused, or timed out)

### Anthropic Skill Generator Plugin (`skillberry-plugin-anthropic-skill-generator`)

**Purpose:** Generate complete Anthropic skills from natural language descriptions using Claude Code via runspace-agent.

**Features:**
- Generates complete Anthropic skills (SKILL.md, tools, documentation) from descriptions
- Uses Claude Code AI agent for intelligent skill creation
- Automatically imports generated skills into the store
- Supports both local and container execution modes (container is default for safety)
- Auto-loads credentials from `~/.claude/settings.json` if available
- Includes skill-creator preinstalled skill for better generation quality

**Configuration:**

The plugin automatically loads credentials from `~/.claude/settings.json` if it exists:
```json
{
  "apiKey": "sk-ant-...",
  "model": "claude-opus-4-8",
  "baseUrl": "https://api.anthropic.com"
}
```

Or configure via environment variables:
```bash
# Option 1: Direct Anthropic API
export ANTHROPIC_API_KEY="sk-ant-..."

# Option 2: Proxy/Gateway
export ANTHROPIC_BASE_URL="https://your-gateway.example.com"
export ANTHROPIC_AUTH_TOKEN="your-token"
export ANTHROPIC_MODEL="claude-opus-4-8"

# Execution mode (default: container - requires Docker)
export RUNSPACE_MODE="container"  # or "local" for development

# Max conversation turns (default: 300)
export RUNSPACE_MAX_TURNS="300"
```

**Requirements:**
- Docker (for default container mode - recommended)
- Anthropic API credentials (API key or proxy configuration)

**API Endpoints:**
- `POST /api/plugins/anthropic-skill-generator/generate-skill`

**Request body:**
```json
{
  "description": "A skill for processing PDF documents and extracting text",
  "skill_name": "pdf-processor",
  "tags": ["pdf", "document-processing"],
  "max_turns": 50
}
```

**Response:**
```json
{
  "success": true,
  "message": "Skill 'pdf-processor' generated successfully.",
  "skill_name": "pdf-processor",
  "skill_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "tools_count": 3,
  "snippets_count": 2
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/plugins/anthropic-skill-generator/generate-skill \
  -H "Content-Type: application/json" \
  -d '{
    "description": "A skill for processing PDF documents and extracting text with OCR support",
    "skill_name": "pdf-processor",
    "tags": ["pdf", "ocr"]
  }'
```

**Configuration Priority:**
1. Request-specific parameters (highest)
2. Environment variables
3. `~/.claude/settings.json` (lowest - automatic)

### Kagenti Approver Plugin (`skillberry-plugin-kagenti-approver`)

**Purpose:** Automatically label skills as `kagenti-approved` when their score tags satisfy configurable criteria.

**Features:**
- Reacts to `content_added:skill` and `content_updated:skill` events — no manual trigger needed
- Adds `kagenti-approved` tag when all criteria in any OR-group are met
- Removes `kagenti-approved` tag when criteria are no longer met (revocation on update)
- No-op if approval state has not changed (avoids unnecessary writes)
- No LLM or external dependencies

**Configuration:**
```bash
# Optional — defaults to "security-score>=9,performance-score>=8" if not set
export KAGENTI_CRITERIA="security-score>=9,performance-score>=8"
```

**Criteria syntax:**
- `,` = AND (all conditions in a group must pass)
- `|` = OR (any group passing is sufficient)
- Supported operators: `>=`, `>`, `<=`, `<`, `=`, `!=`
- Each condition: `{tag-prefix}{operator}{number}` (e.g. `security-score>=9`)

**Examples:**
```bash
# Default: both scores required
KAGENTI_CRITERIA="security-score>=9,performance-score>=8"

# Either a perfect security score, or both scores at lower thresholds
KAGENTI_CRITERIA="security-score>=10|security-score>=7,performance-score>=8"
```

**No API endpoints** — operates entirely in the background via event handlers.

## LLM Configuration

Both plugins use `llm-switchboard` for LLM integration. Configuration is done via environment variables.

### Common Providers

#### OpenAI
```bash
export LLM_PROVIDER=openai.async
export LLM_MODEL=gpt-4
export OPENAI_API_KEY=your_key
```

#### LiteLLM (supports 100+ providers)
```bash
export LLM_PROVIDER=litellm
export LLM_MODEL=your-model-name
export OPENAI_API_KEY=your_key
export OPENAI_API_BASE=https://your-endpoint.com
```

See [llm-switchboard documentation](https://github.com/skillberry-ai/llm-switchboard) for more providers and configuration options.

## Plugin Development

### Creating a New Plugin

Plugins are separate Python packages with this structure:

```
my-plugin/
├── pyproject.toml
├── README.md
├── src/
│   └── my_plugin/
│       ├── __init__.py
│       └── plugin.py
└── tests/
    └── test_plugin.py
```

**Minimal Plugin Example:**

```python
# src/my_plugin/plugin.py
from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType

class MyPlugin(PluginBase):
    def __init__(self):
        metadata = PluginMetadata(
            name="my-plugin",
            version="0.1.0",
            description="My custom plugin",
            plugin_type=PluginType.GENERAL,
        )
        super().__init__(metadata)
    
    def is_enabled(self) -> bool:
        return True
    
    def get_routes(self):
        from fastapi import APIRouter
        router = APIRouter()
        
        @router.get("/hello")
        async def hello():
            return {"message": "Hello from my plugin"}
        
        return router
```

**pyproject.toml:**

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-plugin"
version = "0.1.0"
description = "My custom plugin"
requires-python = ">=3.10"
dependencies = []

[tool.setuptools]
packages = ["my_plugin"]
package-dir = {"" = "src"}
```

### Adding Plugin to Store

1. Create plugin package in `plugins/` directory
2. Add to main `pyproject.toml`:

```toml
[project.optional-dependencies]
plugin-my-plugin = ["my-plugin>=0.1.0"]
plugins-all = [
    "my-plugin>=0.1.0",
    # ... other plugins
]

[tool.uv.sources]
my-plugin = { path = "plugins/my-plugin", editable = true }
```

## Troubleshooting

### Plugin Not Loading

1. Check plugin is installed: `pip list | grep skillberry-plugin`
2. Check logs for import errors
3. Verify environment variables are set

### LLM Configuration Issues

1. Verify environment variables: `env | grep LLM`
2. Check API key is valid
3. Review plugin logs for detailed error messages

### Removing Plugins

```bash
# Uninstall all plugins
pip uninstall -y skillberry-plugin-creator skillberry-plugin-evaluator skillberry-plugin-security skillberry-plugin-dedupe skillberry-plugin-mcp-importer skillberry-plugin-anthropic-skill-generator

# Verify removal
pip list | grep skillberry-plugin
```

### Re-installing Plugins

```bash
# For development (from source)
make install-requirements ODEPS=plugins-all

# For production (from PyPI)
pip install --upgrade skillberry-store[plugins-all]
```

## Support

For plugin-related issues:
- GitHub Issues: https://github.com/skillberry-ai/skillberry-store/issues
- Documentation: https://github.com/skillberry-ai/skillberry-store/tree/main/docs
- Examples: See `plugins/` directory for reference implementations