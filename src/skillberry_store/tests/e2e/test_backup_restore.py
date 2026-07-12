"""
E2E test for the admin backup and restore endpoints.

Steps
-----
1. Import two Anthropic skills (one from ZIP, one from folder).
2. For each skill, create one VMCP server and one VNFS server.
3. Record the full population: lists of tools, snippets, skills, VMCP, and VNFS.
4. Call GET /admin/backup and capture the ZIP response.
5. Call DELETE /admin/purge-all to wipe all data.
6. Call POST /admin/restore with the captured ZIP.
7. Re-record the population and compare it against the pre-backup snapshot,
   ignoring runtime-only fields that are not preserved in a backup.
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

# Runtime-only fields stripped by the backup endpoint; not expected to survive restore.
_VMCP_RUNTIME_FIELDS = {"running", "runtime"}
_VNFS_RUNTIME_FIELDS = {"running", "export_path"}


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


async def _snapshot(client: httpx.AsyncClient) -> dict:
    """Return a dict keyed by object type with sorted lists of their dicts.

    Runtime-only fields (running, export_path, runtime) are stripped before
    recording so that comparisons are not affected by server state.
    """

    def _strip(items: list, drop: set) -> list:
        return sorted(
            [{k: v for k, v in item.items() if k not in drop} for item in items],
            key=lambda d: d.get("uuid", ""),
        )

    r = await client.get(f"{BASE_URL}/tools/")
    assert r.status_code == 200
    tools = _strip(r.json(), set())

    r = await client.get(f"{BASE_URL}/snippets/")
    assert r.status_code == 200
    snippets = _strip(r.json(), set())

    r = await client.get(f"{BASE_URL}/skills/")
    assert r.status_code == 200
    skills = _strip(r.json(), set())

    # Phase 3 (vmcp/vnfs): list endpoints return bare arrays.
    r = await client.get(f"{BASE_URL}/vmcp_servers/")
    assert r.status_code == 200
    vmcp = _strip(r.json(), _VMCP_RUNTIME_FIELDS)

    r = await client.get(f"{BASE_URL}/vnfs_servers/")
    assert r.status_code == 200
    vnfs = _strip(r.json(), _VNFS_RUNTIME_FIELDS)

    return {
        "tools": tools,
        "snippets": snippets,
        "skills": skills,
        "vmcp": vmcp,
        "vnfs": vnfs,
    }


# ─── test ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_backup_and_restore(run_sbs):
    """Full backup-restore round-trip test.

    Populates the store, takes a backup, purges, restores, then asserts the
    population is identical to the pre-backup snapshot.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:

        # ── 1. Import two Anthropic skills ────────────────────────────────────
        skill_uuid_zip = await _import_skill_from_zip(client, _ZIP_COMPLEX)
        skill_uuid_folder = await _import_skill_from_folder(client, _SKILL_FOLDER)
        skill_uuids = [skill_uuid_zip, skill_uuid_folder]

        # ── 2. Create one VMCP + one VNFS per skill ───────────────────────────
        for i, skill_uuid in enumerate(skill_uuids):
            await _create_vmcp(client, f"br_test_vmcp_{i}", skill_uuid)
            await _create_vnfs(client, f"br_test_vnfs_{i}", skill_uuid)

        # ── 3. Record pre-backup population ──────────────────────────────────
        before = await _snapshot(client)

        assert len(before["skills"]) >= 2,  "Expected at least 2 skills before backup"
        assert len(before["tools"]) > 0,    "Expected tools before backup"
        assert len(before["vmcp"]) >= 2,    "Expected at least 2 VMCP servers before backup"
        assert len(before["vnfs"]) >= 2,    "Expected at least 2 VNFS servers before backup"

        # ── 4. Backup ─────────────────────────────────────────────────────────
        backup_response = await client.get(f"{BASE_URL}/admin/backup")
        assert backup_response.status_code == 200, (
            f"Backup failed: {backup_response.text}"
        )
        assert backup_response.headers.get("content-type") == "application/zip", (
            f"Expected ZIP content-type, got: {backup_response.headers.get('content-type')}"
        )
        backup_zip_bytes = backup_response.content
        assert len(backup_zip_bytes) > 0, "Backup ZIP is empty"

        # ── 5. Purge ──────────────────────────────────────────────────────────
        purge_response = await client.delete(f"{BASE_URL}/admin/purge-all")
        assert purge_response.status_code == 200, (
            f"Purge-all failed: {purge_response.text}"
        )

        # Confirm the store is empty
        r = await client.get(f"{BASE_URL}/skills/")
        assert r.json() == [], "Store should be empty after purge"

        # ── 6. Restore ────────────────────────────────────────────────────────
        restore_response = await client.post(
            f"{BASE_URL}/admin/restore",
            files={"backup_file": ("backup.json.zip", backup_zip_bytes, "application/zip")},
        )
        assert restore_response.status_code == 200, (
            f"Restore failed: {restore_response.text}"
        )
        restore_result = restore_response.json()
        assert restore_result["imported_counts"]["tools"] == len(before["tools"]), (
            f"Tool count mismatch after restore: "
            f"expected {len(before['tools'])}, got {restore_result['imported_counts']['tools']}"
        )
        assert restore_result["imported_counts"]["snippets"] == len(before["snippets"]), (
            f"Snippet count mismatch after restore: "
            f"expected {len(before['snippets'])}, got {restore_result['imported_counts']['snippets']}"
        )
        assert restore_result["imported_counts"]["skills"] == len(before["skills"]), (
            f"Skill count mismatch after restore: "
            f"expected {len(before['skills'])}, got {restore_result['imported_counts']['skills']}"
        )
        assert restore_result["imported_counts"]["vmcp_servers"] == len(before["vmcp"]), (
            f"VMCP count mismatch after restore: "
            f"expected {len(before['vmcp'])}, got {restore_result['imported_counts']['vmcp_servers']}"
        )
        assert restore_result["imported_counts"]["vnfs_servers"] == len(before["vnfs"]), (
            f"VNFS count mismatch after restore: "
            f"expected {len(before['vnfs'])}, got {restore_result['imported_counts']['vnfs_servers']}"
        )

        # ── 7. Compare post-restore population with pre-backup snapshot ───────
        after = await _snapshot(client)

        assert after["tools"] == before["tools"], (
            f"Tools differ after restore.\n"
            f"Before: {[t['name'] for t in before['tools']]}\n"
            f"After:  {[t['name'] for t in after['tools']]}"
        )
        assert after["snippets"] == before["snippets"], (
            f"Snippets differ after restore.\n"
            f"Before: {[s['name'] for s in before['snippets']]}\n"
            f"After:  {[s['name'] for s in after['snippets']]}"
        )
        assert after["skills"] == before["skills"], (
            f"Skills differ after restore.\n"
            f"Before: {[s['name'] for s in before['skills']]}\n"
            f"After:  {[s['name'] for s in after['skills']]}"
        )
        assert after["vmcp"] == before["vmcp"], (
            f"VMCP servers differ after restore.\n"
            f"Before: {[v['name'] for v in before['vmcp']]}\n"
            f"After:  {[v['name'] for v in after['vmcp']]}"
        )
        assert after["vnfs"] == before["vnfs"], (
            f"VNFS servers differ after restore.\n"
            f"Before: {[v['name'] for v in before['vnfs']]}\n"
            f"After:  {[v['name'] for v in after['vnfs']]}"
        )
