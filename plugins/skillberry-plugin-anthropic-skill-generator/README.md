# Skillberry Plugin: Anthropic Skill Generator

A Skillberry Store plugin that generates Anthropic skills from natural language descriptions using [runspace-agent](https://pypi.org/project/runspace-agent/0.1.0/).

## Overview

This plugin allows you to create complete Anthropic skills by simply providing a description. It uses the runspace-agent library with Claude Code to generate the skill structure (SKILL.md and associated files), then automatically imports the generated skill into the Skillberry Store.

**Important:** This plugin requires Claude Code (Anthropic's AI agent) to generate skills. You must configure Anthropic API credentials for the plugin to work.

## Features

- **AI-Powered Generation**: Uses runspace-agent to create Anthropic skills from descriptions
- **Automatic Import**: Generated skills are automatically imported into the store
- **Tool & Snippet Support**: Handles both tools and snippets from generated skills
- **Tagging**: Apply custom tags to generated skills for organization
- **REST API**: Provides HTTP endpoints for skill generation
- **UI Integration**: Includes UI configuration for seamless integration

## Installation

The plugin is automatically discovered by Skillberry Store when installed. To install:

```bash
cd plugins/skillberry-plugin-anthropic-skill-generator
pip install -e .
```

### Dependencies

- `runspace-agent==0.1.0` - AI agent for generating Anthropic skills
- Python >= 3.10
- **Docker (required)** - Container mode is the default for safe, isolated execution

## Configuration

### Automatic Configuration from Claude Settings

**The plugin automatically loads credentials from `~/.claude/settings.json` if it exists!**

If you already have Claude Code configured on your machine, the plugin will automatically use those settings. No additional configuration needed!

Example `~/.claude/settings.json`:
```json
{
  "apiKey": "sk-ant-...",
  "model": "claude-opus-4-8",
  "baseUrl": "https://api.anthropic.com",
  "authToken": "optional-for-proxy"
}
```

### Manual Configuration

If you don't have `~/.claude/settings.json`, you can configure the plugin manually:

#### Quick Start with .env.example

The plugin includes a `.env.example` file with all configuration options documented:

```bash
cd plugins/skillberry-plugin-anthropic-skill-generator
cp .env.example .env
# Edit .env with your API credentials
source .env
```

#### Required Environment Variables

The plugin requires Anthropic API credentials to use Claude Code for skill generation. You must set **one** of the following authentication methods:

#### Option 1: Direct Anthropic API (Recommended)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

#### Option 2: Proxy/Gateway Authentication

If you're using an API proxy or gateway:

```bash
export ANTHROPIC_BASE_URL="https://your-gateway.example.com"
export ANTHROPIC_AUTH_TOKEN="your-auth-token"
export ANTHROPIC_MODEL="claude-opus-4-8"  # Optional, defaults to Claude's latest
```

### Configuration Priority

The plugin uses the following priority order (highest to lowest):

1. **Request-specific parameters** - Credentials passed in API requests
2. **Environment variables** - `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, etc.
3. **Claude settings file** - `~/.claude/settings.json` (automatic)

This means you can override the settings file with environment variables, and override both with request-specific parameters.

### Optional Environment Variables

```bash
# Execution mode (default: "container")
# - "container": Runs in Docker container (safer, full isolation) - RECOMMENDED
# - "local": Runs on host machine (faster, less isolation) - use only for development
export RUNSPACE_MODE="container"

# Maximum conversation turns for Claude Code (default: 300)
export RUNSPACE_MAX_TURNS="300"

# Custom skills to include (comma-separated)
export RUNSPACE_PREINSTALLED_SKILLS="skill-creator,mcp-builder"
```

### Docker Setup (Required)

Container mode is the default and provides full isolation. Install Docker:

```bash
# Verify Docker is running
docker ps

# The plugin will automatically build the runspace-agent:latest image on first use
# This happens automatically when the plugin starts
```

**Note:** If Docker is not available, you can override to local mode by setting `RUNSPACE_MODE=local`, but this is **not recommended for production** as it provides less isolation.

### Configuration Check

After setting environment variables, verify the plugin status:

```bash
# Start Skillberry Store
skillberry-store

# Check plugin status via API
curl http://localhost:8000/api/plugins/status
```

The plugin status should show "Ready (container mode) from ~/.claude/settings.json" if credentials are loaded from the settings file, or just "Ready (container mode)" if using environment variables.

## Usage

### Via REST API

Generate a skill by sending a POST request:

```bash
curl -X POST http://localhost:8000/api/plugins/anthropic-skill-generator/generate-skill \
  -H "Content-Type: application/json" \
  -d '{
    "description": "A skill for processing PDF documents and extracting text",
    "skill_name": "pdf-processor",
    "tags": ["pdf", "document-processing"]
  }'
```

**Request Parameters:**
- `description` (required): Natural language description of the skill to generate
- `skill_name` (optional): Custom name for the skill
- `tags` (optional): Array of tags to apply to the skill

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

### Via UI

The plugin integrates with the Skillberry Store UI:

1. Navigate to the Plugins section
2. Find "Anthropic Skill Generator"
3. Click "Generate Anthropic Skill"
4. Enter your skill description
5. Optionally provide a name and tags
6. Click Generate

### Environment Variables in Requests

You can also override environment variables per request:

```bash
curl -X POST http://localhost:8000/api/plugins/anthropic-skill-generator/generate-skill \
  -H "Content-Type: application/json" \
  -d '{
    "description": "A skill for processing PDF documents",
    "skill_name": "pdf-processor",
    "tags": ["pdf"],
    "agent_env": {
      "ANTHROPIC_API_KEY": "sk-ant-...",
      "ANTHROPIC_MODEL": "claude-opus-4-8"
    },
    "max_turns": 50
  }'
```

## How It Works

1. **Description Input**: User provides a natural language description of the desired skill
2. **Skill Generation**: runspace-agent creates the skill structure in a temporary directory
3. **Import Process**: The Anthropic importer parses the generated files
4. **Store Integration**: Tools and snippets are created in the Skillberry Store
5. **Skill Creation**: A skill object is created linking all imported components

## Plugin Status Messages

The plugin reports its status based on configuration:

- `"Ready (container mode)"` - Plugin is properly configured with valid credentials and Docker (default)
- `"Ready (local mode)"` - Configured for local execution (development only)
- `"Missing dependency: runspace-agent not installed"` - Install runspace-agent
- `"Missing credentials: Set ANTHROPIC_API_KEY or ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN"` - Configure API access
- `"Docker not available"` - Docker is required for container mode (default)
- `"Configuration error: <details>"` - Check logs for specific error details

## Development

### Running Tests

```bash
cd plugins/skillberry-plugin-anthropic-skill-generator
pytest tests/
```

### Plugin Structure

```
skillberry-plugin-anthropic-skill-generator/
├── src/
│   └── skillberry_plugin_anthropic_skill_generator/
│       ├── __init__.py
│       └── plugin.py
├── tests/
│   └── test_anthropic_skill_generator_plugin.py
├── pyproject.toml
└── README.md
```

## API Reference

### SkillberryPluginAnthropicSkillGenerator

Main plugin class that handles skill generation.

#### Methods

- `generate_skill(description, skill_name=None, tags=None)` - Generate and import an Anthropic skill
- `is_enabled()` - Check if plugin is properly configured
- `get_status_message()` - Get current plugin status

## Troubleshooting

### Plugin Not Appearing

Ensure the plugin is installed:
```bash
pip list | grep skillberry-plugin-anthropic-skill-generator
```

### Plugin Shows "Missing credentials"

Set the required environment variables before starting Skillberry Store:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
skillberry-store
```

### Generation Fails with "Authentication error"

Verify your API credentials:
```bash
# Test with curl
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

### Container Mode Fails (Default Mode)

Ensure Docker is running:
```bash
docker ps
# If this fails, start Docker daemon

# On Linux
sudo systemctl start docker

# On macOS/Windows
# Start Docker Desktop application
```

If Docker is not available and you need to run immediately, you can temporarily use local mode:
```bash
export RUNSPACE_MODE=local
skillberry-store
```

**Warning:** Local mode is not recommended for production as it provides less isolation.

### Generation Takes Too Long

Reduce max_turns or switch to a faster model:
```bash
export RUNSPACE_MAX_TURNS="50"
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"
```

### Import Errors

Check the logs for detailed error messages:
```bash
tail -f /path/to/skillberry-store/logs/app.log
```

### Skill Quality Issues

The generated skill quality depends on:
- **Description clarity**: Be specific about what the skill should do
- **Model selection**: Opus models generally produce better results
- **Max turns**: Higher values allow more refinement (but take longer)

Example of a good description:
```
"Create a skill that extracts text from PDF files, supports both text-based and
scanned PDFs using OCR, handles multi-page documents, and returns structured JSON
with page numbers and extracted content."
```

## License

Apache License 2.0

## Contributing

Contributions are welcome! Please ensure:
- Code follows the existing plugin structure
- Tests are included for new features
- Documentation is updated accordingly

## Support

For issues and questions:
- GitHub Issues: [skillberry-ai/skillberry-store](https://github.com/skillberry-ai/skillberry-store)
- Documentation: [Skillberry Store Docs](https://github.com/skillberry-ai/skillberry-store/tree/main/docs)