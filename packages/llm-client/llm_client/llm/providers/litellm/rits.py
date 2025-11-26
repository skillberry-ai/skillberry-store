import os
from typing import Any, List, Optional
from .litellm import (
    LiteLLMClient,
    LiteLLMClientOutputVal,
)
from ...base import Hook, register_llm
from ..consts import RITS_API_KEY, RITS_API_URL, XGRAMMAR

import requests


def get_rits_model_list():
    url = "https://rits.fmaas.res.ibm.com/ritsapi/inferenceinfo"
    response = requests.get(url, headers={RITS_API_KEY: os.getenv(RITS_API_KEY, "")})
    if response.status_code == 200:
        return {m["model_name"]: m["endpoint"].split("/")[-1] for m in response.json()}
    else:
        raise Exception(f"Failed getting RITS model list:\n\n{response.text}")


@register_llm("litellm.rits")
class RITSLiteLLMClient(LiteLLMClient):
    """
    Specialized LiteLLMClient for RITS-hosted models.

    Automatically injects:
      - model_path = "hosted_vllm/{model_name}"
      - api_base URL = "{api_url}/{model_url}/v1"
      - authentication headers with RITS_API_KEY
      - guided_decoding_backend
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        model_url: Optional[str] = None,
        api_url: Optional[str] = None,
        guided_decoding_backend: Optional[str] = XGRAMMAR,
        *,
        hooks: Optional[List[Hook]] = None,
        **lite_kwargs: Any,
    ) -> None:
        """
        Initialize the RITS LiteLLM client.

        Args:
            model_name: Name of the hosted RITS model (e.g. "my-model").
            api_key: RITS API key (falls back to env var RITS_API_KEY).
            model_url: URL fragment for the model; derived from model_name if omitted.
            api_url: Base RITS API URL (defaults to None).
            guided_decoding_backend: Backend identifier for guided decoding (defaults to XGRAMMAR).
            hooks: Optional observability hooks to receive events.
            lite_kwargs: Additional parameters passed to the underlying LiteLLM constructor.

        Raises:
            ValueError: If model_url derivation fails.
            EnvironmentError: If API key is missing.
        """
        # Derive model_url from model_name if not provided
        if not model_url:
            try:
                model_url = get_rits_model_list().get(model_name)
            except Exception as e:
                raise ValueError(
                    f"Unable to derive model_url from '{model_name}': {e}"
                ) from e

        # Obtain API key from environment if still not provided
        if not api_key:
            api_key = os.getenv(RITS_API_KEY)
            if not api_key:
                raise EnvironmentError(
                    f"Missing API key; please set the '{RITS_API_KEY}' environment variable."
                )

        # Ensure api_url is set, if not provided, it tries to obtain it from the environment variable, otherwise it raises an error.
        if not api_url:
            api_url = os.getenv(RITS_API_URL)
            if not api_url:
                raise EnvironmentError(
                    f"Missing API URL; please set the '{RITS_API_URL}' environment variable."
                )

        # Construct the full API base endpoint
        api_base = f"{api_url.rstrip('/')}/{model_url}/v1"

        # Call parent constructor with all required lite parameters
        super().__init__(
            model_name=f"hosted_vllm/{model_name}",
            hooks=hooks,
            api_base=api_base,
            api_key=api_key,
            headers={RITS_API_KEY: api_key},
            guided_decoding_backend=guided_decoding_backend,
            **lite_kwargs,
        )


@register_llm("litellm.rits.output_val")
class RITSLiteLLMClientOutputVal(LiteLLMClientOutputVal):
    """
    Specialized LiteLLMClientOutputVal for RITS-hosted models.

    Automatically injects:
      - model_path = "hosted_vllm/{model_name}"
      - api_base URL = "{api_url}/{model_url}/v1"
      - authentication headers with RITS_API_KEY
      - guided_decoding_backend

    Inherits full JSON / Pydantic / type-based output validation,
    retry logic, batch & async support from LiteLLMClientOutputVal.
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        model_url: Optional[str] = None,
        api_url: Optional[str] = None,
        guided_decoding_backend: Optional[str] = XGRAMMAR,
        *,
        hooks: Optional[List[Hook]] = None,
        **lite_kwargs: Any,
    ) -> None:
        """
        Initialize the RITS LiteLLM client with output validation.

        Args:
            model_name: Name of the hosted RITS model (e.g. "my-model").
            api_key: RITS API key (falls back to env var RITS_API_KEY).
            model_url: URL fragment for the model; derived from model_name if omitted.
            api_url: Base RITS API URL (defaults to None).
            guided_decoding_backend: Backend identifier for guided decoding (defaults to XGRAMMAR).
            hooks: Optional observability hooks to receive events.
            lite_kwargs: Additional parameters passed to the underlying LiteLLM constructor.

        Raises:
            ValueError: If model_url derivation fails.
            EnvironmentError: If API key is missing.
        """
        # Derive model_url from model_name if not provided
        if not model_url:
            try:
                model_url = get_rits_model_list().get(model_name)
            except Exception as e:
                raise ValueError(
                    f"Unable to derive model_url from '{model_name}': {e}"
                ) from e

        # Obtain API key from environment if still not provided
        if not api_key:
            api_key = os.getenv(RITS_API_KEY)
            if not api_key:
                raise EnvironmentError(
                    f"Missing API key; please set the '{RITS_API_KEY}' environment variable."
                )

        # Ensure api_url is set, if not provided, it tries to obtain it from the environment variable, otherwise it raises an error.
        if not api_url:
            api_url = os.getenv(RITS_API_URL)
            if not api_url:
                raise EnvironmentError(
                    f"Missing API URL; please set the '{RITS_API_URL}' environment variable."
                )

        # Construct the full API base endpoint
        api_base = f"{api_url.rstrip('/')}/{model_url}/v1"

        # Call parent constructor with all required lite parameters
        super().__init__(
            model_name=f"hosted_vllm/{model_name}",
            hooks=hooks,
            api_base=api_base,
            api_key=api_key,
            headers={RITS_API_KEY: api_key},
            guided_decoding_backend=guided_decoding_backend,
            **lite_kwargs,
        )

    def generate(
        self,
        **kwargs: Any,
    ) -> Any:
        """
        Synchronous chat generation with validation + retries.
        This method is a wrapper around the generate method of the parent class,
        ensuring that the schema_field is set to None, as RITS has problems with litellm schema validation.
        Therefore, we disable schema validation for RITS models, and use the default validation.

        Args:
            **kwargs: Additional keyword arguments passed to the generate method.
        Returns:
            Any: The generated response from the model.
        """

        # Delegate to ValidatingLLMClient.generate
        return super().generate(
            **{
                "schema_field": None,
                **kwargs,
            }
        )

    async def generate_async(
        self,
        **kwargs: Any,
    ) -> Any:
        """
        Asynchronous chat generation with validation + retries.
        This method is a wrapper around the generate_async method of the parent class,
        ensuring that the schema_field is set to None, as RITS has problems with litellm schema validation.
        Therefore, we disable schema validation for RITS models, and use the default validation.

        Args:
            **kwargs: Additional keyword arguments passed to the generate_async method.
        Returns:
            Any: The generated response from the model.
        """

        return await super().generate_async(
            **{
                "schema_field": None,
                **kwargs,
            }
        )
