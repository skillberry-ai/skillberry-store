# Skillberry Plugin Evaluator

Minimal plugin for evaluating content and suggesting tags using LLM via llm-switchboard.

## Installation

```bash
cd plugins/skillberry-plugin-evaluator
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

### Evaluate Content

```bash
curl -X POST http://localhost:8000/api/plugins/skillberry-plugin-evaluator/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "abc-123",
    "content_type": "snippet",
    "content": "def hello():\n    print(\"Hello, World!\")",
    "name": "Hello World"
  }'
```

**Response:**
```json
{
  "success": true,
  "uuid": "abc-123",
  "suggested_tags": ["python", "function", "beginner"],
  "confidence_scores": {
    "python": 0.95,
    "function": 0.90,
    "beginner": 0.85
  },
  "summary": "Simple Python function that prints a greeting message"
}
```

## How It Works

1. Takes content (code, skill description, etc.)
2. Uses LLM to analyze the content
3. Extracts suggested tags with confidence scores
4. Returns evaluation results

## Dependencies

- `llm-switchboard[litellm]>=0.1.0` - Unified LLM client interface

All LLM configuration is handled by llm-switchboard via environment variables.