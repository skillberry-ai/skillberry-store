"""UI Manager for starting and stopping the Vite preview server.

Serves the prebuilt static bundle produced by `make ui-build`. Dev-mode
Vite (with file watchers / HMR) is available separately via `make ui-dev`.
"""

import logging
import subprocess
import os
import signal
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class UIManager:
    """Manages the Vite preview (static bundle) server lifecycle."""

    def __init__(self, ui_dir: Optional[Path] = None, ui_port: int = 3000):
        """Initialize the UI manager.

        Args:
            ui_dir: Path to the UI directory. If None, uses default location.
            ui_port: Port for the UI server (default: 3000).
        """
        if ui_dir is None:
            # Default to src/skillberry_store/ui
            current_file = Path(__file__)
            self.ui_dir = current_file.parent.parent / "ui"
        else:
            self.ui_dir = ui_dir

        self.ui_port = ui_port
        self.process: Optional[subprocess.Popen] = None
        self._is_running = False

    def _dist_exists(self) -> bool:
        """Check whether the prebuilt Vite bundle is present."""
        return (self.ui_dir / "dist" / "index.html").exists()

    def start(self) -> bool:
        """Start the UI preview server.

        Returns:
            bool: True if started successfully, False otherwise.
        """
        if self._is_running:
            logger.warning("UI server is already running")
            return True

        if not self.ui_dir.exists():
            logger.error(f"UI directory not found: {self.ui_dir}")
            return False

        # The static bundle is produced by `make ui-build` before we get here.
        # We do not attempt to install deps or build from Python — that would
        # duplicate Make's job and hide missing-build errors behind long delays.
        if not self._dist_exists():
            logger.error(
                "UI bundle not found at %s. Run `make ui-build` (or `make run`) first.",
                self.ui_dir / "dist",
            )
            return False

        try:
            logger.info(f"Starting UI server on port {self.ui_port}...")

            # Serve the prebuilt bundle via `vite preview` — a static file
            # server (sirv) with no filesystem watchers, so it will not
            # exhaust inotify limits in Kind / other multi-pod environments.
            self.process = subprocess.Popen(
                [
                    "npx",
                    "vite",
                    "preview",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(self.ui_port),
                ],
                cwd=self.ui_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=(
                    os.name == "nt"
                ),  # Windows requires shell=True to resolve npx.cmd
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            # Give it a moment to start
            time.sleep(2)

            # Check if process is still running
            if self.process.poll() is None:
                self._is_running = True
                logger.info(
                    f"UI server started successfully on http://localhost:{self.ui_port}"
                )
                return True
            else:
                stdout, stderr = self.process.communicate()
                logger.error(f"UI server failed to start: {stderr}")
                return False

        except FileNotFoundError:
            logger.error("npm not found. Please install Node.js and npm")
            return False
        except Exception as e:
            logger.error(f"Error starting UI server: {e}")
            return False

    def stop(self) -> bool:
        """Stop the UI preview server.

        Returns:
            bool: True if stopped successfully, False otherwise.
        """
        if not self._is_running or self.process is None:
            logger.info("UI server is not running")
            return True

        try:
            logger.info("Stopping UI server...")

            if os.name != "nt":
                # Unix-like systems: kill the process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            else:
                # Windows: terminate the process
                self.process.terminate()

            # Wait for process to terminate
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("UI server did not stop gracefully, forcing...")
                if os.name != "nt":
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    self.process.kill()
                self.process.wait()

            self._is_running = False
            self.process = None
            logger.info("UI server stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Error stopping UI server: {e}")
            return False

    def is_running(self) -> bool:
        """Check if the UI server is running.

        Returns:
            bool: True if running, False otherwise.
        """
        if not self._is_running or self.process is None:
            return False

        # Check if process is still alive
        if self.process.poll() is not None:
            self._is_running = False
            return False

        return True

    def __del__(self):
        """Cleanup: stop the server when the object is destroyed."""
        if self._is_running:
            self.stop()
