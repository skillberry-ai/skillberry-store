"""SDK-based tests for SkillberryPluginSimulate manifest + router shape."""
from skillberry_plugin_simulate.plugin import SkillberryPluginSimulate


def test_plugin_manifest_slug():
    plugin = SkillberryPluginSimulate()
    assert plugin.manifest.slug == "simulate"


def test_plugin_manifest_name():
    plugin = SkillberryPluginSimulate()
    assert plugin.manifest.name == "Skill Simulator"


def test_plugin_manifest_version():
    plugin = SkillberryPluginSimulate()
    assert plugin.manifest.version == "0.1.0"


def test_plugin_manifest_type_evaluator():
    plugin = SkillberryPluginSimulate()
    assert plugin.manifest.plugin_type == "evaluator"


def test_plugin_manifest_has_api():
    plugin = SkillberryPluginSimulate()
    assert plugin.manifest.has_api is True


def test_plugin_manifest_required_env_docker_host_optional():
    plugin = SkillberryPluginSimulate()
    envs = {e.name: e for e in plugin.manifest.required_env}
    assert "DOCKER_HOST" in envs
    assert envs["DOCKER_HOST"].required is False


def test_plugin_router_exposes_expected_paths():
    plugin = SkillberryPluginSimulate()
    router = plugin.get_router()
    assert router is not None
    paths = {r.path for r in router.routes}
    assert "/simulate" in paths
    assert "/status/{job_id}" in paths
    assert "/toggle" in paths
    assert "/teardown" in paths
    assert "/active/{skill_uuid}" in paths
