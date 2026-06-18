"""Tests for local importlib.metadata resolution (offline, against the dev env)."""

import json

from skillberry_plugin_dependency_tracker.resolver import local as local_mod
from skillberry_plugin_dependency_tracker.resolver.local import (
    _requirement_applies,
    resolve_local,
)

# ── default-vs-extra requirement filtering (the 74-unresolved bug) ────────────


def test_requirement_applies_excludes_extras():
    # extra-gated deps are NOT default runtime deps
    assert _requirement_applies("PySocks; extra == 'socks'") is False
    assert _requirement_applies('chardet<8; extra == "use-chardet-on-py3"') is False
    assert (
        _requirement_applies(
            "brotli>=1.2.0; (platform_python_implementation == 'CPython') "
            "and extra == 'brotli'"
        )
        is False
    )


def test_requirement_applies_keeps_unmarked_and_satisfied():
    assert _requirement_applies("urllib3>=1.21.1,<3") is True
    assert _requirement_applies("idna (>=2.5,<4)") is True
    # an always-true env marker (no extra) is a real runtime dep
    assert _requirement_applies("certifi; python_version >= '3.0'") is True


def test_requires_for_requests_drops_optional_extras(monkeypatch):
    # Against the installed `requests`: PySocks/chardet (extras) must NOT appear.
    reqs = local_mod.local_requires("requests")
    lower = {r.lower() for r in reqs}
    assert "pysocks" not in lower
    assert "chardet" not in lower
    # but its real runtime deps are present
    assert any("urllib3" == r.lower() for r in reqs)


def test_resolves_installed_requests_with_transitive_deps():
    # `requests` is a declared dependency of this plugin, so it (and its deps:
    # urllib3, certifi, idna, charset-normalizer) are installed in the test env.
    report = resolve_local({"requests"})

    assert "requests" in report.packages
    req = report.packages["requests"]
    assert req.version is not None
    assert req.source == "local"
    assert req.direct is True
    assert req.depth == 0
    # transitive deps were walked at max depth
    assert req.requires, "requests should declare Requires-Dist"
    assert "urllib3" in report.packages
    assert report.packages["urllib3"].depth >= 1
    assert report.packages["urllib3"].direct is False
    # edges captured the hierarchy
    assert any(e[0] == "<root>" and e[1] == "requests" for e in report.edges)


def test_unresolved_import_recorded_not_dropped():
    report = resolve_local({"definitely_not_a_real_pkg_xyz"})
    assert report.packages == {}
    assert report.unresolved
    assert report.unresolved[0]["import_name"] == "definitely_not_a_real_pkg_xyz"
    assert report.unresolved[0]["reason"] == "no_distribution"


def test_local_module_classified_separately():
    # `helpers` is bundled with the object; `lxml_not_here` is a real external
    # package that is simply absent. They must be classified differently.
    report = resolve_local({"helpers", "lxml_not_here"}, local_modules={"helpers"})
    reasons = {u["import_name"]: u["reason"] for u in report.unresolved}
    assert reasons["helpers"] == "local_module"
    assert reasons["lxml_not_here"] == "no_distribution"

    block = report.to_extra_block(
        generated_at="T", plugin_version="0.1.0", python_version="3.11.0"
    )
    # local modules are NOT counted as missing external deps
    assert block["summary"]["missing_count"] == 1
    assert block["summary"]["local_module_count"] == 1
    assert block["summary"]["unresolved_count"] == 2


def test_cycle_protection(monkeypatch):
    # Fake a -> b -> a cycle; both installed (versioned), each expanded once.
    monkeypatch.setattr(
        local_mod, "import_to_distributions", lambda n: [n] if n == "a" else []
    )
    monkeypatch.setattr(local_mod, "local_version", lambda d: "1.0.0")
    monkeypatch.setattr(local_mod, "local_record_hashes", lambda d: [])
    monkeypatch.setattr(
        local_mod,
        "local_requires",
        lambda d: ["b"] if d == "a" else ["a"],
    )

    report = resolve_local({"a"})
    # terminates, each node present once
    assert set(report.packages) == {"a", "b"}
    assert report.packages["a"].direct is True
    assert report.packages["b"].direct is False


def test_output_is_deterministic(monkeypatch):
    monkeypatch.setattr(
        local_mod, "import_to_distributions", lambda n: [n] if n in ("a",) else []
    )
    monkeypatch.setattr(local_mod, "local_version", lambda d: "1.0.0")
    monkeypatch.setattr(local_mod, "local_record_hashes", lambda d: [])
    monkeypatch.setattr(
        local_mod, "local_requires", lambda d: ["c", "b"] if d == "a" else []
    )

    r1 = resolve_local({"a"}).to_extra_block(
        generated_at="T", plugin_version="0.1.0", python_version="3.11.0"
    )
    r2 = resolve_local({"a"}).to_extra_block(
        generated_at="T", plugin_version="0.1.0", python_version="3.11.0"
    )
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    # requires sorted
    assert r1["packages"]["a"]["requires"] == ["b", "c"]


def test_uninstalled_child_marked_unresolved(monkeypatch):
    # a is installed and requires b, but b is not installed.
    monkeypatch.setattr(
        local_mod, "import_to_distributions", lambda n: ["a"] if n == "a" else []
    )
    monkeypatch.setattr(
        local_mod, "local_version", lambda d: "1.0.0" if d == "a" else None
    )
    monkeypatch.setattr(local_mod, "local_record_hashes", lambda d: [])
    monkeypatch.setattr(
        local_mod, "local_requires", lambda d: ["b"] if d == "a" else []
    )

    report = resolve_local({"a"})
    assert "a" in report.packages
    assert "b" not in report.packages  # not expanded
    assert any(u["import_name"] == "b" for u in report.unresolved)
