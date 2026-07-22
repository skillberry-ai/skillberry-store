"""Admin API endpoints for the Skillberry Store service."""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import PlainTextResponse, StreamingResponse

from skillberry_store.services.admin_service import AdminService

logger = logging.getLogger(__name__)


def register_admin_api(
    app: FastAPI,
    tags: str = "admin",
    service: Optional[AdminService] = None,
):
    """Register admin API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
        service: Optional AdminService instance.  When ``None``, a new instance
            is created using the server managers stored in ``app.state``.
    """
    if service is None:
        vmcp_manager = getattr(getattr(app, "state", None), "vmcp_server_manager", None)
        vnfs_manager = getattr(getattr(app, "state", None), "vnfs_server_manager", None)
        service = AdminService(
            vmcp_server_manager=vmcp_manager,
            vnfs_server_manager=vnfs_manager,
        )

    @app.get(
        "/admin/metrics",
        tags=[tags],
        response_class=PlainTextResponse,
        openapi_extra={"x-cli-name": "metrics"},
    )
    async def get_metrics():
        """Proxy endpoint to fetch Prometheus metrics.

        This endpoint proxies requests to the Prometheus metrics server
        to avoid CORS issues when accessing metrics from the UI.

        Returns:
            PlainTextResponse: The raw Prometheus metrics in text format.

        Raises:
            HTTPException: If metrics server is not accessible (503).
        """
        text = await service.get_metrics()
        return PlainTextResponse(content=text, media_type="text/plain")

    @app.delete(
        "/admin/purge-all", tags=[tags], openapi_extra={"x-cli-name": "purge-all"}
    )
    async def purge_all_data():
        """Delete all backend components including skills, tools, snippets, VMCP servers, and their descriptions.

        This endpoint performs a hard delete by:
        1. Stopping all running VMCP servers
        2. Clearing VMCP servers persistent storage
        3. Removing all data directories
        4. Recreating empty directories
        5. Resetting in-memory vector indexes

        Use with caution as this operation is irreversible.

        Returns:
            dict: Success message with details of deleted directories.

        Raises:
            HTTPException: If deletion fails (500 status code).
        """
        return service.purge_all()

    @app.get(
        "/admin/backup",
        tags=[tags],
        openapi_extra={"x-cli-name": "backup"},
        response_class=StreamingResponse,
    )
    async def backup_all_data():
        """Create a backup of all data (skills, tools, snippets, VMCP servers, vNFS servers).

        Returns a compressed JSON file (.json.zip) containing all data.
        The UI should download this file directly.

        Returns:
            StreamingResponse: A ZIP file containing the backup JSON.

        Raises:
            HTTPException: If backup creation fails (500 status code).
        """
        from datetime import datetime

        zip_bytes = service.backup_all()
        return StreamingResponse(
            iter([zip_bytes]),
            media_type="application/zip",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=skillberry-backup-"
                    f"{datetime.utcnow().strftime('%Y-%m-%d')}.json.zip"
                )
            },
        )

    @app.post(
        "/admin/restore",
        tags=[tags],
        openapi_extra={"x-cli-name": "restore"},
    )
    async def restore_all_data(backup_file: UploadFile = File(...)):
        """Restore all data from a backup file.

        This endpoint:
        1. Purges all existing data (calls purge_all_data internally)
        2. Restores data from the uploaded backup file
        3. Imports in order: tools, snippets, skills, VMCP servers, vNFS servers
        4. Starts VMCP/vNFS servers that are in approved state
        5. Rebuilds caches and description indexes

        Args:
            backup_file: The backup ZIP file to restore from.

        Returns:
            dict: Success message with counts of restored items.

        Raises:
            HTTPException: If restore fails (400 or 500 status code).
        """
        content = await backup_file.read()
        return service.restore_all(content)

    @app.get("/health", tags=[tags], openapi_extra={"x-cli-name": "health"})
    def health_check():
        """Health check endpoint.

        Returns:
            dict: Health status of the service.
        """
        return {"status": "healthy"}

    @app.get("/changes", tags=[tags], openapi_extra={"x-cli-name": "changes-count"})
    def get_changes_count():
        """Get the global mutation counter for detecting data changes.

        Returns a counter that increments whenever data is modified (create, update, delete).
        The UI uses this to detect when to refresh data without polling individual endpoints.

        Args:
            None.

        Returns:
            dict: Contains 'count' key with the current mutation counter value.
        """
        from skillberry_store.fast_api.changes import get as get_count

        return {"count": get_count()}

    @app.get("/health/ready", tags=[tags], openapi_extra={"x-cli-name": "health-ready"})
    def readiness_check(request: Request):
        """Readiness check endpoint - verifies all description stores are initialized.

        Returns:
            dict: Readiness status with details about each object type (HTTP 200 when ready).

        Raises:
            HTTPException: 500 status when still initializing.
        """
        result = service.readiness_check()

        # Gate readiness on semantic encoder warmup too. Without this, the first
        # request that triggers an embedding races the background warmup and both
        # concurrently instantiate SentenceTransformer — one path ends up with
        # meta tensors and errors with "Cannot copy out of meta tensor".
        warmup_task = getattr(request.app.state, "encoder_warmup_task", None)
        warmup_done = warmup_task is None or warmup_task.done()
        result.setdefault("checks", {})["encoder_warmup"] = warmup_done
        if not warmup_done:
            raise HTTPException(
                status_code=500,
                detail={"status": "initializing", "checks": result["checks"]},
            )
        return result
