"""
E2E test for the admin purge-all endpoint.

Populates the store with a realistic mix of objects (skills imported from the
bundled Anthropic ZIP resources, plus a VMCP and VNFS server for each skill),
calls DELETE /admin/purge-all, and verifies that every list endpoint returns
an empty result.
"""

import os
import pytest
import httpx

BASE_URL = "http://localhost:8000"

_RESOURCES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "anthropic")
)
_ZIP_COMPLEX = os.path.join(_RESOURCES_DIR, "sample_skill_complex_dep.zip")
_SKILL_FOLDER = os.path.join(_RESOURCES_DIR, "sample_skill")


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _import_skill_from_zip(client: httpx.AsyncClient, zip_path: str) -> str:
    """Import an Anthropic skill from a ZIP file and return its skill UUID."""
    with open(zip_path, "rb") as fh:
        zip_content = fh.read()

    response = await client.post(
        f"{BASE_URL}/skills/import-anthropic",
        data={"source_type": "zip", "snippet_mode": "file"},
        files={"zip_file": (os.path.basename(zip_path), zip_content, "application/zip")},
    )
    assert response.status_code == 200, f"Skill import from zip failed: {response.text}"
    result = response.json()
    assert result["success"] is True
    return result["skill_uuid"]


async def _import_skill_from_folder(client: httpx.AsyncClient, folder_path: str) -> str:
    """Import an Anthropic skill from a folder and return its skill UUID."""
    response = await client.post(
        f"{BASE_URL}/skills/import-anthropic",
        data={"source_type": "folder", "snippet_mode": "file", "folder_path": folder_path},
    )
    assert response.status_code == 200, f"Skill import from folder failed: {response.text}"
    result = response.json()
    assert result["success"] is True
    return result["skill_uuid"]


async def _create_vmcp(client: httpx.AsyncClient, name: str, skill_uuid: str) -> str:
    """Create a VMCP server linked to a skill and return its UUID."""
    response = await client.post(
        f"{BASE_URL}/vmcp_servers/",
        params={
            "name": name,
            "description": f"VMCP for {name}",
            "skill_uuid": skill_uuid,
        },
    )
    assert response.status_code == 200, f"VMCP creation failed for {name!r}: {response.text}"
    return response.json()["uuid"]


async def _create_vnfs(client: httpx.AsyncClient, name: str, skill_uuid: str) -> str:
    """Create a VNFS server linked to a skill and return its UUID."""
    response = await client.post(
        f"{BASE_URL}/vnfs_servers/",
        params={
            "name": name,
            "description": f"VNFS for {name}",
            "protocol": "webdav",
            "skill_uuid": skill_uuid,
        },
    )
    assert response.status_code == 200, f"VNFS creation failed for {name!r}: {response.text}"
    return response.json()["uuid"]


# ─── test ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_purge_all_clears_all_objects(run_sbs):
    """Populate the store with skills, VMCP, and VNFS objects, purge, then assert empty.

    Steps
    -----
    1. Import two Anthropic skills (one from ZIP, one from folder).
    2. For each skill, create one VMCP server and one VNFS server.
    3. Sanity-check that skills, tools, snippets, VMCP, and VNFS lists are non-empty.
    4. Call DELETE /admin/purge-all.
    5. Assert every list endpoint returns an empty collection.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:

        # ── 1. Import skills ──────────────────────────────────────────────────
        skill_uuids = []

        skill_uuid_zip = await _import_skill_from_zip(client, _ZIP_COMPLEX)
        skill_uuids.append(skill_uuid_zip)

        skill_uuid_folder = await _import_skill_from_folder(client, _SKILL_FOLDER)
        skill_uuids.append(skill_uuid_folder)

        # ── 2. Create VMCP + VNFS for each skill ──────────────────────────────
        for i, skill_uuid in enumerate(skill_uuids):
            await _create_vmcp(client, f"purge_test_vmcp_{i}", skill_uuid)
            await _create_vnfs(client, f"purge_test_vnfs_{i}", skill_uuid)

        # ── 3. Sanity-check: store is non-empty ───────────────────────────────
        r = await client.get(f"{BASE_URL}/skills/")
        assert r.status_code == 200
        assert len(r.json()) >= 2, "Expected at least 2 skills before purge"

        r = await client.get(f"{BASE_URL}/tools/")
        assert r.status_code == 200
        assert len(r.json()) > 0, "Expected tools before purge"

        # Phase 3 (vmcp/vnfs): list endpoint returns a bare array.
        r = await client.get(f"{BASE_URL}/vmcp_servers/")
        assert r.status_code == 200
        vmcp_before = r.json()
        assert len(vmcp_before) >= 2, "Expected at least 2 VMCP servers before purge"

        r = await client.get(f"{BASE_URL}/vnfs_servers/")
        assert r.status_code == 200
        vnfs_before = r.json()
        assert len(vnfs_before) >= 2, "Expected at least 2 VNFS servers before purge"

        # ── 4. Purge everything ───────────────────────────────────────────────
        purge_response = await client.delete(f"{BASE_URL}/admin/purge-all")
        assert purge_response.status_code == 200, (
            f"Purge-all failed: {purge_response.text}"
        )

        # ── 5. Assert all categories are empty ───────────────────────────────
        r = await client.get(f"{BASE_URL}/tools/")
        assert r.status_code == 200
        assert r.json() == [], f"Expected empty tools list after purge, got: {r.json()}"

        r = await client.get(f"{BASE_URL}/snippets/")
        assert r.status_code == 200
        assert r.json() == [], f"Expected empty snippets list after purge, got: {r.json()}"

        r = await client.get(f"{BASE_URL}/skills/")
        assert r.status_code == 200
        assert r.json() == [], f"Expected empty skills list after purge, got: {r.json()}"

        r = await client.get(f"{BASE_URL}/vmcp_servers/")
        assert r.status_code == 200
        vmcp_after = r.json()
        assert vmcp_after == [], (
            f"Expected empty VMCP list after purge, got: {vmcp_after}"
        )

        r = await client.get(f"{BASE_URL}/vnfs_servers/")
        assert r.status_code == 200
        vnfs_after = r.json()
        assert vnfs_after == [], (
            f"Expected empty VNFS list after purge, got: {vnfs_after}"
        )
