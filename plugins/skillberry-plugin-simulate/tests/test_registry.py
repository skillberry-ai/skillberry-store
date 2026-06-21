import pytest

from skillberry_plugin_simulate.registry import ActiveVmcpRegistry


def _reg(tmp_path):
    return ActiveVmcpRegistry(str(tmp_path / "registry.json"))


def test_upsert_and_get(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert("skill-1", real_vmcp_uuid="real-1", sim_vmcp_uuid="sim-1")
    entry = reg.get("skill-1")
    assert entry == {"active": "real", "real_vmcp_uuid": "real-1", "sim_vmcp_uuid": "sim-1"}


def test_persists_across_instances(tmp_path):
    path = str(tmp_path / "registry.json")
    ActiveVmcpRegistry(path).upsert("skill-1", real_vmcp_uuid="real-1", sim_vmcp_uuid="sim-1")
    assert ActiveVmcpRegistry(path).get("skill-1")["real_vmcp_uuid"] == "real-1"


def test_set_active_sim_requires_sim_vmcp(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert("skill-1", real_vmcp_uuid="real-1", sim_vmcp_uuid=None)
    with pytest.raises(ValueError):
        reg.set_active("skill-1", "sim")


def test_toggle_flips(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert("skill-1", real_vmcp_uuid="real-1", sim_vmcp_uuid="sim-1")
    assert reg.toggle("skill-1") == "sim"
    assert reg.toggle("skill-1") == "real"


def test_remove(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert("skill-1", real_vmcp_uuid="real-1", sim_vmcp_uuid="sim-1")
    reg.remove("skill-1")
    assert reg.get("skill-1") is None


def test_active_vmcp_uuid_resolves(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert("skill-1", real_vmcp_uuid="real-1", sim_vmcp_uuid="sim-1")
    assert reg.active_vmcp_uuid("skill-1") == "real-1"
    reg.set_active("skill-1", "sim")
    assert reg.active_vmcp_uuid("skill-1") == "sim-1"
