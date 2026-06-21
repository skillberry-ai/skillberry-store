from skillberry_plugin_simulate.config import SimulateConfig


def test_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("SIMULATE_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("SIMULATE_LLM_API_BASE", "https://azure.example/v1")
    monkeypatch.setenv("SIMULATION_HARNESS_IMAGE", "kaegis/simulation-harness:1.2")
    monkeypatch.setenv("SIMULATE_DATA_DIR", "/tmp/sim")
    cfg = SimulateConfig.from_env()
    assert cfg.llm_api_key == "sk-test"
    assert cfg.llm_api_base == "https://azure.example/v1"
    assert cfg.harness_image == "kaegis/simulation-harness:1.2"
    assert cfg.data_dir == "/tmp/sim"


def test_defaults(monkeypatch):
    monkeypatch.delenv("SIMULATION_HARNESS_IMAGE", raising=False)
    monkeypatch.delenv("SIMULATE_LLM_API_BASE", raising=False)
    cfg = SimulateConfig.from_env()
    assert cfg.harness_image == "simulation-harness:latest"
    assert cfg.llm_api_base is None


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
