# Skillberry Plugin Creator

Minimal plugin for creating code snippets using LLM via llm-switchboard.

## Installation

```bash
cd plugins/skillberry-plugin-creator
pip install -e .
```

## Configuration

The plugin uses llm-switchboard which reads configuration from environment variables.

### Required Environment Variables

```bash
export LLM_PROVIDER=<provider_name>
export LLM_MODEL=<model_name>
```

Additional environment variables depend on the provider you choose. See [llm-switchboard documentation](https://github.com/your-org/llm-switchboard) for provider-specific configuration.

### Example: OpenAI

```bash
export LLM_PROVIDER=openai.async
export LLM_MODEL=gpt-4
export OPENAI_API_KEY=your_api_key
```

### Example: LiteLLM

```bash
export LLM_PROVIDER=litellm
export LLM_MODEL=your-model-name
export OPENAI_API_KEY=your_api_key
export OPENAI_API_BASE=https://your-endpoint.com
```

## Usage

Start the Skillberry Store and the plugin will be automatically loaded.

### Create Snippet

```bash
curl -X POST http://localhost:8000/api/plugins/skillberry-plugin-creator/create-snippet \
  -H "Content-Type: application/json" \
  -d '{
    "description": "A Python function to calculate fibonacci numbers",
    "name": "fibonacci"
  }'
```

## How It Works

1. Takes a natural language description
2. Uses LLM to generate code snippet
3. Uses LLM to infer metadata (language, tags, description)
4. Saves snippet to Skillberry Store
5. Returns created snippet details

## Dependencies

- `llm-switchboard[litellm]>=0.1.0` - Unified LLM client interface

All LLM configuration is handled by llm-switchboard via environment variables.