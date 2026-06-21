from skillberry_plugin_simulate.plugin import SkillberryPluginSimulate


def test_plugin_metadata():
    plugin = SkillberryPluginSimulate()
    md = plugin.metadata
    assert md.name == "Simulate This"
    assert md.version
    assert md.plugin_type.value in {"creator", "evaluator", "optimizer", "importer"}


def test_plugin_router_exists():
    plugin = SkillberryPluginSimulate()
    router = plugin.get_router()
    assert router is not None
    paths = {r.path for r in router.routes}
    assert "/simulate" in paths
    assert "/status/{job_id}" in paths
    assert "/toggle" in paths
    assert "/teardown" in paths
    assert "/active/{skill_uuid}" in paths


def test_ui_config_actions():
    plugin = SkillberryPluginSimulate()
    cfg = plugin.get_ui_config()
    labels = {a["label"] for a in cfg["actions"]}
    assert {"Simulate this", "Toggle real/sim", "Tear down"} <= labels
