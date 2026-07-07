"""Integration test — install kagenti-approver via the SBS API, expect APPROVED_TAG.

Uses the shared root ``run_sbs`` fixture (no auto-install) and drives
``POST /plugins/kagenti-approver/install?autostart=true`` itself, then creates
a skill whose tag list qualifies for kagenti-approved and waits for the
plugin subprocess to add ``APPROVED_TAG``.

This test is skipped when the ``SBS_RUN_INTEGRATION_PLUGIN`` env var is not
set to ``1`` — installing a per-plugin venv and pip-installing the SDK
takes tens of seconds. CI is expected to opt in.
"""

import asyncio
import os
import time

import httpx
import pytest

from skillberry_plugin_kagenti_approver.plugin import APPROVED_TAG

pytestmark = pytest.mark.skipif(
    os.environ.get("SBS_RUN_INTEGRATION_PLUGIN") != "1",
    reason="Set SBS_RUN_INTEGRATION_PLUGIN=1 to run subprocess integration test.",
)

BASE_URL = "http://localhost:8000"


async def _wait_for_state(slug: str, state: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            r = await client.get(f"{BASE_URL}/plugins/{slug}")
            if r.status_code == 200:
                data = r.json()
                if data.get("state") == state:
                    return
            await asyncio.sleep(0.5)
    raise AssertionError(f"plugin {slug} did not reach state={state} within {timeout}s")


async def _wait_for_tag(uuid: str, tag: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            r = await client.get(f"{BASE_URL}/skills/{uuid}")
            if r.status_code == 200 and tag in (r.json().get("tags") or []):
                return
            await asyncio.sleep(0.25)
    raise AssertionError(f"tag {tag} did not appear on skill {uuid} within {timeout}s")


@pytest.mark.asyncio
async def test_kagenti_approver_end_to_end(run_sbs):
    async with httpx.AsyncClient() as client:
        # Install (autostart=True). Idempotency: if already installed by a
        # previous session, uninstall first.
        r = await client.get(f"{BASE_URL}/plugins/kagenti-approver")
        if r.status_code == 200 and r.json().get("state") in ("installed", "running"):
            await client.delete(f"{BASE_URL}/plugins/kagenti-approver")

        r = await client.post(
            f"{BASE_URL}/plugins/kagenti-approver/install?autostart=true"
        )
        assert r.status_code in (200, 201), r.text

    await _wait_for_state("kagenti-approver", "running", timeout=60)

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}/skills/",
            json={
                "name": "kagenti-approver-integration-skill",
                "description": "test skill",
                "tags": ["security-score:9"],
            },
        )
        assert r.status_code in (200, 201), r.text
        skill = r.json()
        uuid = skill.get("uuid") or skill.get("id")
        assert uuid, r.text

    await _wait_for_tag(uuid, APPROVED_TAG, timeout=15)
