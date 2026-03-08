import os
from typing import Any, List, Optional
from .litellm import (
    LiteLLMClient,
    LiteLLMClientOutputVal,
)
from ...base import Hook, register_llm
from ..consts import IBM_THIRD_PARTY_API_KEY, IBM_LITELLM_API_BASE


@register_llm("litellm.ibm")
class IBMLiteLLMClient(LiteLLMClient):
    """
    Specialized LiteLLMClient for IBM LiteLLM service.
    Automatically injects:
      - api_base URL (defaults to https://ete-litellm.bx.cloud9.ibm.com)
      - authentication with IBM_THIRD_PARTY_API_KEY
      - custom_llm_provider="openai"
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        *,
        hooks: Optional[List[Hook]] = None,
        **lite_kwargs: Any,
    ) -> None:
        """
        Initialize the IBM LiteLLM client.
        Args:
            model_name: Name of the model (e.g. "GCP/claude-3-7-sonnet", "Azure/gpt-4o").
            api_key: IBM Third Party API key (falls back to env var IBM_THIRD_PARTY_API_KEY).
            api_base: Base IBM LiteLLM API URL (defaults to https://ete-litellm.bx.cloud9.ibm.com).
            hooks: Optional observability hooks to receive events.
            lite_kwargs: Additional parameters passed to the underlying LiteLLM constructor.
        Raises:
            EnvironmentError: If API key is missing.
        """
        # Obtain API key from environment if not provided
        if not api_key:
            api_key = os.getenv(IBM_THIRD_PARTY_API_KEY)
            if not api_key:
                raise EnvironmentError(
                    f"Missing API key; please set the '{IBM_THIRD_PARTY_API_KEY}' environment variable."
                )

        # Set default API base if not provided
        if not api_base:
            api_base = os.getenv(
                IBM_LITELLM_API_BASE, "https://ete-litellm.bx.cloud9.ibm.com"
            )

        # Call parent constructor with all required lite parameters
        super().__init__(
            model_name=model_name,
            hooks=hooks,
            api_base=api_base,
            api_key=api_key,
            custom_llm_provider="openai",
            **lite_kwargs,
        )


@register_llm("litellm.ibm.output_val")
class IBMLiteLLMClientOutputVal(LiteLLMClientOutputVal):
    """
    Specialized LiteLLMClientOutputVal for IBM LiteLLM service.
    Automatically injects:
      - api_base URL (defaults to https://ete-litellm.bx.cloud9.ibm.com)
      - authentication with IBM_THIRD_PARTY_API_KEY
      - custom_llm_provider="openai"
    Inherits full JSON / Pydantic / type-based output validation,
    retry logic, batch & async support from LiteLLMClientOutputVal.
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        *,
        hooks: Optional[List[Hook]] = None,
        **lite_kwargs: Any,
    ) -> None:
        """
        Initialize the IBM LiteLLM client with output validation.
        Args:
            model_name: Name of the model (e.g. "GCP/claude-3-7-sonnet", "Azure/gpt-4o").
            api_key: IBM Third Party API key (falls back to env var IBM_THIRD_PARTY_API_KEY).
            api_base: Base IBM LiteLLM API URL (defaults to https://ete-litellm.bx.cloud9.ibm.com).
            hooks: Optional observability hooks to receive events.
            lite_kwargs: Additional parameters passed to the underlying LiteLLM constructor.
        Raises:
            EnvironmentError: If API key is missing.
        """
        # Obtain API key from environment if not provided
        if not api_key:
            api_key = os.getenv(IBM_THIRD_PARTY_API_KEY)
            if not api_key:
                raise EnvironmentError(
                    f"Missing API key; please set the '{IBM_THIRD_PARTY_API_KEY}' environment variable."
                )

        # Set default API base if not provided
        if not api_base:
            api_base = os.getenv(
                IBM_LITELLM_API_BASE, "https://ete-litellm.bx.cloud9.ibm.com"
            )

        # Call parent constructor with all required lite parameters
        super().__init__(
            model_name=model_name,
            hooks=hooks,
            api_base=api_base,
            api_key=api_key,
            custom_llm_provider="openai",
            **lite_kwargs,
        )
