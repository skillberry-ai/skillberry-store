# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Reproduces and guards the ci-push `.stamps/ssh-agent.env` failure.

Background (PR #308 review, issue #6): every push run died at
``.stamps/ssh-agent.env`` with ``Error 1`` before ``docker-build`` ever ran, so
the registry ``:latest`` never flipped to the core-only image (and issue #4 stayed
masked). From run 32854430424 the agent starts fine ("Starting SSH agent" /
"Agent pid 10184") and the step then fails with no diagnostic at all: the recipe
runs ``ssh-add $(SSH_KEY)`` where ``SSH_KEY ?= ~/.ssh/id_rsa 2>/dev/null``, a
GitHub runner has no ``~/.ssh/id_rsa``, and the redirect baked into the variable
swallows the error message.

Adding a key is therefore best-effort now. Docker still receives the agent socket
via ``--ssh default=$SSH_AUTH_SOCK``; a keyless agent simply resolves no private
git dependency. Conversely a *failed* ``ssh-agent`` must now fail loudly: the
shell redirect creates the stamp either way, and an empty stamp would be treated
as up to date forever while buildx silently got ``--ssh default=``.

The tests execute the makefile's real recipe body in an isolated HOME rather than
asserting on the text of the recipe.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GLOBALS_MK = REPO_ROOT / "skillberry-common" / ".mk" / "globals.mk"
STAMP_TARGET = ".stamps/ssh-agent.env"

pytestmark = pytest.mark.skipif(
    shutil.which("ssh-agent") is None or shutil.which("ssh-add") is None,
    reason="ssh-agent/ssh-add are not available on this host",
)


def _make_variable(name: str) -> str:
    """Value of a `NAME ?= value` / `NAME := value` assignment in globals.mk."""
    match = re.search(
        rf"^{re.escape(name)}\s*[?:]?=\s*(.*)$", GLOBALS_MK.read_text(), re.MULTILINE
    )
    assert match, f"{name} is not assigned in {GLOBALS_MK.name}"
    return match.group(1).strip()


def _stamp_recipe_as_shell() -> str:
    """The recipe of the .stamps/ssh-agent.env rule, as a runnable shell script."""
    text = GLOBALS_MK.read_text()
    match = re.search(
        rf"^{re.escape(STAMP_TARGET)}:.*?\n((?:\t.*\n)+)", text, re.MULTILINE
    )
    assert match, f"no recipe found for {STAMP_TARGET} in {GLOBALS_MK.name}"

    # Strip make's leading tab and the per-line `@` (echo-suppressing) prefix.
    lines = [line[1:] for line in match.group(1).splitlines()]
    lines = [line[1:] if line.startswith("@") else line for line in lines]
    script = "\n".join(lines)
    # Make -> shell: $$VAR is a shell variable, $(SSH_KEY) is a make variable.
    script = script.replace("$(SSH_KEY)", _make_variable("SSH_KEY"))
    script = script.replace("$$", "$")
    assert "$(" not in script, f"unexpanded make variable in recipe:\n{script}"
    return script


@pytest.fixture
def agent_sandbox():
    """A short-pathed HOME + work dir, and cleanup of any agent left running.

    Deliberately *not* pytest's `tmp_path`: agent socket paths must fit in
    `sockaddr_un.sun_path` (108 bytes), and tmp_path's per-test directory names
    are long enough to push ssh-agent over that limit — which fails the agent
    for a reason that has nothing to do with what is under test.
    """
    root = Path(tempfile.mkdtemp(prefix="sbs-ssh-"))
    home = root / "h"
    (home / ".ssh").mkdir(parents=True)  # present but empty, like a fresh runner
    work = root / "w"
    (work / ".stamps").mkdir(parents=True)
    try:
        yield home, work
    finally:
        stamp = work / STAMP_TARGET
        if stamp.is_file():
            # `ssh-agent -s` daemonises; don't leak it out of the test session.
            pid = re.search(r"SSH_AGENT_PID=(\d+)", stamp.read_text())
            if pid:
                try:
                    os.kill(int(pid.group(1)), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
        shutil.rmtree(root, ignore_errors=True)


def _run_recipe(home: Path, work: Path, **env_overrides) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "SSH_AUTH_SOCK"}
    env["HOME"] = str(home)
    env.update(env_overrides)
    return subprocess.run(
        ["bash", "-c", _stamp_recipe_as_shell()],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_ssh_agent_stamp_succeeds_without_an_ssh_key(agent_sandbox):
    """The CI shape: no agent in the environment and no key on disk."""
    home, work = agent_sandbox

    proc = _run_recipe(home, work)

    assert proc.returncode == 0, (
        "the ssh-agent.env step fails when no SSH key is present, which is how "
        f"every ci-push run died before docker-build:\nstdout: {proc.stdout}\n"
        f"stderr: {proc.stderr}"
    )
    stamp = work / STAMP_TARGET
    assert stamp.is_file(), "the recipe did not write the stamp file"
    assert "SSH_AUTH_SOCK" in stamp.read_text(), (
        "the stamp must export SSH_AUTH_SOCK — docker-build sources it for "
        "`--ssh default=$SSH_AUTH_SOCK`"
    )


def test_ssh_agent_stamp_reuses_an_agent_already_in_the_environment(agent_sandbox):
    """With SSH_AUTH_SOCK set, the recipe captures it instead of starting an agent."""
    home, work = agent_sandbox
    sock = str(home / "not-a-real-agent.sock")

    proc = _run_recipe(home, work, SSH_AUTH_SOCK=sock)

    assert proc.returncode == 0, (
        "a dead or keyless inherited agent must not fail the build:\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert sock in (work / STAMP_TARGET).read_text()


def test_unusable_stamp_fails_loudly_and_is_removed(agent_sandbox):
    """A failed agent must not leave a stamp make would trust forever.

    The shell redirect creates the file even when ssh-agent cannot start, so
    without the guard `docker-build` sources an empty file and hands buildx
    `--ssh default=` on every subsequent run.
    """
    home, work = agent_sandbox
    # An ssh-agent that "starts" successfully but prints nothing.
    fake_bin = work / "bin"
    fake_bin.mkdir()
    fake_agent = fake_bin / "ssh-agent"
    fake_agent.write_text("#!/bin/sh\nexit 0\n")
    fake_agent.chmod(0o755)

    proc = _run_recipe(home, work, PATH=f"{fake_bin}:{os.environ['PATH']}")

    assert proc.returncode != 0, (
        "an empty ssh-agent.env must fail the step, not be treated as usable:\n"
        f"stdout: {proc.stdout}"
    )
    assert not (work / STAMP_TARGET).exists(), (
        "the unusable stamp must be removed so the next `make` retries instead "
        "of considering the target up to date"
    )
