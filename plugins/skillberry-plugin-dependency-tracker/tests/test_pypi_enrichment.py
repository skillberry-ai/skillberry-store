"""Tests for best-effort PyPI enrichment (no real network)."""

import requests

from skillberry_plugin_dependency_tracker.resolver.base import (
    DependencyReport,
    PackageDep,
)
from skillberry_plugin_dependency_tracker.resolver.pypi import (
    enrich_from_pypi,
    enrich_report,
    pypi_enabled_from_env,
)


class _Resp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


_OK_PAYLOAD = {
    "info": {"version": "2.32.3"},
    "urls": [
        {"packagetype": "sdist", "digests": {"sha256": "sdistsha"}},
        {"packagetype": "bdist_wheel", "digests": {"sha256": "wheelsha"}},
    ],
}


def test_ok_enrichment_reports_update_and_hashes():
    sess = type("S", (), {"get": lambda self, url, timeout: _Resp(200, _OK_PAYLOAD)})()
    out = enrich_from_pypi("requests", "2.31.0", session=sess)
    assert out["status"] == "ok"
    assert out["latest_version"] == "2.32.3"
    assert out["update_available"] is True
    assert out["artifact_sha256"] == {"sdist": "sdistsha", "wheel": "wheelsha"}


def test_no_update_when_versions_equal():
    sess = type("S", (), {"get": lambda self, url, timeout: _Resp(200, _OK_PAYLOAD)})()
    out = enrich_from_pypi("requests", "2.32.3", session=sess)
    assert out["update_available"] is False


def test_timeout_does_not_raise():
    class _S:
        def get(self, url, timeout):
            raise requests.Timeout()

    out = enrich_from_pypi("x", "1.0", session=_S())
    assert out == {"status": "timeout"}


def test_rate_limit_429_is_soft_error():
    class _S:
        def get(self, url, timeout):
            return _Resp(429)

    out = enrich_from_pypi("x", "1.0", session=_S())
    assert out["status"] == "error"


def test_404_not_found():
    class _S:
        def get(self, url, timeout):
            return _Resp(404)

    out = enrich_from_pypi("x", "1.0", session=_S())
    assert out["status"] == "not_found"


def test_connection_error_does_not_raise():
    class _S:
        def get(self, url, timeout):
            raise requests.ConnectionError()

    out = enrich_from_pypi("x", "1.0", session=_S())
    assert out["status"] == "error"


def test_enrich_report_disabled_leaves_pypi_none():
    report = DependencyReport(packages={"a": PackageDep(name="a", version="1.0")})
    status = enrich_report(report, enabled=False)
    assert status == "skipped"
    assert report.packages["a"].pypi is None


def test_enrich_report_ok(monkeypatch):
    report = DependencyReport(
        packages={
            "a": PackageDep(name="a", version="1.0"),
            "b": PackageDep(name="b", version=None),  # unresolved -> skipped
        }
    )

    # Patch the module-level enrich_from_pypi the report iterator calls.
    import skillberry_plugin_dependency_tracker.resolver.pypi as pypi_mod

    monkeypatch.setattr(
        pypi_mod,
        "enrich_from_pypi",
        lambda dist, ver, timeout, session: {
            "status": "ok",
            "latest_version": "2.0",
            "update_available": True,
            "artifact_sha256": {},
        },
    )
    status = enrich_report(report, enabled=True)
    assert status == "ok"
    assert report.packages["a"].pypi["status"] == "ok"
    assert report.packages["b"].pypi is None  # version None -> not enriched


def test_pypi_enabled_from_env(monkeypatch):
    monkeypatch.delenv("DEPENDENCY_TRACKER_PYPI", raising=False)
    assert pypi_enabled_from_env() is True
    monkeypatch.setenv("DEPENDENCY_TRACKER_PYPI", "off")
    assert pypi_enabled_from_env() is False
    monkeypatch.setenv("DEPENDENCY_TRACKER_PYPI", "0")
    assert pypi_enabled_from_env() is False
    monkeypatch.setenv("DEPENDENCY_TRACKER_PYPI", "on")
    assert pypi_enabled_from_env() is True
