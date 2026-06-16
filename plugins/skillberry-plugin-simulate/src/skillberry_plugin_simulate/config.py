"""Environment-driven configuration for the Simulate This plugin."""
import os
from dataclasses import dataclass
from typing import Optional


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
    ready_timeout_seconds: int = 120
    poll_interval_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> "SimulateConfig":
        return cls(
            llm_api_key=os.getenv("SIMULATE_LLM_API_KEY"),
            llm_api_base=os.getenv("SIMULATE_LLM_API_BASE"),
            harness_image=os.getenv("SIMULATION_HARNESS_IMAGE", "simulation-harness:latest"),
            data_dir=os.getenv("SIMULATE_DATA_DIR", os.path.expanduser("~/.skillberry/simulate")),
            skills_store_path=os.getenv("SIMULATE_SKILLS_STORE_PATH"),
            logs_path=os.getenv("SIMULATE_LOGS_PATH"),
        )

    def is_configured(self) -> bool:
        return bool(self.llm_api_key)
