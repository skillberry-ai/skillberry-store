# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Coverage for the startup vector-DB backend check.

Background (PR #308 review, issue #18, informational): lazy backend imports moved
failures from startup to first use — ``SBS_VDB=chroma`` on a core-only image now
fails at the first embedding call rather than at boot. The review offered "accept
as-is, or add a startup-time backend availability check"; this takes the check, but
only as a log line. Turning a misconfiguration into a boot failure would be a new
crash mode for deployments that currently start and serve their non-search
endpoints.
"""

from __future__ import annotations

import builtins

import pytest

from skillberry_store.fast_api import server as server_module
from skillberry_store.vdbs.identify_vdb import VectorDBType, check_backend_available


@pytest.mark.parametrize("db_type", [t.value for t in VectorDBType])
def test_installed_backends_report_no_problem(db_type):
    """This environment installs all three, so each must resolve cleanly."""
    assert check_backend_available(db_type) is None


def test_unsupported_type_is_reported_with_the_supported_list():
    problem = check_backend_available("postgres")

    assert problem is not None
    assert "postgres" in problem
    for supported in (t.value for t in VectorDBType):
        assert supported in problem, "the message should name the valid options"


def test_missing_backend_package_is_reported_not_raised(monkeypatch):
    """The core-only image case: the backend is configured but not installed."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if "chroma" in name:
            raise ImportError("No module named 'chromadb'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    problem = check_backend_available("chroma")

    assert problem is not None
    assert "chroma" in problem
    assert "not " in problem and "installed" in problem
    assert "extra" in problem, "say how to fix it"


def test_startup_logs_the_problem_without_raising(monkeypatch, caplog):
    """A misconfiguration must be visible at boot but must not become a crash."""
    monkeypatch.setenv("SBS_VDB", "not-a-backend")

    with caplog.at_level("ERROR"):
        server_module._check_vector_db_backend()  # must not raise

    assert "Vector DB backend check failed" in caplog.text
    assert "not-a-backend" in caplog.text


def test_startup_logs_the_healthy_case(monkeypatch, caplog):
    monkeypatch.setenv("SBS_VDB", "faiss")

    with caplog.at_level("INFO"):
        server_module._check_vector_db_backend()

    assert "is available" in caplog.text


def test_default_backend_is_faiss(monkeypatch, caplog):
    """Unset SBS_VDB must resolve, not report a problem."""
    monkeypatch.delenv("SBS_VDB", raising=False)

    with caplog.at_level("INFO"):
        server_module._check_vector_db_backend()

    assert "faiss" in caplog.text
    assert "check failed" not in caplog.text
