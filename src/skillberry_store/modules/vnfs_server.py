"""Virtual NFS server implementation with pluggable filesystem backends."""

import logging
import os
import shutil
import socket
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FilesystemServerBackend(ABC):
    """Abstract backend for serving a directory as a network filesystem."""

    @abstractmethod
    def start(self, export_path: str, port: int) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...


class ShenanigaNFSBackend(FilesystemServerBackend):
    """User-space NFSv3 via ShenanigaNFS. No root required."""

    def __init__(self):
        self._thread = None
        self._loop = None

    def start(self, export_path: str, port: int) -> None:
        import asyncio
        import math
        import secrets
        import threading

        try:
            from shenaniganfs.fs import (
                SimpleFS,
                SimpleDirectory,
                SimpleFile,
                VerifyingFileHandleEncoder,
            )
            from shenaniganfs.fs_manager import FileSystemManager
            from shenaniganfs.nfs3 import MountV3Service, NFSV3Service
            from shenaniganfs.server import TCPTransportServer
        except ImportError as exc:
            raise RuntimeError(
                "ShenanigaNFS is not installed. "
                "Add 'git+https://github.com/JordanMilne/ShenanigaNFS.git#egg=shenanigaNFS' "
                "to your dependencies."
            ) from exc

        class PathFS(SimpleFS):
            """Read-only in-memory snapshot of a local directory."""

            def __init__(self, path: str):
                super().__init__()
                self.read_only = True
                self.track_entry(SimpleDirectory(mode=0o0555, name=b"", root_dir=True))
                self._populate(Path(path), self.root_dir)
                self.sanity_check()

            def _populate(self, dir_path: Path, parent: SimpleDirectory) -> None:
                for item in sorted(dir_path.iterdir(), key=lambda p: p.name):
                    if item.is_symlink():
                        continue
                    if item.is_dir():
                        entry = SimpleDirectory(
                            mode=0o0555, name=item.name.encode("utf-8")
                        )
                        parent.link_child(entry)
                        self._populate(item, entry)
                    elif item.is_file():
                        data = item.read_bytes()
                        entry = SimpleFile(
                            name=item.name.encode("utf-8"),
                            mode=0o0444,
                            contents=bytearray(data),
                            blocks=max(1, math.ceil(len(data) / self.block_size)),
                        )
                        parent.link_child(entry)

        handle_encoder = VerifyingFileHandleEncoder(hmac_secret=secrets.token_bytes(16))
        fs_manager = FileSystemManager(
            handle_encoder=handle_encoder,
            factories={b"/": lambda ctx: PathFS(export_path)},
        )

        transport_server = TCPTransportServer("0.0.0.0", port)
        transport_server.register_prog(MountV3Service(fs_manager))
        transport_server.register_prog(NFSV3Service(fs_manager))

        self._loop = asyncio.new_event_loop()

        async def _serve():
            server = await transport_server.start()
            async with server:
                await server.serve_forever()

        def _run():
            self._loop.run_until_complete(_serve())

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        logger.info(
            f"ShenanigaNFS backend started on port {port}, serving {export_path}"
        )

    def stop(self) -> None:
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        logger.info("ShenanigaNFS backend stopped")


class WebDavBackend(FilesystemServerBackend):
    """WebDAV via wsgidav. Serves export_path as a read-only static file tree."""

    def __init__(self):
        self._server = None
        self._thread = None

    def start(self, export_path: str, port: int) -> None:
        import threading

        try:
            from wsgidav.wsgidav_app import WsgiDAVApp
            from wsgidav.fs_dav_provider import FilesystemProvider
            from cheroot import wsgi as cheroot_wsgi
        except ImportError as exc:
            raise RuntimeError(
                "wsgidav / cheroot is not installed. "
                "Add 'wsgidav>=4.3' to your dependencies."
            ) from exc

        config = {
            "host": "0.0.0.0",
            "port": port,
            "provider_mapping": {"/": FilesystemProvider(export_path, readonly=True)},
            "simple_dc": {"user_mapping": {"*": True}},
            "verbose": 0,
        }
        app = WsgiDAVApp(config)
        server_args = {
            "bind_addr": ("0.0.0.0", port),
            "wsgi_app": app,
        }
        self._server = cheroot_wsgi.Server(**server_args)

        def _run():
            self._server.start()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        logger.info(f"WebDAV backend started on port {port}, serving {export_path}")

    def stop(self) -> None:
        if self._server:
            try:
                self._server.stop()
            except Exception as exc:
                logger.warning(f"Error stopping WebDAV server: {exc}")
        logger.info("WebDAV backend stopped")


class VirtualNfsServer:
    """Represents a virtual NFS endpoint that serves a skill as a filesystem."""

    def __init__(
        self,
        name: str,
        skill_uuid: Optional[str],
        port: Optional[int],
        protocol: str = "webdav",
        description: str = "",
        uuid: Optional[str] = None,
    ):
        self.name = name
        self.skill_uuid = skill_uuid
        self.description = description
        self.protocol = protocol
        self.uuid = uuid or name

        if port is None:
            self.port = self._find_available_port()
        else:
            if not self._is_port_available(port):
                raise ValueError(f"Port {port} is not available")
            self.port = port

        self.export_path = Path(tempfile.mkdtemp(prefix=f"vnfs_{self.uuid}_"))
        self.backend: FilesystemServerBackend = (
            ShenanigaNFSBackend() if protocol == "nfs" else WebDavBackend()
        )
        self.running = False

    # ------------------------------------------------------------------
    # Port helpers (same logic as VirtualMcpServer)
    # ------------------------------------------------------------------

    def _is_port_available(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return True
            except socket.error:
                return False

    def _find_available_port(self, start_port: Optional[int] = None) -> int:
        if start_port is None:
            start_port = int(os.environ.get("VNFS_SERVERS_START_PORT", 11000))
        port = start_port
        while not self._is_port_available(port):
            port += 1
        return port

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(
        self,
        skill: Dict,
        tools: List[Dict],
        snippets: List[Dict],
        tool_modules: Optional[Dict[str, str]] = None,
    ) -> None:
        """Generate files then start the backend server."""
        from skillberry_store.tools.anthropic.exporter import export_skill_to_directory

        export_skill_to_directory(
            skill, tools, snippets, str(self.export_path), tool_modules
        )
        self.backend.start(str(self.export_path), self.port)
        self.running = True
        logger.info(
            f"VirtualNfsServer '{self.name}' started on port {self.port} "
            f"({self.protocol}), export_path={self.export_path}"
        )

    def stop(self) -> None:
        """Stop backend and clean up temp directory."""
        try:
            self.backend.stop()
        except Exception as exc:
            logger.warning(f"Error stopping backend for '{self.name}': {exc}")
        shutil.rmtree(self.export_path, ignore_errors=True)
        self.running = False
        logger.info(f"VirtualNfsServer '{self.name}' stopped")

    def refresh(
        self,
        skill: Dict,
        tools: List[Dict],
        snippets: List[Dict],
        tool_modules: Optional[Dict[str, str]] = None,
    ) -> None:
        """Regenerate files from updated skill without restarting the server."""
        from skillberry_store.tools.anthropic.exporter import export_skill_to_directory

        export_skill_to_directory(
            skill, tools, snippets, str(self.export_path), tool_modules
        )
        logger.info(f"VirtualNfsServer '{self.name}' files refreshed")

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "skill_uuid": self.skill_uuid,
            "port": self.port,
            "protocol": self.protocol,
            "description": self.description,
            "running": self.running,
            "export_path": str(self.export_path),
        }
