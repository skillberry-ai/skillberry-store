import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Literal

import uvicorn

from pydantic_settings import BaseSettings
from pydantic import Field, model_validator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, RedirectResponse
from fastapi_mcp import FastApiMCP

from skillberry_store.fast_api.openapi_ids import custom_generate_unique_id
from skillberry_store.fast_api.skills_api import register_skills_api
from skillberry_store.fast_api.snippets_api import register_snippets_api
from skillberry_store.fast_api.tools_api import register_tools_api
from skillberry_store.fast_api.admin_api import register_admin_api
from skillberry_store.fast_api.vmcp_api import register_vmcp_api
from skillberry_store.fast_api.vnfs_api import register_vnfs_api
from skillberry_store.fast_api.plugins_api import register_plugins_api
from skillberry_store.fast_api.auth_api import register_auth_api
from skillberry_store.access_control.audit import (
    audit_rbac_coverage,
    stamp_rbac_markers,
)
from skillberry_store.access_control.config import get_config as get_acl_config
from skillberry_store.access_control.deps import make_enforce_dependency
from skillberry_store.access_control.sessions import SessionStore
from skillberry_store.tools.configure import (
    configure_logging,
)

try:
    from skillberry_store.fast_api.git_version import __git_version__
except:
    __git_version__ = "unknown"

from skillberry_store.fast_api.observability import observability_setup

# this environment variable is used to enable the latest API version
ENABLE_API_VERSION = os.environ.get("ENABLE_API_VERSION", "latest")

logger = logging.getLogger(__name__)


class SBSettings(BaseSettings):
    """Configuration settings for the SBS server."""

    sbs_host: str = Field("0.0.0.0", validation_alias="SBS_HOST")
    sbs_port: int = Field(8000, validation_alias="SBS_PORT")
    ui_port: int = Field(8002, validation_alias="SBS_UI_PORT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", validation_alias="UVICORN_LOG_LEVEL"
    )
    observability: bool = Field(True, validation_alias="OBSERVABILITY")
    sbs_vdb: str = Field("faiss", validation_alias="SBS_VDB")

    @property
    def display_host(self) -> str:
        """Return a browser-friendly host (0.0.0.0 is not browsable on Windows)."""
        return "localhost" if self.sbs_host == "0.0.0.0" else self.sbs_host


async def _warm_semantic_encoder() -> None:
    """Force the semantic encoder to initialize in a worker thread.

    Runs off the event loop so it does not stall concurrent request handling.
    Logs start/finish (with elapsed time) and swallows failures — a warmup miss
    just means the first real semantic query pays the cold-start cost, which is
    the pre-existing behavior.
    """
    logger.info("Semantic encoder warmup starting (background)")
    start = time.monotonic()
    try:
        loop = asyncio.get_running_loop()

        # Imported inside the executor call so the embedding-runtime import
        # itself is paid on the worker thread, not the event loop.
        def _warm_sync() -> None:
            from skillberry_store.vdbs.vector_db_interface import text_to_vector

            text_to_vector("warmup")

        await loop.run_in_executor(None, _warm_sync)
        elapsed = time.monotonic() - start
        logger.info(f"Semantic encoder warmup finished in {elapsed:.2f}s")
    except Exception:
        logger.exception("Semantic encoder warmup failed")


def _check_vector_db_backend() -> None:
    """Surface a misconfigured SBS_VDB in the boot log rather than on first search.

    Backend imports are on demand (chroma pulls onnxruntime/hnswlib, lancedb pulls
    pyarrow/pandas), so an unavailable backend previously failed at the first
    embedding call. This only logs: a deployment that starts today and serves its
    non-search endpoints must keep starting.
    """
    from skillberry_store.vdbs.identify_vdb import check_backend_available

    db_type = os.getenv("SBS_VDB", "faiss")
    problem = check_backend_available(db_type)
    if problem:
        logger.error("Vector DB backend check failed: %s", problem)
    else:
        logger.info("Vector DB backend %r is available", db_type)


@asynccontextmanager
async def _sbs_lifespan(app: FastAPI):
    """FastAPI lifespan hook — schedules background warmups without blocking startup."""
    # Fire-and-forget: create_task returns immediately, so lifespan yields to
    # uvicorn straight away and the server begins accepting connections. Keep a
    # reference on app.state so the task isn't garbage-collected mid-run.
    _check_vector_db_backend()
    app.state.encoder_warmup_task = asyncio.create_task(_warm_semantic_encoder())
    yield


def ui_dist_dir() -> Path:
    """Location of the pre-built UI bundle (``make ui-build`` / Dockerfile builder).

    A module-level function rather than an inline expression so tests can point
    the /ui mount at a synthetic bundle: `dist` is gitignored and no test target
    builds it, so on CI the directory never exists and every /ui route would
    otherwise be dead code (PR #308 review issue #7).
    """
    return Path(__file__).parent.parent / "ui" / "dist"


class SBS(FastAPI):
    def __init__(self, **settings: Any):
        """Initialize the SBS server with FastAPI and custom settings."""

        # Access-control is wired as a global FastAPI dependency and MUST be
        # loaded BEFORE super().__init__() so it lands on ``router.dependencies``
        # while the router is empty. FastAPI copies the router-level dependency
        # list into each route's dependant at ``add_api_route`` time — appending
        # later would silently miss every already-registered route. See
        # docs/design/access-control.md §8 for the wider design.
        acl_cfg = get_acl_config()
        sessions = SessionStore()
        acl_dependencies: List = []
        if acl_cfg.mode == "standalone":
            acl_dependencies = [Depends(make_enforce_dependency(acl_cfg, sessions))]
        elif acl_cfg.mode != "disabled":
            # Should have been rejected at config load; belt and braces.
            raise RuntimeError(f"Unsupported access-control mode: {acl_cfg.mode!r}")

        super().__init__(
            lifespan=_sbs_lifespan,
            generate_unique_id_function=custom_generate_unique_id,
            dependencies=acl_dependencies,
        )
        self.state.acl_cfg = acl_cfg
        self.state.acl_sessions = sessions
        self.settings = SBSettings(**settings)
        self.configure_fastapi()
        configure_logging(logging._nameToLevel[self.settings.log_level])
        self.logger = logging.getLogger(__name__)
        logger.info(f"SBSettings sbs_vdb = {self.settings.sbs_vdb}")

        # Load per-endpoint import auth config (import_auth_config.yaml /
        # SBS_IMPORT_AUTH_CONFIG). Logs the
        # path and endpoint count; harmless if no config file is present.
        from skillberry_store.tools.endpoint_auth import get_config

        get_config()

        # Initialize object handlers (singleton pattern). Descriptions are created
        # inside each ObjectHandler using SBS_VDB (defaults to "faiss").
        from skillberry_store.modules.object_handler import initialize_object_handlers

        initialize_object_handlers()
        logger.info("Object handlers initialized")

        # Initialize service layer (singletons in services.registry)
        from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager
        from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager
        from skillberry_store.services.registry import (
            initialize_services,
            get_service,
        )

        sts_url = f"http://{self.settings.sbs_host}:{self.settings.sbs_port}"

        initialize_services(
            vmcp_server_manager=VirtualMcpServerManager(sts_url=sts_url, app=self),
            vnfs_server_manager=VirtualNfsServerManager(sts_url=sts_url, app=self),
        )
        tools_service = get_service("tool")
        skills_service = get_service("skill")
        snippets_service = get_service("snippet")
        vnfs_service = get_service("vnfs")
        vmcp_service = get_service("vmcp")

        from skillberry_store.services.admin_service import AdminService

        admin_service = AdminService(
            vmcp_server_manager=vmcp_service.server_manager,
            vnfs_server_manager=vnfs_service.server_manager,
        )

        # Initialize plugin system
        from skillberry_store.plugins.loader import PluginLoader
        from skillberry_store.plugins.store_api import StoreAPI

        store_api = StoreAPI(
            {
                "tools": tools_service,
                "skills": skills_service,
                "snippets": snippets_service,
                "vnfs": vnfs_service,
                "vmcp": vmcp_service,
            }
        )

        plugin_loader = PluginLoader(store_api=store_api)
        discovered = plugin_loader.discover_plugins()
        logger.info(f"Discovered {len(discovered)} plugins: {discovered}")

        self.state.plugin_loader = plugin_loader

        register_vmcp_api(
            self,
            tags="vmcp_servers",
            service=vmcp_service,
        )
        register_vnfs_api(
            self,
            tags="vnfs_servers",
            service=vnfs_service,
        )
        register_skills_api(
            self,
            tags="skills",
            service=skills_service,
        )
        register_snippets_api(
            self,
            tags="snippets",
            service=snippets_service,
        )
        register_tools_api(
            self,
            tags="tools",
            service=tools_service,
        )
        register_admin_api(self, tags="admin", service=admin_service)

        register_plugins_api(self, plugin_loader=plugin_loader, tags="plugins")

        # ------------------------------------------------------------------
        # Access control (see docs/design/access-control.md).
        # /auth/* endpoints are always registered. The PEP itself is a
        # global FastAPI dependency installed on the router before this
        # point (see the top of __init__); in 'disabled' mode no dep is
        # installed and the OpenAPI schema publishes no security scheme.
        # ------------------------------------------------------------------
        register_auth_api(self, cfg=acl_cfg, sessions=sessions, tags="auth")
        if acl_cfg.mode == "disabled":
            logger.info("Access control mode=disabled — PEP dependency not installed")
        else:
            logger.info(
                "Access control mode=%s — PEP dependency installed "
                "(%d users, %d roles, %d bindings)",
                acl_cfg.mode,
                len(acl_cfg.users),
                len(acl_cfg.roles),
                len(acl_cfg.bindings),
            )

        # Mount plugin routers
        plugin_loader.mount_routers(self)
        logger.info("Plugin routers mounted")

        # ------------------------------------------------------------------
        # RBAC marker stamping + coverage audit (r13). Every non-allowlisted
        # APIRoute must declare (resource, verb) via @requires — the audit
        # fails startup with a listing of any offenders. Runs in all modes
        # so that missing markers are caught in tests / dev, not only when
        # standalone mode is switched on.
        # ------------------------------------------------------------------
        stamped = stamp_rbac_markers(self)
        logger.info("RBAC markers stamped on %d route(s)", stamped)
        audit_rbac_coverage(self, acl_cfg)

        # Mount the Control MCP with a CURATED surface. The store auto-generates an
        # MCP tool per REST endpoint, but agents only need the content operations,
        # and many endpoints either don't belong on the agent surface (health,
        # readiness, metrics, admin backup/restore/purge, change polling, provenance)
        # or can't be MCP tools at all (file-upload endpoints — an MCP call has no
        # file body). Rather than maintaining a separate allow-list that drifts as
        # endpoints come and go, each endpoint opts in where it is declared via
        # ``openapi_extra={"x-mcp-tool": True}`` (alongside the existing
        # ``x-cli-name``). We derive the allow-list from those markers here.
        mcp_included_operations = self._mcp_included_operations()
        logger.info(
            "Exposing %d operations on the Control MCP: %s",
            len(mcp_included_operations),
            ", ".join(sorted(mcp_included_operations)),
        )

        # In `disabled` mode there is no notion of a tenant, so we mount a
        # single MCP at /control_sse with the full curated surface — same
        # as before. In `standalone` mode we additionally mount one MCP
        # per configured user at /control_sse/<username>, each with its
        # ``include_operations`` restricted to what that user is
        # authorized to invoke under RBAC. Middleware still enforces on
        # each tool call — the per-user surface just prevents denied
        # tools from appearing in the client's tool list.
        if acl_cfg.mode == "disabled":
            mcp_server = FastApiMCP(self, include_operations=mcp_included_operations)
            mcp_server.mount_sse(mount_path="/control_sse")
        else:
            from skillberry_store.access_control.mcp_plan import operations_for_user

            self._mcp_per_user_mounts: List[str] = []
            for user in acl_cfg.users:
                allowed_full = set(operations_for_user(self, user, acl_cfg))
                allowed = sorted(allowed_full & set(mcp_included_operations))
                mount_path = f"/control_sse/{user.username}"
                user_mcp = FastApiMCP(self, include_operations=allowed)
                user_mcp.mount_sse(mount_path=mount_path)
                self._mcp_per_user_mounts.append(mount_path)
                logger.info(
                    "Mounted per-tenant MCP for '%s' at %s exposing %d ops: %s",
                    user.username,
                    mount_path,
                    len(allowed),
                    ", ".join(allowed) if allowed else "(none)",
                )

    def _mcp_included_operations(self) -> List[str]:
        """Operation ids opted in to the Control MCP via ``x-mcp-tool``.

        Reads the generated OpenAPI schema (the same source ``FastApiMCP``
        consumes) so the Control MCP surface stays in sync with the endpoints
        automatically — there is no list to maintain in parallel.
        """
        return mcp_operations_from_openapi(self.openapi())

    def configure_fastapi(self):
        """Configures CORS middleware and OpenAPI documentation settings."""
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.openapi = lambda: custom_openapi(self, [])

        # Add observability for FastAPI application
        if int(os.getenv("OTEL_TRACES_PORT", 0)) > 0:
            # Imported inside the guard rather than at module scope: a
            # deployment without tracing never touches this instrumentation
            # stack. See the companion note in observability.otel_setup.
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(self)

        # Serve the pre-built UI bundle from this process. This replaces the
        # `npx vite preview` subprocess (UIManager) that used to run alongside
        # the server, saving ~50–100 MiB of RSS.
        #
        # The bundle is produced at build time by `make ui-build` (or by
        # the Dockerfile builder stage). If it is absent (e.g., a bare dev
        # checkout), the /ui mount is simply skipped — the API still starts
        # normally, and `make ui-dev` / `make ui-build && make run` work
        # as before.
        ui_dist = ui_dist_dir()
        if ui_dist.exists():
            # Catch-all for /ui: this one route serves both real static files
            # (JS/CSS/fonts) and, for anything else, index.html so React Router
            # can handle the route client-side.
            #
            # There is deliberately no StaticFiles mount. A previous version
            # mounted one and justified the ordering with "Starlette evaluates
            # mounts before APIRoutes" — it does not: `Router.__call__` walks
            # routes in registration order with no Mount precedence. Since this
            # `{path:path}` route was registered first it matched everything
            # under /ui, leaving the mount reachable only for the bare `/ui` ->
            # `/ui/` redirect, which is now an explicit route below. Starlette's
            # FileResponse handles Range requests itself (it sets accept-ranges
            # and parses Range/If-Range), so serving from here rather than from
            # StaticFiles costs no byte-range support.
            #
            # Vite emits content-hashed asset filenames, so a rebuild always
            # produces new names -- those are safe to cache forever. index.html
            # is the entry point and is NOT hashed: served without a
            # Cache-Control header it only carries ETag/Last-Modified, and
            # browsers then apply heuristic freshness and reuse it without
            # revalidating. The stale HTML points at the previous build's asset
            # names (also cached), so the whole old bundle boots with zero
            # network traffic and no rebuild ever reaches the user.
            _ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
            _INDEX_CACHE_CONTROL = "no-cache, must-revalidate"
            ui_root = ui_dist.resolve()

            # GET *and* HEAD: FastAPI's @app.get registers GET only (unlike
            # Starlette's plain Route, which implies HEAD), so a HEAD would
            # otherwise 405 instead of answering with the cache directives set
            # here.
            @self.api_route(
                "/ui/{path:path}", methods=["GET", "HEAD"], include_in_schema=False
            )
            async def _ui_spa_fallback(path: str):
                # Real static assets (JS, CSS, fonts, images) are served from
                # disk. Anything else falls back to index.html so React Router
                # can handle the route client-side (/ui/skills, /ui/tools/:uuid).
                asset = (ui_root / path).resolve()
                # Unlike StaticFiles, this handler joins a client-supplied path
                # onto the bundle directory, so it has to reject traversal out
                # of it (e.g. GET /ui/../../../etc/passwd from a raw client).
                if asset.is_relative_to(ui_root) and asset.is_file():
                    # Only content-hashed assets may be cached immutably. HTML
                    # is never hashed by Vite, so `GET /ui/index.html` — the
                    # entry point requested by its real name, which is what a
                    # bookmark, a doc link or an ingress rewriting /ui/ ->
                    # /ui/index.html sends — must get the no-cache directive
                    # instead. Matching on the suffix rather than on the exact
                    # name also covers any additional HTML entry point.
                    cache_control = (
                        _INDEX_CACHE_CONTROL
                        if asset.suffix == ".html"
                        else _ASSET_CACHE_CONTROL
                    )
                    return FileResponse(asset, headers={"Cache-Control": cache_control})
                return FileResponse(
                    ui_root / "index.html",
                    headers={"Cache-Control": _INDEX_CACHE_CONTROL},
                )

            # The `{path:path}` route above needs the trailing slash, so the bare
            # prefix gets its own redirect. This used to be the only thing the
            # StaticFiles mount still handled.
            @self.api_route(
                "/ui", methods=["GET", "HEAD"], include_in_schema=False
            )
            async def _ui_prefix_redirect():
                return RedirectResponse(url="/ui/")

            logger.info("UI bundle served at /ui from %s", ui_dist)

            @self.get("/", include_in_schema=False)
            async def _root_redirect():
                return RedirectResponse(url="/ui/")

        else:
            logger.warning(
                "UI bundle not found at %s — /ui not mounted. "
                "Run `make ui-build` to build it.",
                ui_dist,
            )

    def run(self):
        """Starts the FastAPI app using Uvicorn."""
        self.logger.info("Starting SBS server")
        self.logger.info(
            f"API server running at: http://{self.settings.display_host}:{self.settings.sbs_port}"
        )
        # self.logger.info(f"UI available at: http://localhost:{self.settings.ui_port}")
        self.logger.info(
            f"API documentation at: http://{self.settings.display_host}:{self.settings.sbs_port}/docs"
        )

        if self.settings.observability:
            observability_setup()

        # Configure uvicorn logging - create custom config to ensure all requests are logged
        import copy
        from uvicorn.config import LOGGING_CONFIG

        log_config = copy.deepcopy(LOGGING_CONFIG)
        log_config["formatters"]["access"][
            "fmt"
        ] = '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
        log_config["loggers"]["uvicorn.access"][
            "level"
        ] = "DEBUG"  # Ensure all access logs are shown

        uvicorn.run(
            self,
            host=self.settings.sbs_host,
            port=self.settings.sbs_port,
            access_log=True,
            log_config=log_config,
        )


def mcp_operations_from_openapi(openapi_schema: dict) -> List[str]:
    """Collect ``operationId``s opted in to the Control MCP via ``x-mcp-tool``.

    An endpoint joins the Control MCP surface by declaring
    ``openapi_extra={"x-mcp-tool": True}`` (next to the existing ``x-cli-name``).
    FastAPI merges ``openapi_extra`` into each operation object, so the marker
    and the ``operationId`` both live in the generated schema — the same schema
    ``FastApiMCP`` consumes. Deriving the allow-list from there keeps the CLI and
    Control MCP aligned and avoids maintaining a parallel list that drifts.
    """
    operations: List[str] = []
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            if operation.get("x-mcp-tool") and operation.get("operationId"):
                operations.append(operation["operationId"])
    return operations


def custom_openapi(app: FastAPI, openapi_tags):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="skillberry",
        summary="Towards hallucination-less AI systems",
        version=__git_version__,
        tags=openapi_tags,
        contact={
            "name": "Eran Raichstein",
            "email": "eranra@il.ibm.com",
        },
        routes=app.routes,
    )

    # Strip the auto-derived ``security`` requirement from routes that the
    # ACL config marks as unauthenticated (``/auth/*``, ``/health*``,
    # ``/admin/metrics``, …). The router-level ``Depends(enforce)`` puts
    # ``security: [{HTTPBearer: []}]`` on every operation via the
    # ``HTTPBearer`` scheme in its param signature. That's correct as a
    # default, but misleading for endpoints the enforce dep short-circuits
    # — the OpenAPI schema is the same source Swagger UI / SDK generators
    # consume, so lock icons there should track what the server actually
    # requires. We remove ``security`` in place rather than layering an
    # ``openapi_extra={"security": []}`` override because FastAPI's
    # ``deep_dict_update`` concatenates lists (empty list is a no-op).
    acl_cfg = getattr(getattr(app, "state", None), "acl_cfg", None)
    if acl_cfg is not None and openapi_schema.get("paths"):
        _METHOD_KEYS = {
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "options",
            "head",
            "trace",
        }
        for path, path_item in openapi_schema["paths"].items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in list(path_item.items()):
                if method not in _METHOD_KEYS or not isinstance(operation, dict):
                    continue
                if acl_cfg.is_unauthenticated(method, path):
                    operation.pop("security", None)

    # Fix file upload schema for SDK generation
    # FastAPI generates contentMediaType but OpenAPI generators expect format: binary
    if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
        schemas = openapi_schema["components"]["schemas"]

        # Define all file upload endpoints and their file parameter names.
        # Body-schema names track the route ``operationId`` — with
        # ``custom_generate_unique_id`` in effect the ID is the route function
        # name, so these are ``Body_<function_name>``.
        file_upload_fixes = [
            ("Body_add_tool_from_python", "tool"),
            ("Body_create_tool", "module"),
            ("Body_create_snippet", "file"),
            ("Body_import_anthropic_skill", "zip_file"),
            ("Body_restore_all_data", "backup_file"),
        ]

        # Apply fix to all file upload schemas
        for schema_name, file_param in file_upload_fixes:
            if schema_name in schemas:
                schema = schemas[schema_name]
                if "properties" in schema and file_param in schema["properties"]:
                    file_prop = schema["properties"][file_param]
                    # Remove contentMediaType and add format: binary
                    if "contentMediaType" in file_prop:
                        del file_prop["contentMediaType"]
                    file_prop["format"] = "binary"

    app.openapi_schema = openapi_schema
    return app.openapi_schema
