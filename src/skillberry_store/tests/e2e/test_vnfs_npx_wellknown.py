"""End-to-end tests for npx-compatible WebDAV vNFS servers.

These tests exercise the full flow:

  1. Create a slug-safe skill in the store.
  2. Create a WebDAV vNFS pointing at it with npx_compat=True.
  3. Hit /.well-known/agent-skills/index.json over HTTP.
  4. Confirm every advertised file is fetchable at both the well-known path
     and the top-level (WebDAV mount) path.
  5. Invoke `npx skills add http://127.0.0.1:<port> -l` and assert the CLI
     successfully discovers the skill (`-l/--list` is the CLI's "dry run"
     switch — it lists the resolved skills without touching agent dirs).

The npx step is skipped automatically if the `npx` binary is not available
on PATH, so this file remains runnable in environments without Node.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import uuid as uuid_lib

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def slug_safe_skill_uuid(run_sbs) -> str:
    """Create a skill with a slug-safe name and return its UUID.

    We can't reuse the existing ``sample_skill_complex_dep`` fixture because
    its name contains underscores, which fails the npx / Anthropic slug rule.
    """
    unique = uuid_lib.uuid4().hex[:8]
    name = f"npx-demo-{unique}"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{BASE_URL}/skills/",
            params={
                "name": name,
                "description": (
                    "A minimal skill used to verify that skillberry-store can "
                    "publish itself through the well-known agent-skills endpoint."
                ),
                "state": "approved",
            },
        )
        assert response.status_code == 200, response.text
        skill_uuid = response.json()["uuid"]
    yield skill_uuid
    # Best-effort cleanup — swallow errors so we don't mask real failures.
    try:
        with httpx.Client(timeout=10.0) as client:
            client.delete(f"{BASE_URL}/skills/{skill_uuid}")
    except Exception:
        pass


@pytest.fixture
def npx_vnfs(run_sbs, slug_safe_skill_uuid):
    """Create a WebDAV+npx_compat vNFS and clean it up after the test."""
    vnfs_name = f"npx-vnfs-{uuid_lib.uuid4().hex[:6]}"
    with httpx.Client(timeout=30.0) as client:
        create = client.post(
            f"{BASE_URL}/vnfs_servers/",
            params={
                "name": vnfs_name,
                "description": "vNFS with npx_compat=true for e2e verification.",
                "protocol": "webdav",
                "npx_compat": "true",
                "skill_uuid": slug_safe_skill_uuid,
            },
        )
        assert create.status_code == 200, create.text
        payload = create.json()
        port = payload["port"]
        uuid = payload["uuid"]
        yield {"name": vnfs_name, "uuid": uuid, "port": port}

        try:
            client.delete(f"{BASE_URL}/vnfs_servers/{uuid}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_npx_compat_rejected_on_nfs(run_sbs, slug_safe_skill_uuid):
    """Schema validator refuses npx_compat with protocol=nfs (regardless of skill)."""
    unique = uuid_lib.uuid4().hex[:6]
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{BASE_URL}/vnfs_servers/",
            params={
                "name": f"npx-nfs-{unique}",
                "description": "should be rejected",
                "protocol": "nfs",
                "npx_compat": "true",
                "skill_uuid": slug_safe_skill_uuid,
            },
        )
    # FastAPI translates the pydantic validation error to 422.
    assert response.status_code in (400, 422), response.text
    assert "webdav" in response.text.lower()


@pytest.mark.asyncio
async def test_wellknown_manifest_is_served(npx_vnfs):
    """GET /.well-known/agent-skills/index.json returns the expected shape."""
    port = npx_vnfs["port"]
    # Give the WebDAV backend a beat to start listening.
    await asyncio.sleep(1.0)
    url = f"http://127.0.0.1:{port}/.well-known/agent-skills/index.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Retry briefly in case the backend is still spinning up.
        last_exc = None
        for _ in range(10):
            try:
                response = await client.get(url)
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                await asyncio.sleep(0.5)
        else:
            raise AssertionError(f"WebDAV backend not reachable: {last_exc}")

    assert response.status_code == 200, response.text
    payload = json.loads(response.text)
    assert payload["version"] == 1
    assert len(payload["skills"]) == 1
    entry = payload["skills"][0]
    assert entry["name"].startswith("npx-demo-")
    assert "SKILL.md" in entry["files"]


@pytest.mark.asyncio
async def test_every_advertised_file_is_fetchable(npx_vnfs):
    """Every path in the manifest is served at both well-known and top-level paths."""
    port = npx_vnfs["port"]
    await asyncio.sleep(1.0)
    base = f"http://127.0.0.1:{port}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        manifest = (await client.get(f"{base}/.well-known/agent-skills/index.json")).json()
        entry = manifest["skills"][0]
        slug = entry["name"]
        for rel in entry["files"]:
            wellknown_url = f"{base}/.well-known/agent-skills/{slug}/{rel}"
            top_level_url = f"{base}/{slug}/{rel}"
            wk_resp = await client.get(wellknown_url)
            tl_resp = await client.get(top_level_url)
            assert wk_resp.status_code == 200, f"missing at well-known: {rel}"
            assert tl_resp.status_code == 200, f"missing at top-level: {rel}"
            # Files must be byte-identical between the two mount points.
            assert wk_resp.content == tl_resp.content, f"file diverges: {rel}"


@pytest.mark.asyncio
async def test_install_url_is_exposed_on_get(npx_vnfs):
    """`GET /vnfs_servers/<uuid>` includes install_url for npx-compat WebDAV vNFS."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{BASE_URL}/vnfs_servers/{npx_vnfs['uuid']}")
    assert response.status_code == 200
    body = response.json()
    assert body.get("npx_compat") is True
    assert body.get("install_url")
    assert body["install_url"].endswith(f":{npx_vnfs['port']}")


@pytest.mark.skipif(shutil.which("npx") is None, reason="npx binary not on PATH")
@pytest.mark.asyncio
async def test_npx_skills_add_list_engages_endpoint(npx_vnfs):
    """`npx skills add <url> --list` reaches the well-known endpoint successfully.

    ``--list`` (``-l``) tells the CLI to enumerate the skills the source
    exposes without installing them anywhere — the closest thing to a dry-run
    and enough to prove the well-known handshake works end-to-end.
    """
    port = npx_vnfs["port"]
    await asyncio.sleep(1.0)

    # Confirm the endpoint is up before we invoke the CLI so we can tell a
    # server-side failure apart from a CLI failure.
    async with httpx.AsyncClient(timeout=10.0) as client:
        preflight = await client.get(
            f"http://127.0.0.1:{port}/.well-known/agent-skills/index.json"
        )
        assert preflight.status_code == 200, preflight.text
        slug = preflight.json()["skills"][0]["name"]

    env = {**os.environ, "npm_config_yes": "true"}
    proc = await asyncio.create_subprocess_exec(
        "npx",
        "skills",
        "add",
        f"http://127.0.0.1:{port}",
        "--list",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    try:
        stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        raise AssertionError("`npx skills add --list` timed out")

    output = stdout_bytes.decode("utf-8", errors="replace")
    assert proc.returncode == 0, (
        f"`npx skills add --list` failed (exit {proc.returncode}):\n{output}"
    )
    # The skill's slug should appear in the CLI output listing.
    assert slug in output, (
        f"`npx skills add --list` did not surface the skill '{slug}':\n{output}"
    )
