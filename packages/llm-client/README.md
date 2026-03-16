# LLM Client Library

A flexible, extensible framework for working with any large-language-model (LLM) provider in a uniform way.

## Features

- **Unified interface** for multiple LLM providers (OpenAI, Azure OpenAI, IBM WatsonX, LiteLLM, RITS, IBM LiteLLM)
- **Tool calling support** across all providers with standardized response format
- **Structured output validation** with JSON Schema and Pydantic models
- **Optional dependencies** for each provider to keep installations lean
- **Robust error handling** and retry logic
- **Sync and async support** throughout
- **Observability hooks** for monitoring and debugging

---

## Installation

First, clone the repository:

```bash
git clone git@github.ibm.com:Blueberry/llm-client.git
cd llm-client
```

Then install with pip:

```bash
pip install -e .
```

### Installation with Providers

Install with specific provider support:

#### LiteLLM (Recommended Default)

```bash
pip install -e ".[litellm]"
```

#### OpenAI / Azure OpenAI

```bash
pip install -e ".[openai]"
```

#### IBM WatsonX AI

```bash
pip install -e ".[watsonx]"
```

#### RITS

```bash
pip install -e ".[rits]"
```

#### Ollama

```bash
pip install -e ".[ollama]"
```

#### All Providers

```bash
pip install -e ".[all]"
```

#### Development

```bash
pip install -e ".[dev]"
```

For detailed installation instructions, see [INSTALL.md](INSTALL.md).

---

## Quick Start

There are two options for getting LLM providers:
1. Instantiating specific LLM providers via `get_llm`
2. Through environment variables and the `auto_from_env` provider.

### 1. Using `get_llm` to instantiate an LLM provider
```python
from llm_client.llm import get_llm

# Get an LLM provider
OpenAIClient = get_llm("openai.sync")

client = OpenAIClient(
    api_key="*** openai api key ***"
)

# Generate text
response = client.generate("Explain quantum computing", model="o4-mini")
print(response)
```

### 2. Using environment variables and the `auto_from_env` provider
Set the following environment variables:
- `LLM_PROVIDER=openai.sync` 
- `MODEL_NAME=o4-mini`
- `OPENAI_API_KEY=*** openai api key ***`

```python
from llm_client.llm import get_llm

# Get an LLM provider
client = get_llm("auto_from_env")

# Generate text
response = client.generate("Explain quantum computing")
print(response)
```

You can list all available registered llm clients with:

```python
from llm_client.llm import list_available_llms

print(f"Available LiteLLM providers: {list_available_llms()}")
```

Example output:

```python
"Available LiteLLM providers: ['auto_from_env', 'litellm', 'litellm.output_val', 'litellm.rits', 'litellm.rits.output_val', 'litellm.watsonx', 'litellm.watsonx.output_val', 'litellm.ibm', 'litellm.ibm.output_val', 'litellm.ollama', 'litellm.ollama.output_val', 'openai.sync', 'openai.async', 'openai.sync.output_val', 'openai.async.output_val', 'azure_openai.sync', 'azure_openai.async', 'azure_openai.sync.output_val', 'azure_openai.async.output_val', 'watsonx', 'watsonx.output_val']"
```
---

## Examples

Comprehensive examples for each client are available in the `llm_examples/` directory:

- **`azure_openai.py`** - Azure OpenAI client examples with Azure-specific configurations
- **`litellm_rits.py`** - LiteLLM RITS client examples with hosted models
- **`litellm_ollama.py`** - LiteLLM Ollama client examples with local models
- **`litellm_watsonx.py`** - LiteLLM WatsonX client examples with Granite models
- **`litellm_ibm.py`** - LiteLLM IBM client examples with IBM's third-party LiteLLM service
- **`ibm_watsonx_ai.py`** - IBM WatsonX AI client examples with native IBM SDK

Each example file demonstrates:
- Basic text generation (with and without output validation)
- Tool calling functionality
- Async and sync usage patterns
- Error handling and observability hooks
- Structured output with Pydantic models and JSON schemas

To run an example:
```bash
python toolkit-core/llm_examples/azure_openai_example.py
```

---

## Provider-Agnostic Generation Parameters

All providers support a unified `GenerationArgs` interface for consistent parameter handling across different LLM APIs. This allows you to write provider-agnostic code that works seamlessly with any supported provider.

### GenerationArgs

```python
from llm_client.llm.types import GenerationArgs

# Create generation parameters
gen_args = GenerationArgs(
    min_tokens=10,           # Minimum tokens to generate (supported only by ibm-watsonx-ai)
    max_tokens=100,           # Maximum tokens to generate
    temperature=0.7,          # Sampling temperature (0.0-2.0)
    top_p=0.9,               # Nucleus sampling threshold
    top_k=50,                # Top-k sampling (where supported)
    frequency_penalty=0.1,    # Frequency penalty (-2.0 to 2.0)
    presence_penalty=0.1,     # Presence penalty (-2.0 to 2.0)
    repetition_penalty=1.1,   # Repetition penalty (where supported)
    stop_sequences=["END"],   # Stop sequences
    seed=42,                  # Random seed for reproducibility
    decoding_method="sample", # "greedy" or "sample" token selection
    stream=False,             # Enable streaming
    echo=False,               # Echo input in output (text mode)
    logprobs=True,            # Return log probabilities
    top_logprobs=5,           # Number of top logprobs to return
    timeout=30.0              # Request timeout in seconds
)

# Use with any provider
response = client.generate(
    "Explain quantum computing", 
    generation_args=gen_args
)
```

### Parameter Mapping by Provider

Each provider automatically maps `GenerationArgs` to their native parameter formats:

#### **OpenAI/Azure OpenAI**
- **Direct mapping**: Most parameters map 1:1 (e.g., `temperature` → `temperature`)
- **Stop sequences**: `stop_sequences` → `stop`
- **Decoding method**: `decoding_method="greedy"` → `temperature=0.0`
- **Text vs Chat**: Different parameter support (e.g., `echo` only in text mode, `tools` only in chat mode)

#### **IBM WatsonX AI**
- **Parameter wrapping**: All parameters wrapped in `params` dict for IBM ModelInference API
- **Text mode mappings**: `max_tokens` → `max_new_tokens`, `seed` → `random_seed`
- **Chat mode mappings**: `max_tokens` → `max_tokens`, `seed` → `seed`
- **Stop sequences**: `stop_sequences` → `stop_sequences` (text), `stop_sequences` → `stop` (chat)
- **Decoding method**: Native support for `decoding_method` parameter

#### **LiteLLM**
- **Chat-only**: Only supports chat modes (no text completion)
- **Parameter passthrough**: Most parameters passed directly to underlying model
- **Top-k handling**: `top_k` → `{"top_k": value}` for models that support it
- **Repetition penalty**: `repetition_penalty` → `{"repetition_penalty": value}`
- **Decoding method**: `decoding_method="greedy"` → `temperature=0.0`

### Usage Examples

```python
from llm_client.llm import get_llm
from llm_client.llm.types import GenerationArgs

# Same parameters work across all providers
gen_args = GenerationArgs(
    max_tokens=150,
    temperature=0.7,
    top_p=0.9,
    seed=42,
    decoding_method="sample"
)

# IBM WatsonX
watsonx_client = get_llm("watsonx")(
    model_name="meta-llama/llama-3-3-70b-instruct",
    api_key="...",
    project_id="..."
)
watsonx_response = watsonx_client.generate(
    "What is AI?", 
    generation_args=gen_args
)

# LiteLLM
litellm_client = get_llm("litellm")(
    model_name="meta-llama/llama-3-3-70b-instruct"
)
litellm_response = litellm_client.generate(
    "What is AI?", 
    generation_args=gen_args
)
```

---

## Structured output validation 

```python
# Use structured output
WatsonXLiteLLMClientOutputVal = get_llm("openai.sync.output_val")
structured_client = WatsonXLiteLLMClientOutputVal(
    model_name="meta-llama/llama-3-3-70b-instruct",
    include_schema_in_system_prompt=True, # Whether to add the Json Schema to the system prompt, or not
)

from pydantic import BaseModel
class Person(BaseModel):
    name: str
    age: int

person = structured_client.generate(
    "Extract: John Doe, 30 years old",
    schema=Person,
    max_retries=2
)
print(f"Name: {person.name}, Age: {person.age}")
```

---

## Core Components

### `base.py`

- **`LLMClient`**  
  The abstract foundation for any provider.  
  - Manages a registry of implementations (`register_llm`, `get_llm`).  
  - Handles initialization of the underlying SDK client.  
  - Exposes four main methods:  
    - `generate` (sync single)  
    - `generate_async` (async single)  
  - Emits observability hooks around every call (`before_generate`, `after_generate`, `error`).  
  - Requires subclasses to register their own `MethodConfig` entries (mapping "chat", "text", etc., to real SDK methods) and to implement a `_parse_llm_response(raw)` method to extract plain-text from the provider's raw response.

### `output_parser.py`

- **`ValidatingLLMClient`**  
  An extension of `LLMClient` that adds:  
  1. **Output enforcement** against a schema (JSON Schema dict, Pydantic model, or basic Python type).  
  2. Automatic **prompt injection** of system-level instructions ("Only output JSON matching this schema").  
  3. **Cleaning** of raw responses (stripping Markdown, extracting fenced JSON).  
  4. **Retries** for malformed outputs—only the bad items are retried.  
  5. Methods mirror `LLMClient` but return fully-parsed Python objects (or Pydantic instances) instead of raw text.

---

## Available Providers

All provider adapters live under `providers/`. They subclass either `LLMClient` (plain) or `ValidatingLLMClient` (with output validation), and register themselves with a name you can pass to `get_llm(...)`.

### OpenAI Adapter  
**Path:** `providers/openai/openai.py`  
**Registered names:**  
- `openai.sync` -> synchronous client
- `openai.async` -> asynchronous client
- `openai.sync.output_val` -> synchronous client with output validation
- `openai.async.output_val` -> asynchronous client with output validation

**Features:**  
- Wraps `openai.OpenAI` SDK.  
- Supports text & chat, sync & async.  
- Tool calling support with structured responses.
- Streaming support.
- **Parameter mapping**: Direct 1:1 mapping for most parameters, with `decoding_method` mapped to temperature control

**Environment:**  
Set `OPENAI_API_KEY` in your environment, or pass it to the constructor.

**Example:**
```python
from llm_client.llm import get_llm
from llm_client.llm.types import GenerationArgs

# Basic usage
client = get_llm("openai.sync")(api_key="your-key")
response = client.generate("Hello, world!", model="gpt-4o")

# With GenerationArgs
gen_args = GenerationArgs(
    max_tokens=100,
    temperature=0.7,
    decoding_method="sample"
)
response = client.generate("Hello, world!", generation_args=gen_args, model="gpt-4o")

# With output validation
client = get_llm("openai.sync.output_val")(api_key="your-key")
from pydantic import BaseModel
class Person(BaseModel):
    name: str
    age: int

person = client.generate(
  "Create a person",
  model="gpt-4o",
  schema=Person,
  include_schema_in_system_prompt=True, # Whether to add the Json Schema to the system prompt, or not
)
```

### Azure OpenAI Adapter  
**Path:** `providers/openai/openai.py`  
**Registered names:**  
- `azure_openai.sync` -> synchronous client
- `azure_openai.async` -> asynchronous client
- `azure_openai.sync.output_val` -> synchronous client with output validation
- `azure_openai.async.output_val` -> asynchronous client with output validation

**Features:**  
- Wraps `openai.AzureOpenAI` SDK.  
- Supports Azure-specific configurations (endpoint, API version, deployment).  
- Tool calling support with structured responses.
- Streaming support.
- **Parameter mapping**: Same as OpenAI with direct 1:1 mapping and `decoding_method` support

**Example:**
```python
from llm_client.llm import get_llm
from llm_client.llm.types import GenerationArgs

client = get_llm("azure_openai.sync")(
    api_key="your-key",
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_version="2024-08-01-preview"
)

# With GenerationArgs
gen_args = GenerationArgs(
    max_tokens=100,
    temperature=0.5,
    decoding_method="sample"
)
response = client.generate("Hello, world!", generation_args=gen_args, model="gpt-4o-2024-08-06")
```

### LiteLLM Adapter  
**Path:** `providers/litellm/litellm.py`  
**Registered names:**  
- `litellm` -> plain text adapter  
- `litellm.output_val` -> validating adapter

**Features:**  
- Wraps any model served by the `litellm` SDK.  
- Supports chat, text APIs, both sync & async.  
- The **plain** adapter returns raw strings; the **output-val** adapter enforces JSON schemas, Pydantic models, or basic types with retries.  
- Streaming support.

**Parameter Mapping:**  
LiteLLM uses custom parameter transforms for some GenerationArgs parameters:
- `top_k` is mapped to LiteLLM using a custom transform function
- `repetition_penalty` is mapped directly
- `decoding_method` is transformed to `temperature` (sample=0.7, greedy=0.0)
- All other standard parameters (max_tokens, temperature, etc.) are mapped directly

### RITS-Hosted LiteLLM Adapter  
**Path:** `providers/litellm/rits.py`
**Registered names:**  
- `litellm.rits` -> plain text adapter  
- `litellm.rits.output_val` -> validating adapter

**Features:**  
- Subclasses the **validating** LiteLLM adapter.  
- Automatically sets:  
  - `model_name="hosted_vllm/{model_name}"`  
  - `api_base="{RITS_API_URL}/{model_url}/v1"`  
  - `headers` with your `RITS_API_KEY`  
  - `guided_decoding_backend=XGRAMMAR`  

**Parameter Mapping:**  
RITS inherits the same parameter mapping as the base LiteLLM adapter, with additional RITS-specific configuration.

**Usage with GenerationArgs:**
```python
from llm_client.llm import GenerationArgs, get_llm

generation_args = GenerationArgs(
    max_tokens=150,
    temperature=0.6,
    top_k=50,
    decoding_method="sample"
)

client = get_llm("litellm.rits.output_val")
response = client.generate("What is machine learning?", generation_args=generation_args, model_name="ibm-granite/granite-3.1-8b-instruct", model_url="granite-3-1-8b-instruct")
```  

**Environment variables:**  
- `RITS_API_KEY` (your API key)
- `RITS_API_URL` (RITS API url)

**Example:**  
```python
from llm_client.llm import get_llm

client = get_llm("litellm.rits.output_val")(
    model_name="ibm-granite/granite-3.1-8b-instruct"
    model_url="granite-3-1-8b-instruct" # The short model name that is added to the url (if not given - uses rits api to get this name)
    include_schema_in_system_prompt=True, # Whether to add the Json Schema to the system prompt, or not (recommended in RITS - as the response_format in LiteLLM parameter is not working well with RITS)
)
result: int = client.generate("Compute 2+2", schema=int, max_retries=1)
```

### Watsonx-Hosted LiteLLM Adapter  
**Path:** `providers/litellm/watsonx.py`  
**Registered names:**  
- `litellm.watsonx` -> plain text adapter  
- `litellm.watsonx.output_val` -> validating adapter

**Features:**  
- Like RITS, but for IBM Watsonx.  
- Automatically prefixes `model_name="watsonx/{model_name}"`.  
- Inherits all the validation and retry logic from the validating LiteLLM base class.

**Parameter Mapping:**  
Watsonx inherits the same parameter mapping as the base LiteLLM adapter.

**Usage with GenerationArgs:**
```python
from llm_client.llm import GenerationArgs, get_llm

generation_args = GenerationArgs(
    max_tokens=200,
    temperature=0.5,
    top_k=30,
    decoding_method="sample"
)

client = get_llm("litellm.watsonx")
response = client.generate("Explain artificial intelligence", generation_args=generation_args, model_name="granite-3.1-8b-instruct")
```

**Environment variables:**  
- `WX_API_KEY`  
- `WX_PROJECT_ID` or `WX_SPACE_ID`
- `WX_URL`

**Example:**  
```python
from llm_client.llm import get_llm

client = get_llm("litellm.watsonx.output_val")(
    model_name="meta-llama/llama-3-3-70b-instruct"
)

class Weather(BaseModel):
    city: str
    temperature_c: float
    condition: str

weather = client.generate(
    "Return weather for Rome with 25C and sunny condition.",
    schema=Weather,
    max_retries=2,
    include_schema_in_system_prompt=True, # Whether to add the Json Schema to the system prompt, or not
)
```

### IBM LiteLLM Adapter  
**Path:** `providers/litellm/ibm_litellm.py`  
**Registered names:**  
- `litellm.ibm` -> plain text adapter  
- `litellm.ibm.output_val` -> validating adapter

**Features:**  
- Specialized LiteLLM adapter for IBM's third-party LiteLLM service.  
- Automatically sets:  
  - `api_base="https://ete-litellm.bx.cloud9.ibm.com"` (default, can be overridden)
  - `custom_llm_provider="openai"`  
  - Authentication with `IBM_THIRD_PARTY_API_KEY`
- Supports multiple model providers through IBM's LiteLLM gateway (GCP/claude, Azure/gpt-4o, etc.)
- Inherits all validation and retry logic from the validating LiteLLM base class

**Parameter Mapping:**  
IBM LiteLLM inherits the same parameter mapping as the base LiteLLM adapter.

**Usage with GenerationArgs:**
```python
from llm_client.llm import GenerationArgs, get_llm

generation_args = GenerationArgs(
    max_tokens=200,
    temperature=0.3,
    top_p=0.9
)

client = get_llm("litellm.ibm")
response = client.generate(
    "Explain distributed systems", 
    generation_args=generation_args, 
    model_name="GCP/claude-3-7-sonnet"
)
```

**Environment variables:**  
- `IBM_THIRD_PARTY_API_KEY` (required - your IBM API key)
- `IBM_LITELLM_API_BASE` (optional - defaults to https://ete-litellm.bx.cloud9.ibm.com)

**Example:**  
```python
from llm_client.llm import get_llm
from pydantic import BaseModel

# Basic usage
client = get_llm("litellm.ibm")(
    model_name="GCP/claude-3-7-sonnet"
)
response = client.generate("Write a short joke")

# With structured output validation
structured_client = get_llm("litellm.ibm.output_val")(
    model_name="GCP/claude-3-7-sonnet",
    include_schema_in_system_prompt=True
)

class Person(BaseModel):
    name: str
    age: int
    occupation: str

person = structured_client.generate(
    "Extract info: Alice is 30 years old and works as a software engineer.",
    schema=Person,
    max_retries=2
)
```

### IBM WatsonX AI Adapter  
**Path:** `providers/ibm_watsonx_ai/ibm_watsonx_ai.py`  
**Registered names:**  
- `watsonx` -> plain text adapter  
- `watsonx.output_val` -> validating adapter

**Features:**  
- Wraps the native IBM WatsonX AI SDK. 
- Advanced generation parameters (temperature, etc.).

**Parameter Mapping:**  
IBM WatsonX AI uses its own parameter mapping for GenerationArgs:
- Most parameters (max_tokens, temperature, top_p, etc.) are mapped directly
- `decoding_method` is mapped to WatsonX's native decoding method parameter
- Provider uses the official IBM WatsonX parameter names for optimal compatibility

**Usage with GenerationArgs:**
```python
from llm_client.llm import GenerationArgs, get_llm

generation_args = GenerationArgs(
    max_tokens=150,
    temperature=0.7,
    top_p=0.9,
    decoding_method="sample"
)

client = get_llm("watsonx")
response = client.generate("What is AI?", generation_args=generation_args, model_name="meta-llama/llama-3-3-70b-instruct")
```

**Example:**
```python
from llm_client.llm import get_llm

client = get_llm("watsonx")(
    model_name="meta-llama/llama-3-3-70b-instruct",
)
response = client.generate("Explain quantum computing")
```

---

## Adding Your Own Provider

1. **Subclass** either `LLMClient` (for plain text) or `ValidatingLLMClient` (if you need schema enforcement).  
2. **Implement**  
   - `@classmethod provider_class() -> your SDK client class`  
   - `_register_methods()` to map `"chat"`, `"chat_async"`, (if available `"text"`, `"text_async"`).
   - `_parse_llm_response(raw)` to pull a single string out of the provider's raw response.

3. **Register** your class:  
   ```python
   @register_llm("myprovider")
   class MyClient(LLMClient):
       ...
   ```

4. **Use** it via the registry:  
   ```python
   from llm_client.llm import get_llm

   Client = get_llm("myprovider")
   client = Client(api_key="…", other_args=…)
   text = client.generate("Hello world")
   ```

---

## Tips & Best Practices

- **Hooks** let you tap into every call for logging, tracing, or metrics:  
  ```python
  client = MyClient(..., hooks=[lambda ev, data: print(ev, data)])
  ```
- **Retries** in validating mode help you guard against model hallucinations in structured outputs—set `max_retries=1` or `2` for quick corrections.
- **Keep schemas small**: only require the fields you care about to avoid brittle failures when the model adds extra metadata.
- **Tool calling** works consistently across all providers with the same interface.
- **Environment variables** can be used for API keys and configuration to keep secrets out of code.

---

## Logging and Debugging

The LLM Client library includes a comprehensive logging system that provides detailed visibility into API calls, payloads, responses, and errors. This is essential for debugging, monitoring, and understanding the behavior of your LLM interactions.

### Features

- **Multi-level logging**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Visual formatting**: Rich library integration for beautiful console output
- **Detailed API tracking**: Log request payloads, raw responses, parsed outputs, and timing
- **Sensitive data filtering**: Automatic redaction of API keys, tokens, and credentials
- **File output**: Optional logging to files with automatic rotation
- **Easy configuration**: Environment variables or programmatic setup
- **Non-invasive**: Opt-in logging that doesn't affect existing code

### Quick Start

#### Basic Setup

```python
from llm_client import configure_logging

# Configure logging with default settings (INFO level, console only)
configure_logging()

# Now all LLM operations will be logged
from llm_client.llm import get_llm
client = get_llm("openai.sync")(api_key="your-key")
response = client.generate("Hello, world!", model="gpt-4o")
```

#### Environment Variables

The easiest way to enable logging is through environment variables:

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export LLM_CLIENT_LOG_LEVEL=DEBUG

# Optional: Enable file logging
export LLM_CLIENT_LOG_DIR=/path/to/logs
```

```python
from llm_client import configure_logging

# Automatically uses environment variables
configure_logging()
```

#### Programmatic Configuration

For more control, configure logging programmatically:

```python
from llm_client import configure_logging, LogConfig

# Create custom configuration
config = LogConfig(
    level="DEBUG",              # Log level
    log_dir="/path/to/logs",    # Optional: directory for log files
    max_payload_length=2000,    # Truncate large payloads
    enable_rich=True,           # Use Rich for beautiful formatting
    log_file_prefix="llm_client" # Prefix for log files
)

configure_logging(config)
```

### Log Levels

Choose the appropriate log level for your needs:

- **`DEBUG`**: Most verbose - logs all API calls, payloads, raw responses, parsing steps, and internal operations
- **`INFO`**: Standard logging - logs API calls, responses, and important events
- **`WARNING`**: Only warnings and errors - logs potential issues and failures
- **`ERROR`**: Only errors - logs failures and exceptions
- **`CRITICAL`**: Only critical failures - logs severe errors that may cause system failure

### What Gets Logged

#### Generation Calls (INFO level)

```
🚀 Starting generation
   Mode: chat
   Prompt: "Explain quantum computing"
   Model: gpt-4o
   Parameters: {'temperature': 0.7, 'max_tokens': 100}
```

#### API Payloads (DEBUG level)

```
📤 API Request Payload
   {
     "model": "gpt-4o",
     "messages": [{"role": "user", "content": "Explain quantum computing"}],
     "temperature": 0.7,
     "max_tokens": 100
   }
```

#### Raw LLM Responses (DEBUG level)

```
📥 Raw LLM Response (duration: 1.23s)
   {
     "id": "chatcmpl-...",
     "object": "chat.completion",
     "created": 1234567890,
     "model": "gpt-4o",
     "choices": [{
       "message": {
         "role": "assistant",
         "content": "Quantum computing is..."
       },
       "finish_reason": "stop"
     }],
     "usage": {
       "prompt_tokens": 10,
       "completion_tokens": 50,
       "total_tokens": 60
     }
   }
```

#### Parsed Responses (DEBUG level)

```
📝 Parsed Response
   "Quantum computing is a revolutionary approach..."
```

#### Completion (INFO level)

```
✅ Generation completed
   Duration: 1.23s
   Tokens: 60 (10 prompt + 50 completion)
```

#### Errors (ERROR level)

```
❌ Generation failed
   Error: OpenAI API error: Rate limit exceeded
   Duration: 0.45s
   Traceback: ...
```

### Sensitive Data Protection

The logging system automatically filters sensitive information:

- API keys (`api_key`, `OPENAI_API_KEY`, etc.)
- Authentication tokens (`token`, `auth_token`, `bearer_token`)
- Passwords and secrets (`password`, `secret`, `credential`)
- Authorization headers

Filtered values are replaced with `***REDACTED***` in logs.

### File Logging

Enable file logging to persist logs for later analysis:

```python
from llm_client import configure_logging, LogConfig

config = LogConfig(
    level="DEBUG",
    log_dir="/var/log/llm_client",  # Directory for log files
    log_file_prefix="my_app"        # Prefix for log files
)

configure_logging(config)
```

Log files are automatically:
- Named with timestamps: `my_app_20260316_203045.log`
- Rotated when they reach 10MB
- Limited to 5 backup files
- Created with proper permissions

### Advanced Usage

#### Custom Logger Instance

Get a logger instance for your own modules:

```python
from llm_client import get_logger

logger = get_logger("my_module")
logger.info("Custom log message")
logger.debug("Detailed debug info")
```

#### Conditional Logging

```python
from llm_client import configure_logging, LogConfig
import os

# Only enable debug logging in development
config = LogConfig(
    level="DEBUG" if os.getenv("ENV") == "dev" else "INFO"
)

configure_logging(config)
```

#### Integration with Existing Logging

The LLM Client logging system integrates with Python's standard logging:

```python
import logging
from llm_client import configure_logging

# Configure your app's logging
logging.basicConfig(level=logging.INFO)

# Configure LLM Client logging (uses same root logger)
configure_logging()
```

### Example Output

With Rich formatting enabled (default), you'll see beautifully formatted logs:

```
[2026-03-16 20:30:45] INFO     🚀 Starting generation
                               Mode: chat
                               Prompt: "Explain quantum computing"
                               Model: gpt-4o

[2026-03-16 20:30:45] DEBUG    📤 API Request Payload
                               {
                                 "model": "gpt-4o",
                                 "messages": [...]
                               }

[2026-03-16 20:30:46] DEBUG    📥 Raw LLM Response (duration: 1.23s)
                               {
                                 "choices": [{
                                   "message": {
                                     "content": "Quantum computing..."
                                   }
                                 }]
                               }

[2026-03-16 20:30:46] INFO     ✅ Generation completed
                               Duration: 1.23s
                               Tokens: 60
```

### Best Practices

1. **Use DEBUG in development**: Get full visibility into API interactions
2. **Use INFO in production**: Balance between visibility and performance
3. **Enable file logging for production**: Persist logs for troubleshooting
4. **Review logs regularly**: Identify patterns, errors, and optimization opportunities
5. **Protect sensitive data**: The system filters common patterns, but review your logs
6. **Monitor log file sizes**: Configure rotation to prevent disk space issues

### Troubleshooting

#### Logs not appearing?

```python
# Ensure logging is configured
from llm_client import configure_logging
configure_logging()

# Check log level
import logging
print(logging.getLogger("llm_client").level)
```

#### Want more detail?

```python
# Switch to DEBUG level
from llm_client import configure_logging, LogConfig
configure_logging(LogConfig(level="DEBUG"))
```

#### Rich formatting not working?

```python
# Install Rich library
# pip install "llm-client[dev]"

# Or disable Rich formatting
from llm_client import configure_logging, LogConfig
configure_logging(LogConfig(enable_rich=False))
```

---

## Supported Features by Provider

| Feature | OpenAI | Azure OpenAI | LiteLLM | LiteLLM RITS | LiteLLM WatsonX | IBM WatsonX AI |
|---------|---------|--------------|---------|--------------|-----------------|----------------|
| Basic Generation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Async Generation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tool Calling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Structured Output | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Observability Hooks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Retry Logic | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
