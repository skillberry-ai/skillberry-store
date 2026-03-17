#!/usr/bin/env python3
"""
Ensure pip exists for the currently running Python interpreter.

Behavior:
- If pip is already available, exit 0.
- Otherwise download get-pip.py from bootstrap.pypa.io and execute it
  using this same Python interpreter.
- If that succeeds, exit 0.
- If anything fails, exit -1.

Notes:
- On Linux/POSIX, sys.exit(-1) is commonly observed by the shell as 255.
- This script requires outbound HTTPS access to bootstrap.pypa.io.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"


def pip_available() -> bool:
    """
    Check whether pip is available for the current interpreter.
    We test via 'python -m pip --version' to verify that the module is usable.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def download_get_pip(target_path: str) -> None:
    """
    Download get-pip.py to target_path.
    """
    with urllib.request.urlopen(GET_PIP_URL, timeout=60) as response:
        if getattr(response, "status", 200) != 200:
            raise RuntimeError(f"HTTP error while downloading get-pip.py: {response.status}")
        with open(target_path, "wb") as f:
            shutil.copyfileobj(response, f)


def bootstrap_pip() -> bool:
    """
    Download and execute get-pip.py using the current interpreter.
    Returns True on success, False otherwise.
    """
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="ensure-pip-")
        script_path = os.path.join(temp_dir, "get-pip.py")

        print(f"[INFO] Downloading {GET_PIP_URL}", file=sys.stderr)
        download_get_pip(script_path)

        print(f"[INFO] Running get-pip.py with {sys.executable}", file=sys.stderr)
        result = subprocess.run(
            [sys.executable, script_path],
            check=False,
        )

        if result.returncode != 0:
            print(
                f"[ERROR] get-pip.py failed with exit code {result.returncode}",
                file=sys.stderr,
            )
            return False

        return pip_available()

    except Exception as e:
        print(f"[ERROR] Failed to bootstrap pip: {e}", file=sys.stderr)
        return False

    finally:
        if temp_dir and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    if pip_available():
        print("[INFO] pip is already available.", file=sys.stderr)
        return 0

    print("[INFO] pip is not available. Attempting bootstrap via get-pip.py...", file=sys.stderr)

    if bootstrap_pip():
        print("[INFO] pip successfully installed.", file=sys.stderr)
        return 0

    print("[ERROR] Could not install pip.", file=sys.stderr)
    return -1


if __name__ == "__main__":
    sys.exit(main())
