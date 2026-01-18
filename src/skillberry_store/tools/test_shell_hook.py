import os
import subprocess
from unittest import mock

import pytest

from skillberry_store.tools.shell_hook import ShellHook


@pytest.fixture
def shell_hook():
    return ShellHook()


def test_get_command_template_exists(shell_hook):
    with mock.patch.dict(os.environ, {"SBS_TEST_COMMAND": "echo hello {name}"}):
        template = shell_hook.get_command_template("test")
        assert template == "echo hello {name}"


def test_get_command_template_missing(shell_hook):
    with mock.patch.dict(os.environ, {}, clear=True):
        template = shell_hook.get_command_template("nonexistent")
        assert template is None


def test_execute_success(shell_hook):
    with mock.patch.dict(os.environ, {"SBS_TEST_COMMAND": "echo Hello {name}"}):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["echo", "Hello world"],
                returncode=0,
                stdout="Hello world\n",
                stderr="",
            )
            shell_hook.execute("test", name="world")

            mock_run.assert_called_once()
            assert "Hello world" in mock_run.return_value.stdout


def test_execute_command_failure(shell_hook):
    with mock.patch.dict(os.environ, {"SBS_FAIL_COMMAND": "false"}):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1, cmd="false", output="", stderr="Simulated failure"
            )
            shell_hook.execute("fail")
            mock_run.assert_called_once()
