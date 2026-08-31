# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Coverage for the pinned fastembed model cache.

Background (PR #308 review, issue #9): nothing set HF_HOME / TRANSFORMERS_CACHE /
``cache_dir=``, and fastembed honours none of those (nor XDG_CACHE_HOME) — it uses
its own temp-dir cache, not the warmed ``~/.cache/huggingface``. Since
``/health/ready`` gates on ``encoder_warmup``, that put the ~80 MB ONNX download
(11.45 s measured) on the readiness critical path, repaid on every pod restart
where the temp dir is an ephemeral ``emptyDir``, and made air-gapped deployment
impossible.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from skillberry_store.vdbs import vector_db_interface as vdb
from skillberry_store.vdbs.vector_db_interface import (
    ENCODER_CACHE_DIR_ENV,
    encoder_cache_dir,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_explicit_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv(ENCODER_CACHE_DIR_ENV, str(tmp_path / "explicit"))
    monkeypatch.setenv("APP_HOME", "/app")

    assert encoder_cache_dir() == tmp_path / "explicit"


def test_container_layout_uses_app_home(monkeypatch):
    """The path the Dockerfile seeds, and the one $APP_HOME's chgrp/chmod covers."""
    monkeypatch.delenv(ENCODER_CACHE_DIR_ENV, raising=False)
    monkeypatch.setenv("APP_HOME", "/app")

    assert encoder_cache_dir() == Path("/app/.cache/fastembed")


def test_dev_checkout_falls_back_to_the_user_cache(monkeypatch, tmp_path):
    monkeypatch.delenv(ENCODER_CACHE_DIR_ENV, raising=False)
    monkeypatch.delenv("APP_HOME", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))

    assert encoder_cache_dir() == tmp_path / "xdg" / "fastembed"

    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    assert encoder_cache_dir() == tmp_path / "home" / ".cache" / "fastembed"


def test_cache_dir_is_never_a_bare_temp_dir(monkeypatch):
    """Whatever the environment, the cache must not be fastembed's temp default."""
    monkeypatch.delenv(ENCODER_CACHE_DIR_ENV, raising=False)
    monkeypatch.delenv("APP_HOME", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)

    resolved = encoder_cache_dir()

    assert resolved.is_absolute()
    assert resolved.name == "fastembed"


def test_encoder_is_constructed_with_the_resolved_cache_dir(monkeypatch, tmp_path):
    """The resolved directory must actually reach TextEmbedding(cache_dir=...)."""
    seen = {}

    class FakeEncoder:
        def __init__(self, model_name, **kwargs):
            seen["model_name"] = model_name
            seen["kwargs"] = kwargs

    monkeypatch.setattr(vdb, "TextEmbedding", FakeEncoder)
    monkeypatch.setattr(vdb, "_encoder", None)
    monkeypatch.setenv(ENCODER_CACHE_DIR_ENV, str(tmp_path / "weights"))

    vdb._get_encoder()

    assert seen["kwargs"].get("cache_dir") == str(tmp_path / "weights")
    assert (tmp_path / "weights").is_dir(), "the cache dir must be created eagerly"
    monkeypatch.setattr(vdb, "_encoder", None)


def test_unwritable_cache_dir_does_not_take_the_service_down(monkeypatch, tmp_path):
    """A read-only mount must degrade to the old behaviour, not fail startup."""
    constructed = []

    class FakeEncoder:
        def __init__(self, model_name, **kwargs):
            constructed.append(kwargs)

    blocker = tmp_path / "not-a-dir"
    blocker.write_text("i am a file")

    monkeypatch.setattr(vdb, "TextEmbedding", FakeEncoder)
    monkeypatch.setattr(vdb, "_encoder", None)
    monkeypatch.setenv(ENCODER_CACHE_DIR_ENV, str(blocker / "weights"))

    vdb._get_encoder()

    assert constructed == [{}], "should fall back to fastembed's own default cache"
    monkeypatch.setattr(vdb, "_encoder", None)


def test_dockerfile_preseeds_the_model_at_build_time():
    """Without a build-time seed the download still lands on the readiness path."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()

    seed = re.search(r"^RUN python -c .*?(?=\n[A-Z#]|\n\n)", dockerfile, re.DOTALL | re.MULTILINE)
    assert seed, "Dockerfile has no build-time encoder pre-seed step"
    body = seed.group(0)
    assert "text_to_vector" in body, "the seed step must actually embed something"
    assert "encoder_cache_dir" in body, (
        "the seed step should report where it seeded, so a miss is visible"
    )
    # The seed must happen in the builder stage, i.e. before the runtime FROM,
    # so the cache travels with the COPY --from=builder $APP_HOME.
    runtime_stage = dockerfile.index("# Runtime Stage")
    assert dockerfile.index(body) < runtime_stage, (
        "the pre-seed must run in the builder stage so the cache is copied into "
        "the runtime image under $APP_HOME"
    )


@pytest.mark.parametrize("var", ["HF_HOME", "TRANSFORMERS_CACHE"])
def test_no_reliance_on_variables_fastembed_ignores(var):
    """Documented trap: setting these would look like a fix and change nothing."""
    source = (
        REPO_ROOT / "src" / "skillberry_store" / "vdbs" / "vector_db_interface.py"
    ).read_text()
    code_lines = [
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    ]
    assert not [line for line in code_lines if f'"{var}"' in line or f"'{var}'" in line], (
        f"{var} is not honoured by fastembed; the cache must be pinned via cache_dir="
    )
