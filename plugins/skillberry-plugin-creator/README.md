# Skillberry Creator Plugin

AI-powered content creator plugin for Skillberry Store with multi-LLM support.

## Overview

This plugin uses [llm-switchboard](https://github.com/skillberry-ai/llm-switchboard) to generate tools, skills, and snippets from natural language descriptions. It supports multiple LLM providers including OpenAI, Azure OpenAI, WatsonX, and 100+ providers via LiteLLM.

## Installation

**Prerequisites:** The core `skillberry-store` package must be installed first.

```bash
# Install core package (if not already installed)
pip install skillberry-store

# Then install the plugin
pip install skillberry-plugin-creator
```

**For Development:**
```bash
# Install core in editable mode
pip install -e /path/to/skillberry-store

# Install plugin in editable mode
cd plugins/skillberry-plugin-creator
pip install -e .

# Run tests
PYTHONPATH=/path/to/skillberry-store/src:src pytest tests/
```

## Configuration

The plugin uses llm-switchboard for LLM integration. Configure via environment variables:

### OpenAI (default)
```bash
export LLM_PROVIDER=openai.async
export LLM_API_KEY=your-openai-api-key
export LLM_MODEL=gpt-4  # optional
```

### Azure OpenAI
```bash
export LLM_PROVIDER=azure_openai.async
export LLM_API_KEY=your-azure-api-key
export LLM_BASE_URL=https://your-resource.openai.azure.com
export LLM_MODEL=gpt-4
```

### WatsonX
```bash
export LLM_PROVIDER=watsonx
export LLM_API_KEY=your-watsonx-api-key
export LLM_MODEL=ibm/granite-13b-chat-v2
```

### LiteLLM (100+ providers)
```bash
export LLM_PROVIDER=litellm
export LLM_API_KEY=your-api-key
export LLM_MODEL=claude-3-opus-20240229
```

See [llm-switchboard documentation](https://github.com/skillberry-ai/llm-switchboard) for more providers.

## Usage

### Via API

```bash
# Create a tool
curl -X POST http://localhost:8000/api/plugins/creator/create-tool \
  -H "Content-Type: application/json" \
  -d '{"description": "A function that calculates fibonacci numbers"}'

# Create a skill
curl -X POST http://localhost:8000/api/plugins/creator/create-skill \
  -H "Content-Type: application/json" \
  -d '{"description": "A skill for data analysis with pandas"}'

# Create a snippet
curl -X POST http://localhost:8000/api/plugins/creator/create-snippet \
  -H "Content-Type: application/json" \
  -d '{"description": "A code snippet for reading CSV files"}'
```

### Via CLI

```bash
# Create a tool
sbs plugin creator create-tool --description "A function that calculates fibonacci numbers"

# Create a skill
sbs plugin creator create-skill --description "A skill for data analysis"

# Create a snippet
sbs plugin creator create-snippet --description "Code for reading CSV files"
```

### Via UI

1. Navigate to the Plugins page in Skillberry Store UI
2. Find the "AI Content Creator" plugin
3. Click on "Create Tool", "Create Skill", or "Create Snippet"
4. Enter your description and submit

## Features

- **Tool Generation**: Create Python functions from descriptions
- **Skill Generation**: Create complete skill bundles with multiple tools
- **Snippet Generation**: Create reusable code snippets
- **API Integration**: RESTful API endpoints for programmatic access
- **CLI Commands**: Command-line interface for quick creation
- **UI Integration**: Seamless integration with Skillberry Store UI

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest tests/
```

## License

MIT