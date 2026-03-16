"""
LLM Client Library

A flexible, extensible framework for working with any large-language-model (LLM)
provider in a uniform way.
"""

__version__ = "0.1.0"

# Re-export main components from llm module
from .llm import (
    LLMClient,
    ValidatingLLMClient,
    get_llm,
    register_llm,
    list_available_llms,
    Hook,
    MethodConfig,
    OutputValidationError,
    GenerationMode,
    LLMResponse,
    GenerationArgs,
)

# Re-export logging utilities
from .llm.logging_utils import (
    configure_logging,
    LogConfig,
    get_logger,
)

__all__ = [
    "__version__",
    "LLMClient",
    "ValidatingLLMClient",
    "get_llm",
    "register_llm",
    "list_available_llms",
    "Hook",
    "MethodConfig",
    "OutputValidationError",
    "GenerationMode",
    "LLMResponse",
    "GenerationArgs",
    "configure_logging",
    "LogConfig",
    "get_logger",
]
