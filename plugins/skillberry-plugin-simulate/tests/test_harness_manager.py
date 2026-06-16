from unittest.mock import MagicMock

from skillberry_plugin_simulate.config import SimulateConfig
from skillberry_plugin_simulate.harness_manager import HarnessManager, find_free_port


def _config():
    return SimulateConfig(
        llm_api_key="sk-x", llm_api_base=None, harness_image="sim:latest",
        data_dir="/tmp/sim", skills_store_path="/data/skills", logs_path="/data/logs",
    )


def test_find_free_port_in_range():
    port = find_free_port((8600, 8699), exclude=set())
    assert 8600 <= port <= 8699


def test_find_free_port_skips_excluded():
    port = find_free_port((8600, 8601), exclude={8600})
    assert port == 8601


def test_start_runs_container_with_env_and_ports():
    docker_client = MagicMock()
    container = MagicMock()
    container.id = "abc123"
    docker_client.containers.run.return_value = container

    mgr = HarnessManager(_config(), docker_client=docker_client)
    info = mgr.start(rest_port=8600, mcp_port=8700)

    assert info["container_id"] == "abc123"
    assert info["rest_port"] == 8600
    assert info["mcp_port"] == 8700
    assert info["rest_url"] == "http://127.0.0.1:8600"
    kwargs = docker_client.containers.run.call_args.kwargs
    assert kwargs["environment"]["LLM_API_KEY"] == "sk-x"
    assert kwargs["detach"] is True
    # REST 8086 and mcp_port mapped to the chosen host ports
    assert kwargs["ports"] == {"8086/tcp": 8600, "8700/tcp": 8700}


def test_llm_api_base_included_only_when_set():
    docker_client = MagicMock()
    docker_client.containers.run.return_value = MagicMock(id="x")
    cfg = _config()
    cfg.llm_api_base = "https://azure/v1"
    mgr = HarnessManager(cfg, docker_client=docker_client)
    mgr.start(rest_port=8600, mcp_port=8700)
    env = docker_client.containers.run.call_args.kwargs["environment"]
    assert env["LLM_API_BASE"] == "https://azure/v1"


def test_stop_removes_container():
    docker_client = MagicMock()
    container = MagicMock()
    docker_client.containers.get.return_value = container
    mgr = HarnessManager(_config(), docker_client=docker_client)
    mgr.stop("abc123")
    container.stop.assert_called_once()
    container.remove.assert_called_once()
