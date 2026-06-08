# Service Layer Pattern — Design Spec

**Date:** 2026-06-08  
**Issue:** [#158 — Refactor to Service Layer Pattern](https://github.com/skillberry-ai/skillberry-store/issues/158)

## Problem

Business logic for content operations (create, update, delete, query) is duplicated between:

1. `fast_api/*_api.py` — HTTP handlers that mix HTTP concerns with business logic
2. `plugins/store_api.py` — reimplements similar logic for plugin access

Changes must be made in two places, risking inconsistency.

## Scope

Service files for the five content-type APIs only:
- `tools_api.py`, `skills_api.py`, `snippets_api.py`, `vnfs_api.py`, `vmcp_api.py`

Out of scope: `plugins_api.py`, `admin_api.py`, `changes.py`, utility files.

## Architecture

```
HTTP Request → FastAPI handler → Service → ObjectHandler (storage)
Plugin call  → StoreAPI proxy  → Service → ObjectHandler (storage)
```

### New files

```
src/skillberry_store/services/
├── __init__.py
├── tools_service.py
├── skills_service.py
├── snippets_service.py
├── vnfs_service.py
└── vmcp_service.py
```

### Modified files

- `fast_api/tools_api.py` — thin HTTP wrapper
- `fast_api/skills_api.py` — thin HTTP wrapper
- `fast_api/snippets_api.py` — thin HTTP wrapper
- `fast_api/vnfs_api.py` — thin HTTP wrapper
- `fast_api/vmcp_api.py` — thin HTTP wrapper
- `plugins/store_api.py` — proxy to service instances
- `fast_api/server.py` — instantiate services, inject into API registers and StoreAPI

## Service Class Interface

Each service takes its `ObjectHandler` and an optional `Description` in its constructor:

```python
class ToolsService:
    def __init__(self, handler: ObjectHandler, descriptions: Optional[Description] = None):
        ...

    def create(self, tool_data: Dict) -> Dict
    def get(self, uuid_or_name: str) -> Dict
    def list_all(self, filters: Optional[Dict] = None) -> List[Dict]
    def update(self, uuid_or_name: str, data: Dict) -> Dict
    def delete(self, uuid_or_name: str) -> None
    def search(self, query: str) -> List[Dict]
```

`SkillsService` additionally exposes:
```python
    def populate_objects(self, skill_dict: Dict) -> Dict  # resolves tool_uuids/snippet_uuids
```

`VnfsService` and `VmcpService` have the same CRUD surface. Server lifecycle operations (start/stop/restart) that currently live in the API handlers and interact with `VirtualNfsServerManager`/`VirtualMcpServerManager` are moved to the service as well, since they are business logic, not HTTP concerns.

## Responsibility Split

| Concern | API layer | Service layer |
|---|---|---|
| HTTP status codes / `HTTPException` | ✅ | ❌ |
| Prometheus counter increments | ✅ | ❌ |
| Plugin event emission (`emit_*`) | ✅ | ❌ |
| UUID generation + validation | ❌ | ✅ |
| Timestamp setting (created_at, modified_at) | ❌ | ✅ |
| Cache management | ❌ | ✅ |
| Description index writes/deletes | ❌ | ✅ |
| Duplicate/not-found checks | ❌ | ✅ |

Services raise Python exceptions:
- `ValueError` — invalid input (missing required fields, malformed UUID)
- `KeyError` — resource not found
- `RuntimeError` — unexpected storage failure

API handlers map these to HTTP status codes (400, 404, 409, 500).

## StoreAPI Refactoring

`store_api.py` becomes a thin proxy holding service references:

```python
class StoreAPI:
    def __init__(self, services: Dict[str, Any]):
        self.tools_service = services.get("tools")
        self.skills_service = services.get("skills")
        self.snippets_service = services.get("snippets")
        self.vnfs_service = services.get("vnfs")
        self.vmcp_service = services.get("vmcp")

    def get_tool(self, uuid: str) -> Optional[Dict]:
        return self.tools_service.get(uuid)
    # all methods delegate to the appropriate service
```

Service instances are created once in `server.py` and shared between FastAPI routes and `StoreAPI` — no duplicated handler references.

## Testing

- Existing end-to-end tests in `tests/` remain unchanged as regression guard for HTTP behavior.
- New service-level unit tests added in `tests/services/`:
  - `test_tools_service.py`
  - `test_skills_service.py`
  - `test_snippets_service.py`
  - `test_vnfs_service.py`
  - `test_vmcp_service.py`
- Service tests exercise business logic (UUID generation, timestamp setting, cache calls, error raising) directly against a mock/real handler — no HTTP layer required.

## Non-Goals

- No changes to `ObjectHandler` or storage layer.
- No changes to schemas (`ToolSchema`, `SkillSchema`, etc.).
- No new API endpoints or behavior changes — this is a pure structural refactor.
- No test changes beyond adding the new service-level tests.
