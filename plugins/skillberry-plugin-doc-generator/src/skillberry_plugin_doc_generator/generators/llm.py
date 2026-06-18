"""Optional LLM-backed documentation generator.

This backend is used automatically *only when an LLM is configured* — i.e. when
``llm-switchboard`` is importable and the provider's credentials (e.g. an API
key) are present in the environment. It is wired exactly like the security
evaluator plugin: ``llm_switchboard.get_llm(provider)`` →
``Client(model_name=...)`` → ``await client.generate_async(prompt=...)``.

No specific model is hardcoded. Provider/model are read from the same env vars
the other plugins use (``LLM_PROVIDER`` / ``LLM_MODEL``), so the host chooses
which frontier model (if any) to plug in.

If construction fails (no switchboard, no key, misconfig) the factory falls back
to the deterministic ``HeuristicGenerator``; if a *runtime* call fails, this
backend falls back to the heuristic result for that one object, so documentation
generation never hard-fails just because the model is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from .base import Documentation, ObjectDoc, ParamDoc
from .heuristic import HeuristicGenerator

logger = logging.getLogger(__name__)


# API-key env vars to look for, by provider-name prefix. Several SDK clients
# (e.g. OpenAI) do NOT validate the key at construction time — they only fail on
# the first call — so we gate on the key being present in the environment. This
# is what makes "default stays as-is unless an API key exists" hold precisely.
_PROVIDER_KEY_ENVS = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "azure": ("AZURE_OPENAI_API_KEY", "OPENAI_API_KEY"),
    "watsonx": ("WATSONX_APIKEY", "WATSONX_API_KEY"),
    "rits": ("RITS_API_KEY",),
}


def _has_api_key(provider_name: str) -> bool:
    """True if an API key for ``provider_name`` is present in the environment.

    An explicit ``LLM_API_KEY`` always counts. Otherwise we match the provider
    name prefix (e.g. ``openai.async`` -> ``OPENAI_API_KEY``). Unknown providers
    are treated as "key present" so a host using a custom provider isn't blocked.
    """
    if os.getenv("LLM_API_KEY"):
        return True
    prefix = provider_name.split(".", 1)[0].lower()
    envs = _PROVIDER_KEY_ENVS.get(prefix)
    if envs is None:
        return True  # custom/unknown provider: don't second-guess the host
    return any(os.getenv(e) for e in envs)


def build_llm_client():
    """Construct an LLM client from env, or return ``None`` if unavailable.

    Mirrors the security evaluator's initialization, but additionally requires
    that the provider's API key is actually present, so the deterministic
    default is kept unless a key exists. Returns ``(client, label)`` on success,
    or ``None`` when switchboard is missing, no key is configured, or
    construction fails.
    """
    try:
        from llm_switchboard import get_llm
    except ImportError:
        logger.info("doc-gen: llm-switchboard not installed; using heuristic backend")
        return None

    provider_name = os.getenv("LLM_PROVIDER", "openai.async")
    model_name = os.getenv("LLM_MODEL", "gpt-4")

    if not _has_api_key(provider_name):
        logger.info(
            "doc-gen: no API key for provider %s; using heuristic backend",
            provider_name,
        )
        return None

    try:
        client_cls = get_llm(provider_name)
        client = client_cls(model_name=model_name)
    except Exception as e:
        # Most commonly: missing API key for the configured provider.
        logger.info("doc-gen: LLM not configured (%s); using heuristic backend", e)
        return None
    return client, f"{provider_name}:{model_name}"


_SYSTEM_INSTRUCTION = (
    "You are documenting a {object_type} from a curated store of reusable "
    "AI-agent building blocks. Produce clear, accurate, reusable documentation "
    "grounded ONLY in the information given — do not invent behavior, "
    "parameters, or examples that are not supported by the input."
)


def _build_prompt(obj: ObjectDoc, existing: Optional[Documentation]) -> str:
    """Construct the generation prompt from the normalized object view."""
    parts: List[str] = [_SYSTEM_INSTRUCTION.format(object_type=obj.object_type)]
    parts.append(f"\nName: {obj.name}")
    if obj.description:
        parts.append(
            f"Existing author description (preserve its intent): {obj.description}"
        )
    if obj.tags:
        parts.append(f"Tags: {', '.join(obj.tags)}")
    if obj.parameters:
        param_lines = [
            f"  - {p.name} (type={p.type}, required={p.required})"
            + (f": {p.description}" if p.description else "")
            for p in obj.parameters
        ]
        parts.append("Parameters:\n" + "\n".join(param_lines))
    if obj.references:
        parts.append(f"References: {', '.join(obj.references)}")
    if obj.code_blobs:
        # Bound the code we send; this is documentation, not analysis.
        joined = "\n\n".join(obj.code_blobs)
        parts.append("Code / content (truncated):\n" + joined[:6000])

    parts.append(
        "\nReturn ONLY a JSON object with exactly these fields:\n"
        '- "description": string — a clear summary of what this is and does\n'
        '- "when_to_use": string — when an agent/user should reach for it\n'
        '- "parameters": array of {"name","type","required","description"} '
        "(echo the inputs above, filling in clear descriptions; [] if none)\n"
        '- "examples": array of strings — at least one concise usage example\n'
        "Return ONLY the JSON object, no prose, no code fences."
    )
    return "\n".join(parts)


def _parse_documentation(response: str) -> Documentation:
    """Parse the model's JSON response into a Documentation (raises on failure)."""
    start = response.find("{")
    end = response.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    data: Dict[str, Any] = json.loads(response[start:end])

    params: List[ParamDoc] = []
    for p in data.get("parameters") or []:
        if not isinstance(p, dict) or not p.get("name"):
            continue
        params.append(
            ParamDoc(
                name=p["name"],
                type=p.get("type"),
                required=bool(p.get("required")),
                description=(p.get("description") or "").strip(),
            )
        )
    examples = [str(e) for e in (data.get("examples") or []) if str(e).strip()]
    return Documentation(
        description=(data.get("description") or "").strip(),
        when_to_use=(data.get("when_to_use") or "").strip(),
        parameters=params,
        examples=examples,
        # The LLM is generating fresh prose; record the backend in mode-agnostic
        # terms. The plugin records the backend name separately.
        mode=data.get("mode") or "generated",
    )


class LLMGenerator:
    """LLM-backed generator. Falls back to heuristic on any runtime failure."""

    def __init__(self, client: Any, label: str):
        self._client = client
        self._label = label
        self.name = f"llm({label})"
        self._fallback = HeuristicGenerator()

    def generate(
        self, obj: ObjectDoc, existing: Optional[Documentation]
    ) -> Documentation:
        prompt = _build_prompt(obj, existing)
        try:
            response = self._run(prompt)
            doc = _parse_documentation(response)
            if doc.is_empty():
                raise ValueError("LLM returned empty documentation")
            return doc
        except Exception as e:
            logger.warning(
                "doc-gen: LLM generation failed (%s); falling back to heuristic", e
            )
            return self._fallback.generate(obj, existing)

    def _run(self, prompt: str) -> str:
        """Call the (async) switchboard client from sync context safely.

        The plugin's public methods are ``async`` but call ``generate`` directly
        (sync). switchboard exposes ``generate_async``; we drive it on a private
        event loop so this stays a drop-in for the heuristic backend.
        """
        import asyncio

        coro = self._client.generate_async(prompt=prompt)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            # We're already inside a running loop (the FastAPI request handler).
            # Run the coroutine to completion on a dedicated loop in a thread to
            # avoid "loop already running".
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return asyncio.run(coro)
