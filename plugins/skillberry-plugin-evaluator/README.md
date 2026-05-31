# Skillberry Evaluator Plugin

AI-powered content evaluator plugin for Skillberry Store with multi-LLM support.

## Overview

This plugin automatically evaluates skills, tools, and snippets when they are added to the store, using [llm-switchboard](https://github.com/skillberry-ai/llm-switchboard) to analyze content and suggest relevant tags. It supports multiple LLM providers including OpenAI, Azure OpenAI, WatsonX, and 100+ providers via LiteLLM.

## Installation

**Prerequisites:** The core `skillberry-store` package must be installed first.

```bash
# Install core package (if not already installed)
pip install skillberry-store

# Then install the plugin
pip install skillberry-plugin-evaluator
```

**For Development:**
```bash
# Install core in editable mode
pip install -e /path/to/skillberry-store

# Install plugin in editable mode
cd plugins/skillberry-plugin-evaluator
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
export LLM_MODEL=gpt-4  # optional, defaults to gpt-4
export TAG_CONFIDENCE_THRESHOLD=0.7  # optional, defaults to 0.7
```

## Features

- **Automatic Evaluation**: Automatically evaluates new content when added
- **Manual Evaluation**: Evaluate specific items on demand
- **Batch Evaluation**: Evaluate multiple items at once
- **Tag Suggestions**: AI-powered tag suggestions with confidence scores
- **Statistics**: Track evaluation metrics and common tags

## Usage

### Via API

```bash
# Evaluate a single item
curl -X POST http://localhost:8000/api/plugins/evaluator/evaluate \
  -H "Content-Type: application/json" \
  -d '{"uuid": "abc-123", "content_type": "tool"}'

# Batch evaluate
curl -X POST http://localhost:8000/api/plugins/evaluator/batch-evaluate \
  -H "Content-Type: application/json" \
  -d '{"content_type": "tool", "max_items": 50}'

# Get statistics
curl http://localhost:8000/api/plugins/evaluator/stats
```

### Via CLI

```bash
# Evaluate a specific item
sbs plugin evaluator evaluate --uuid abc-123 --type tool

# Batch evaluate all new tools
sbs plugin evaluator batch --type tool --max-items 100

# View statistics
sbs plugin evaluator stats
```

### Via UI

1. Navigate to the Plugins page in Skillberry Store UI
2. Find the "AI Content Evaluator" plugin
3. Click on "Evaluate Content" to evaluate a specific item
4. Or use "Batch Evaluate" to evaluate multiple items
5. View "Statistics" to see evaluation metrics

## How It Works

1. **Content Analysis**: When content is added or manually evaluated, the plugin retrieves the content details
2. **AI Evaluation**: Sends content to configured LLM with evaluation prompt
3. **Tag Extraction**: Parses AI response to extract suggested tags and confidence scores
4. **Tag Application**: Applies tags that meet the confidence threshold
5. **Metadata Storage**: Stores evaluation metadata for tracking

## Tag Categories

The evaluator suggests tags from these categories:

- **Programming Language**: python, javascript, go, rust, etc.
- **Domain**: data-science, web-dev, devops, security, testing, etc.
- **Complexity**: beginner, intermediate, advanced
- **Purpose**: utility, framework, library, template, example
- **Technology**: api, cli, database, ml, cloud, etc.

## Configuration Options

### Plugin Settings (via UI)

- **auto_evaluate**: Automatically evaluate new content (default: true)
- **confidence_threshold**: Minimum confidence to apply tags (default: 0.7)

### Environment Variables

- `LLM_PROVIDER`: LLM provider to use (default: openai)
- `LLM_API_KEY`: API key for LLM provider (required)
- `LLM_MODEL`: Model to use (default: gpt-4)
- `TAG_CONFIDENCE_THRESHOLD`: Minimum confidence for tag application (default: 0.7)

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest tests/
```

## Architecture

The plugin demonstrates the Skillberry plugin architecture:

- **Self-contained**: All functionality in plugin package
- **API Integration**: Provides REST endpoints automatically mounted
- **CLI Integration**: Commands automatically registered
- **UI Integration**: Configuration for automatic UI rendering
- **Event Hooks**: Can hook into content lifecycle events
- **Store Access**: Uses StoreAPI to query and update content

## License

MIT