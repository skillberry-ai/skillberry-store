"""UI Manager for starting and stopping the Vite development server."""

import logging
import subprocess
import os
import signal
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class UIManager:
    """Manages the Vite UI development server lifecycle."""

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

    def _check_node_modules(self) -> bool:
        """Check if node_modules exists."""
        node_modules = self.ui_dir / "node_modules"
        return node_modules.exists()

    def _install_dependencies(self) -> bool:
        """Install npm dependencies if needed."""
        if self._check_node_modules():
            logger.info("UI dependencies already installed")
            return True

        logger.info("Installing UI dependencies...")
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=self.ui_dir,
                capture_output=True,
                text=True,
                shell=(
                    os.name == "nt"
                ),  # Windows requires shell=True to resolve npm.cmd
                timeout=300,  # 5 minutes timeout
            )
            if result.returncode == 0:
                logger.info("UI dependencies installed successfully")
                return True
            else:
                logger.error(f"Failed to install UI dependencies: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("UI dependency installation timed out")
            return False
        except Exception as e:
            logger.error(f"Error installing UI dependencies: {e}")
            return False

    def start(self) -> bool:
        """Start the UI development server.

        Returns:
            bool: True if started successfully, False otherwise.
        """
        if self._is_running:
            logger.warning("UI server is already running")
            return True

        if not self.ui_dir.exists():
            logger.error(f"UI directory not found: {self.ui_dir}")
            return False

        # Check and install dependencies if needed
        if not self._install_dependencies():
            logger.error("Cannot start UI server without dependencies")
            return False

        try:
            logger.info(f"Starting UI server on port {self.ui_port}...")

            # Start the Vite dev server using npx to ensure vite is found
            self.process = subprocess.Popen(
                ["npx", "vite", "--host", "0.0.0.0", "--port", str(self.ui_port)],
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
        """Stop the UI development server.

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
