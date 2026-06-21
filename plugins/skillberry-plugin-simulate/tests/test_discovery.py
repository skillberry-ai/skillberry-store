from importlib.metadata import entry_points


def test_plugin_registered_as_entry_point():
    eps = entry_points()
    group = eps.select(group="skillberry_store.plugins") if hasattr(eps, "select") else eps.get("skillberry_store.plugins", [])
    names = {ep.name for ep in group}
    assert "simulate" in names


def test_entry_point_loads_to_plugin_class():
    from skillberry_store.plugins.base import PluginBase

    eps = entry_points()
    group = eps.select(group="skillberry_store.plugins") if hasattr(eps, "select") else eps.get("skillberry_store.plugins", [])
    ep = next(e for e in group if e.name == "simulate")
    cls = ep.load()
    assert issubclass(cls, PluginBase)
