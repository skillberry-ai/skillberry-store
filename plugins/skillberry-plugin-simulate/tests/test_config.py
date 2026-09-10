from skillberry_plugin_simulate.config import DEFAULT_HARNESS_IMAGE, SimulateConfig


def test_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("SIMULATE_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("SIMULATE_LLM_API_BASE", "https://azure.example/v1")
    monkeypatch.setenv(
        "SIMULATION_HARNESS_IMAGE", "ghcr.io/skillberry-ai/simulation-harness:0.1.2"
    )
    monkeypatch.setenv("SIMULATE_DATA_DIR", "/tmp/sim")
    cfg = SimulateConfig.from_env()
    assert cfg.llm_api_key == "sk-test"
    assert cfg.llm_api_base == "https://azure.example/v1"
    assert cfg.harness_image == "ghcr.io/skillberry-ai/simulation-harness:0.1.2"
    assert cfg.data_dir == "/tmp/sim"


def test_defaults(monkeypatch):
    monkeypatch.delenv("SIMULATION_HARNESS_IMAGE", raising=False)
    monkeypatch.delenv("SIMULATE_LLM_API_BASE", raising=False)
    cfg = SimulateConfig.from_env()
    assert cfg.harness_image == DEFAULT_HARNESS_IMAGE
    assert cfg.llm_api_base is None


def test_default_image_is_the_external_release_line():
    """The harness ships from skillberry-ai/simulation-harness on GHCR.

    `latest` there tracks main, not releases, so the default must not use it.
    """
    assert DEFAULT_HARNESS_IMAGE == "ghcr.io/skillberry-ai/simulation-harness:0.1"
    assert not DEFAULT_HARNESS_IMAGE.endswith(":latest")


def test_harness_llm_overrides_read_from_env(monkeypatch):
    monkeypatch.setenv("SIMULATE_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SIMULATE_LLM_SKILL_GENERATION_MODEL", "gateway/gpt-4.1")
    monkeypatch.setenv("SIMULATE_LLM_SIMULATION_MODEL", "gateway/gpt-4.1-mini")
    cfg = SimulateConfig.from_env()
    assert cfg.llm_provider == "openai"
    assert cfg.llm_skill_generation_model == "gateway/gpt-4.1"
    assert cfg.llm_simulation_model == "gateway/gpt-4.1-mini"


def test_harness_llm_overrides_default_to_none(monkeypatch):
    """Unset means "leave the harness's own harness.yaml defaults alone"."""
    for var in (
        "SIMULATE_LLM_PROVIDER",
        "SIMULATE_LLM_SKILL_GENERATION_MODEL",
        "SIMULATE_LLM_SIMULATION_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)
    cfg = SimulateConfig.from_env()
    assert cfg.llm_provider is None
    assert cfg.llm_skill_generation_model is None
    assert cfg.llm_simulation_model is None


def test_is_configured_requires_key(monkeypatch):
    monkeypatch.delenv("SIMULATE_LLM_API_KEY", raising=False)
    assert SimulateConfig.from_env().is_configured() is False
    monkeypatch.setenv("SIMULATE_LLM_API_KEY", "sk-x")
    assert SimulateConfig.from_env().is_configured() is True


def test_ready_timeout_read_from_env(monkeypatch):
    monkeypatch.setenv("SIMULATE_READY_TIMEOUT_SECONDS", "600")
    cfg = SimulateConfig.from_env()
    assert cfg.ready_timeout_seconds == 600


def test_ready_timeout_default_is_large_enough(monkeypatch):
    monkeypatch.delenv("SIMULATE_READY_TIMEOUT_SECONDS", raising=False)
    cfg = SimulateConfig.from_env()
    assert cfg.ready_timeout_seconds >= 300
