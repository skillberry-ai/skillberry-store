"""Environment-driven configuration for the Simulate This plugin."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load this plugin's own .env. The host store only loads its root .env, so a
# plugin that ships a .env (unlike the other plugins, which rely on host env
# vars / ~/.claude/settings.json) must load it itself. override=False keeps
# host-provided environment variables authoritative over the file.
_PLUGIN_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_PLUGIN_ENV, override=False)

# The harness is published from github.com/skillberry-ai/simulation-harness.
# Pinned to the release line (`0.1` == the newest v0.1.x release), NOT `latest`
# — upstream tags `latest` from every push to main, so it is ahead of the
# newest release and can change the REST contract between runs.
DEFAULT_HARNESS_IMAGE = "ghcr.io/skillberry-ai/simulation-harness:0.1"


@dataclass
class SimulateConfig:
    llm_api_key: Optional[str]
    llm_api_base: Optional[str]
    harness_image: str
    data_dir: str
    rest_port_range: tuple = (8600, 8699)
    mcp_port_range: tuple = (8700, 8799)
    skills_store_path: Optional[str] = None
    logs_path: Optional[str] = None
    ready_timeout_seconds: int = 600
    poll_interval_seconds: float = 2.0
    # Optional overrides for the harness's own LLM settings. The harness image
    # ships config/harness.yaml defaulting to provider `openai` with `gpt-4.1`
    # for both models; behind a gateway that namespaces model ids differently
    # those defaults do not resolve, so they are overridable per deployment.
    llm_provider: Optional[str] = None
    llm_skill_generation_model: Optional[str] = None
    llm_simulation_model: Optional[str] = None

    @classmethod
    def from_env(cls) -> "SimulateConfig":
        raw_timeout = os.getenv("SIMULATE_READY_TIMEOUT_SECONDS")
        return cls(
            llm_api_key=os.getenv("SIMULATE_LLM_API_KEY"),
            llm_api_base=os.getenv("SIMULATE_LLM_API_BASE"),
            harness_image=os.getenv("SIMULATION_HARNESS_IMAGE", DEFAULT_HARNESS_IMAGE),
            data_dir=os.getenv("SIMULATE_DATA_DIR", os.path.expanduser("~/.skillberry/simulate")),
            skills_store_path=os.getenv("SIMULATE_SKILLS_STORE_PATH"),
            logs_path=os.getenv("SIMULATE_LOGS_PATH"),
            ready_timeout_seconds=int(raw_timeout) if raw_timeout else 600,
            llm_provider=os.getenv("SIMULATE_LLM_PROVIDER"),
            llm_skill_generation_model=os.getenv("SIMULATE_LLM_SKILL_GENERATION_MODEL"),
            llm_simulation_model=os.getenv("SIMULATE_LLM_SIMULATION_MODEL"),
        )

    def is_configured(self) -> bool:
        return bool(self.llm_api_key)
