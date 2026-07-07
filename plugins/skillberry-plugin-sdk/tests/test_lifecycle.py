from fastapi.testclient import TestClient

from skillberry_plugin_sdk.lifecycle import PluginLifecycleBase
from skillberry_plugin_sdk.manifest import PluginManifest


class DummyPlugin(PluginLifecycleBase):
    def __init__(self) -> None:
        manifest = PluginManifest(
            name="Dummy", slug="dummy", version="0.1.0", has_api=False
        )
        super().__init__(manifest=manifest)


def test_lifecycle_health_and_info() -> None:
    plugin = DummyPlugin()
    app = plugin.build_app()
    client = TestClient(app)

    r = client.get("/lifecycle/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    r = client.get("/lifecycle/info")
    assert r.status_code == 200
    assert r.json()["slug"] == "dummy"

    r = client.get("/lifecycle/ready")
    assert r.status_code == 200
    assert r.json()["ready"] is True


def test_validate_env_flags_missing() -> None:
    plugin = DummyPlugin()
    plugin._manifest = PluginManifest(
        name="Dummy", slug="dummy", version="0.1.0",
        required_env=[{"name": "MUST_HAVE", "required": True}],
    )
    assert plugin.validate_env({}) == ["MUST_HAVE"]
    assert plugin.validate_env({"MUST_HAVE": "yes"}) == []
