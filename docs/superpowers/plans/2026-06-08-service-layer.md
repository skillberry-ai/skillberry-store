# Service Layer Pattern Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract business logic from FastAPI handlers and StoreAPI into per-type service classes so both share one implementation.

**Architecture:** Five service classes (`SnippetsService`, `SkillsService`, `ToolsService`, `VnfsService`, `VmcpService`) live in `src/skillberry_store/services/`. FastAPI handlers become thin wrappers that increment counters, emit plugin events, and map service exceptions to HTTP codes. `StoreAPI` delegates every method to a service instance.

**Tech Stack:** Python, FastAPI, pytest, unittest.mock

---

## File Map

**Create:**
- `src/skillberry_store/services/__init__.py`
- `src/skillberry_store/services/snippets_service.py`
- `src/skillberry_store/services/skills_service.py`
- `src/skillberry_store/services/tools_service.py`
- `src/skillberry_store/services/vnfs_service.py`
- `src/skillberry_store/services/vmcp_service.py`
- `src/skillberry_store/tests/services/__init__.py`
- `src/skillberry_store/tests/services/test_snippets_service.py`
- `src/skillberry_store/tests/services/test_skills_service.py`
- `src/skillberry_store/tests/services/test_tools_service.py`
- `src/skillberry_store/tests/services/test_vnfs_service.py`
- `src/skillberry_store/tests/services/test_vmcp_service.py`

**Modify:**
- `src/skillberry_store/fast_api/snippets_api.py`
- `src/skillberry_store/fast_api/skills_api.py`
- `src/skillberry_store/fast_api/tools_api.py`
- `src/skillberry_store/fast_api/vnfs_api.py`
- `src/skillberry_store/fast_api/vmcp_api.py`
- `src/skillberry_store/plugins/store_api.py`
- `src/skillberry_store/fast_api/server.py`

---

## Exception Contract

Services never import from `fastapi`. They raise:
- `ValueError` — invalid input / duplicate UUID (API maps to 400 or 409)
- `KeyError` — resource not found (API maps to 404)
- `RuntimeError` — unexpected storage failure (API maps to 500)

To isolate from handler's `HTTPException`, use this helper in every service:

```python
def _resolve_uuid(self, uuid_or_name: str) -> str:
    try:
        return self.handler.resolve_to_uuid_or_error(uuid_or_name)
    except Exception as e:
        if hasattr(e, "status_code") and e.status_code == 404:
            raise KeyError(f"'{uuid_or_name}' not found")
        raise
```

---

## Task 1: SnippetsService

**Files:**
- Create: `src/skillberry_store/services/__init__.py`
- Create: `src/skillberry_store/services/snippets_service.py`
- Create: `src/skillberry_store/tests/services/__init__.py`
- Create: `src/skillberry_store/tests/services/test_snippets_service.py`
- Modify: `src/skillberry_store/fast_api/snippets_api.py`

- [ ] **Step 1: Create empty init files**

```bash
touch src/skillberry_store/services/__init__.py
touch src/skillberry_store/tests/services/__init__.py
```

- [ ] **Step 2: Write failing tests**

Create `src/skillberry_store/tests/services/test_snippets_service.py`:

```python
import pytest
from unittest.mock import MagicMock, call
from skillberry_store.services.snippets_service import SnippetsService


def _handler(exists=False):
    h = MagicMock()
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = "some-parent"
    h.resolve_to_uuid_or_error.return_value = "aaaa-1111"
    h.read_dict.return_value = {
        "uuid": "aaaa-1111", "name": "s1", "content": "x",
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
    }
    h.list_all_dicts.return_value = [
        {"name": "a", "modified_at": "2024-02-01"},
        {"name": "b", "modified_at": "2024-01-01"},
    ]
    return h


def test_create_generates_uuid_and_timestamps():
    svc = SnippetsService(_handler())
    result = svc.create({"name": "s1", "content": "hello"})
    assert "uuid" in result
    assert "created_at" in result
    assert "modified_at" in result


def test_create_writes_and_updates_cache():
    h = _handler()
    svc = SnippetsService(h)
    svc.create({"name": "s1", "content": "hello"})
    h.write_dict.assert_called_once()
    h.update_cache.assert_called_once()


def test_create_raises_on_duplicate_uuid():
    svc = SnippetsService(_handler(exists=True))
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "s1", "content": "x"})


def test_create_writes_description_when_provided():
    h = _handler()
    desc = MagicMock()
    svc = SnippetsService(h, descriptions=desc)
    svc.create({"name": "s1", "content": "x", "description": "about it"})
    desc.write_description.assert_called_once()


def test_get_returns_dict():
    h = _handler()
    svc = SnippetsService(h)
    result = svc.get("s1")
    assert result["name"] == "s1"


def test_get_raises_key_error_when_not_found():
    h = _handler()
    from fastapi import HTTPException
    h.resolve_to_uuid_or_error.side_effect = HTTPException(status_code=404, detail="not found")
    svc = SnippetsService(h)
    with pytest.raises(KeyError):
        svc.get("missing")


def test_list_all_returns_sorted():
    svc = SnippetsService(_handler())
    result = svc.list_all()
    assert result[0]["name"] == "a"  # most recent first


def test_update_merges_and_preserves_created_at():
    h = _handler()
    svc = SnippetsService(h)
    result = svc.update("s1", {"name": "s1", "content": "new"})
    assert result["created_at"] == "2024-01-01T00:00:00+00:00"
    assert result["content"] == "new"


def test_delete_updates_cache_before_delete():
    h = _handler()
    svc = SnippetsService(h)
    svc.delete("s1")
    # cache updated before object deleted
    cache_call_order = [str(c) for c in h.mock_calls]
    update_idx = next(i for i, c in enumerate(cache_call_order) if "update_cache" in c)
    delete_idx = next(i for i, c in enumerate(cache_call_order) if "delete_object" in c)
    assert update_idx < delete_idx


def test_delete_cleans_up_description():
    h = _handler()
    desc = MagicMock()
    svc = SnippetsService(h, descriptions=desc)
    svc.delete("s1")
    desc.delete_description.assert_called_once_with("aaaa-1111")
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
pytest src/skillberry_store/tests/services/test_snippets_service.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'skillberry_store.services.snippets_service'`

- [ ] **Step 4: Implement SnippetsService**

Create `src/skillberry_store/services/snippets_service.py`:

```python
"""Business logic for snippet CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.modules.description import Description
from skillberry_store.utils.utils import generate_or_validate_uuid

logger = logging.getLogger(__name__)


class SnippetsService:
    def __init__(self, handler: ObjectHandler, descriptions: Optional[Description] = None):
        self.handler = handler
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Snippet '{uuid_or_name}' not found")
            raise

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"Snippet with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(data["uuid"], data["name"])
        self.handler.write_dict(data["uuid"], data)
        if data.get("name"):
            self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"Snippet '{data.get('name')}' created with UUID {data['uuid']}")
        return data

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        return self.handler.read_dict(uuid)

    def list_all(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        items = self.handler.list_all_dicts()
        if filters:
            items = [i for i in items if all(i.get(k) == v for k, v in filters.items())]
        items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return items

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        existing = self.handler.read_dict(uuid)
        old_name = existing.get("name")
        old_parent = existing.get("parent")
        new_name = data.get("name") or old_name
        if new_name:
            data["parent"] = self.handler.get_cache_parent_for_head(uuid, new_name)
        merged = {**existing, **data}
        merged["uuid"] = existing.get("uuid", uuid)
        merged["created_at"] = existing.get("created_at")
        merged["modified_at"] = datetime.now(timezone.utc).isoformat()
        self.handler.write_dict(uuid, merged)
        if new_name:
            self.handler.update_cache(uuid, new_name=new_name, old_name=old_name, old_parent=old_parent)
        if self.descriptions and merged.get("description"):
            self.descriptions.write_description(uuid, merged["description"])
        logger.info(f"Snippet '{uuid_or_name}' updated")
        return merged

    def delete(self, uuid_or_name: str) -> None:
        uuid = self._resolve_uuid(uuid_or_name)
        try:
            d = self.handler.read_dict(uuid)
            name, parent = d.get("name"), d.get("parent")
        except Exception:
            name, parent = None, None
        if uuid and name:
            self.handler.update_cache(uuid, new_name=None, old_name=name, old_parent=parent)
        self.handler.delete_object(uuid)
        if self.descriptions:
            try:
                self.descriptions.delete_description(uuid)
            except Exception as e:
                logger.warning(f"Could not delete snippet description for {uuid}: {e}")
        logger.info(f"Snippet '{uuid_or_name}' deleted")
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest src/skillberry_store/tests/services/test_snippets_service.py -v
```
Expected: all 10 tests PASS.

- [ ] **Step 6: Refactor snippets_api.py to use the service**

Replace the body of `register_snippets_api` so it accepts an optional service and delegates to it. The handler init and all business logic move out; only counters, event emission, and HTTP mapping remain.

Full replacement for `src/skillberry_store/fast_api/snippets_api.py`:

```python
"""Snippets API endpoints for the Skillberry Store service."""

import logging
from typing import Optional, Annotated
from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from prometheus_client import Counter
from skillberry_store.plugins.events import (
    emit_content_added,
    emit_content_updated,
    emit_content_deleted,
)
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.snippet_schema import SnippetSchema
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.services.snippets_service import SnippetsService

logger = logging.getLogger(__name__)

prom_prefix = "sts_fastapi_snippets_"
create_snippet_counter = Counter(f"{prom_prefix}create_snippet_counter", "Count number of snippet create operations")
list_snippets_counter = Counter(f"{prom_prefix}list_snippets_counter", "Count number of snippet list operations")
get_snippet_counter = Counter(f"{prom_prefix}get_snippet_counter", "Count number of snippet get operations")
delete_snippet_counter = Counter(f"{prom_prefix}delete_snippet_counter", "Count number of snippet delete operations")
update_snippet_counter = Counter(f"{prom_prefix}update_snippet_counter", "Count number of snippet update operations")
search_snippets_counter = Counter(f"{prom_prefix}search_snippets_counter", "Count number of snippet search operations")


def register_snippets_api(
    app: FastAPI,
    tags: str = "snippets",
    snippets_descriptions: Optional[Description] = None,
    service: Optional[SnippetsService] = None,
):
    if service is None:
        from skillberry_store.modules.object_handler import get_object_handler
        service = SnippetsService(get_object_handler("snippet"), snippets_descriptions)

    @app.post("/snippets/", tags=[tags], openapi_extra={"x-cli-name": "create-snippet"})
    async def create_snippet(
        snippet: Annotated[SnippetSchema, Query()],
        file: Optional[UploadFile] = File(None),
    ):
        logger.info(f"Request to create snippet: {snippet.name}")
        create_snippet_counter.inc()
        if file:
            try:
                content_bytes = await file.read()
                snippet.content = content_bytes.decode("utf-8")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error reading uploaded file: {str(e)}")
        try:
            result = service.create(snippet.to_dict())
            emit_content_added("snippet", result["uuid"])
            return {"message": f"Snippet '{result['name']}' created successfully.", "name": result["name"], "uuid": result["uuid"]}
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating snippet '{snippet.name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error creating snippet: {str(e)}")

    @app.get("/snippets/", tags=[tags], openapi_extra={"x-cli-name": "list-snippets"})
    def list_snippets():
        logger.info("Request to list snippets")
        list_snippets_counter.inc()
        try:
            return service.list_all()
        except Exception as e:
            logger.error(f"Error listing snippets: {e}")
            raise HTTPException(status_code=500, detail=f"Error listing snippets: {str(e)}")

    @app.get("/snippets/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "get-snippet"})
    def get_snippet(uuid_or_name: str):
        logger.info(f"Request to get snippet: {uuid_or_name}")
        get_snippet_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving snippet '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving snippet: {str(e)}")

    @app.delete("/snippets/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "delete-snippet"})
    async def delete_snippet(uuid_or_name: str):
        logger.info(f"Request to delete snippet: {uuid_or_name}")
        delete_snippet_counter.inc()
        try:
            snippet = service.get(uuid_or_name)
            snippet_uuid = snippet["uuid"]
            service.delete(uuid_or_name)
            emit_content_deleted("snippet", snippet_uuid)
            return {"message": f"Snippet with UUID or name '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception(f"Error deleting snippet '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting snippet: {str(e)}")

    @app.put("/snippets/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "update-snippet"})
    async def update_snippet(uuid_or_name: str, snippet: SnippetSchema):
        logger.info(f"Request to update snippet: {uuid_or_name}")
        update_snippet_counter.inc()
        try:
            result = service.update(uuid_or_name, snippet.to_dict())
            emit_content_updated("snippet", result["uuid"])
            return {"message": f"Snippet with UUID or name '{uuid_or_name}' updated successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating snippet '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error updating snippet: {str(e)}")

    @app.get("/search/snippets", tags=[tags], openapi_extra={"x-cli-name": "search-snippets"})
    def search_snippets(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        logger.info(f"Request to search snippets for term: {search_term}")
        search_snippets_counter.inc()
        if not snippets_descriptions:
            raise HTTPException(status_code=503, detail="Snippet search is not available")
        try:
            matched = snippets_descriptions.search_description(search_term=search_term, k=max_number_of_results)
            filtered = [m for m in matched if float(m["similarity_score"]) <= similarity_threshold]
            snippets_to_filter = []
            for m in filtered:
                name = m.get("filename") or m.get("name")
                if not name:
                    continue
                try:
                    d = service.get(name)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    snippets_to_filter.append(d)
                except Exception:
                    pass
            result_snippets = apply_search_filters(snippets_to_filter, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
            result_snippets.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [{"filename": s.get("name", ""), "similarity_score": s.get("similarity_score", 0.0)} for s in result_snippets if s.get("name")]
        except Exception as e:
            logger.error(f"Error searching snippets: {e}")
            raise HTTPException(status_code=500, detail=f"Error searching snippets: {str(e)}")
```

- [ ] **Step 7: Run full test suite**

```bash
pytest src/skillberry_store/tests/ -v -m "not integration" 2>&1 | tail -20
```
Expected: all existing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add src/skillberry_store/services/__init__.py \
        src/skillberry_store/services/snippets_service.py \
        src/skillberry_store/tests/services/__init__.py \
        src/skillberry_store/tests/services/test_snippets_service.py \
        src/skillberry_store/fast_api/snippets_api.py
git commit -m "feat: extract SnippetsService and refactor snippets_api to thin wrapper"
```

---

## Task 2: SkillsService

**Files:**
- Create: `src/skillberry_store/services/skills_service.py`
- Create: `src/skillberry_store/tests/services/test_skills_service.py`
- Modify: `src/skillberry_store/fast_api/skills_api.py`

- [ ] **Step 1: Write failing tests**

Create `src/skillberry_store/tests/services/test_skills_service.py`:

```python
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from skillberry_store.services.skills_service import SkillsService


def _handler(exists=False):
    h = MagicMock()
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = None
    h.resolve_to_uuid_or_error.return_value = "bbbb-2222"
    h.read_dict.return_value = {
        "uuid": "bbbb-2222", "name": "sk1",
        "tool_uuids": [], "snippet_uuids": [],
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
    }
    h.list_all_dicts.return_value = [
        {"name": "a", "modified_at": "2024-02-01", "tool_uuids": [], "snippet_uuids": []},
    ]
    return h


def test_create_generates_uuid():
    svc = SkillsService(_handler(), tools_handler=MagicMock(), snippets_handler=MagicMock())
    result = svc.create({"name": "sk1"})
    assert "uuid" in result


def test_create_raises_on_duplicate():
    svc = SkillsService(_handler(exists=True), tools_handler=MagicMock(), snippets_handler=MagicMock())
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "sk1"})


def test_populate_objects_adds_tools_and_snippets():
    tools_h = MagicMock()
    tools_h.read_dicts.return_value = [{"uuid": "t1", "name": "tool1"}]
    snippets_h = MagicMock()
    snippets_h.read_dicts.return_value = []
    svc = SkillsService(_handler(), tools_handler=tools_h, snippets_handler=snippets_h)
    skill = {"name": "sk1", "tool_uuids": ["t1"], "snippet_uuids": []}
    result = svc.populate_objects(skill)
    assert result["tools"] == [{"uuid": "t1", "name": "tool1"}]
    assert result["snippets"] == []


def test_list_all_returns_sorted_and_populated():
    th, sh = MagicMock(), MagicMock()
    th.read_dicts.return_value = []
    sh.read_dicts.return_value = []
    svc = SkillsService(_handler(), tools_handler=th, snippets_handler=sh)
    result = svc.list_all()
    assert len(result) == 1


def test_delete_updates_cache_then_deletes():
    h = _handler()
    svc = SkillsService(h, tools_handler=MagicMock(), snippets_handler=MagicMock())
    svc.delete("sk1")
    calls = [str(c) for c in h.mock_calls]
    assert any("update_cache" in c for c in calls)
    assert any("delete_object" in c for c in calls)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest src/skillberry_store/tests/services/test_skills_service.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement SkillsService**

Create `src/skillberry_store/services/skills_service.py`:

```python
"""Business logic for skill CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.modules.description import Description
from skillberry_store.utils.utils import generate_or_validate_uuid

logger = logging.getLogger(__name__)


class SkillsService:
    def __init__(
        self,
        handler: ObjectHandler,
        tools_handler: ObjectHandler,
        snippets_handler: ObjectHandler,
        descriptions: Optional[Description] = None,
    ):
        self.handler = handler
        self.tools_handler = tools_handler
        self.snippets_handler = snippets_handler
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Skill '{uuid_or_name}' not found")
            raise

    def populate_objects(self, skill_dict: Dict[str, Any]) -> Dict[str, Any]:
        if skill_dict.get("tool_uuids"):
            try:
                skill_dict["tools"] = self.tools_handler.read_dicts(skill_dict["tool_uuids"])
            except Exception as e:
                raise RuntimeError(f"Skill '{skill_dict.get('name')}' references missing tools: {e}")
        else:
            skill_dict["tools"] = []
        if skill_dict.get("snippet_uuids"):
            try:
                skill_dict["snippets"] = self.snippets_handler.read_dicts(skill_dict["snippet_uuids"])
            except Exception as e:
                raise RuntimeError(f"Skill '{skill_dict.get('name')}' references missing snippets: {e}")
        else:
            skill_dict["snippets"] = []
        return skill_dict

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"Skill with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(data["uuid"], data["name"])
        self.handler.write_dict(data["uuid"], data)
        if data.get("name"):
            self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"Skill '{data.get('name')}' created with UUID {data['uuid']}")
        return data

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        skill = self.handler.read_dict(uuid)
        return self.populate_objects(skill)

    def list_all(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        items = self.handler.list_all_dicts()
        if filters:
            items = [i for i in items if all(i.get(k) == v for k, v in filters.items())]
        for item in items:
            self.populate_objects(item)
        items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return items

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        existing = self.handler.read_dict(uuid)
        old_name = existing.get("name")
        old_parent = existing.get("parent")
        new_name = data.get("name") or old_name
        if new_name:
            data["parent"] = self.handler.get_cache_parent_for_head(uuid, new_name)
        merged = {**existing, **data}
        merged["uuid"] = existing.get("uuid", uuid)
        merged["created_at"] = existing.get("created_at")
        merged["modified_at"] = datetime.now(timezone.utc).isoformat()
        self.handler.write_dict(uuid, merged)
        if new_name:
            self.handler.update_cache(uuid, new_name=new_name, old_name=old_name, old_parent=old_parent)
        if self.descriptions and merged.get("description"):
            self.descriptions.write_description(uuid, merged["description"])
        logger.info(f"Skill '{uuid_or_name}' updated")
        return merged

    def delete(self, uuid_or_name: str) -> None:
        uuid = self._resolve_uuid(uuid_or_name)
        try:
            d = self.handler.read_dict(uuid)
            name, parent = d.get("name"), d.get("parent")
        except Exception:
            name, parent = None, None
        if uuid and name:
            self.handler.update_cache(uuid, new_name=None, old_name=name, old_parent=parent)
        self.handler.delete_object(uuid)
        if self.descriptions:
            try:
                self.descriptions.delete_description(uuid)
            except Exception as e:
                logger.warning(f"Could not delete skill description for {uuid}: {e}")
        logger.info(f"Skill '{uuid_or_name}' deleted")
```

- [ ] **Step 4: Run service tests**

```bash
pytest src/skillberry_store/tests/services/test_skills_service.py -v
```
Expected: all PASS.

- [ ] **Step 5: Refactor skills_api.py**

Replace the full content of `src/skillberry_store/fast_api/skills_api.py` with:

```python
"""Skills API endpoints for the Skillberry Store service."""

import logging
from typing import Optional, Annotated, List
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import Response
from prometheus_client import Counter
from skillberry_store.plugins.events import (
    emit_content_added,
    emit_content_updated,
    emit_content_deleted,
)
from skillberry_store.tools.anthropic.importer import import_from_anthropic_skill
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.skill_schema import SkillSchema
from skillberry_store.schemas.manifest_schema import ManifestState
from skillberry_store.tools.anthropic.exporter import export_skill_to_anthropic_format
from skillberry_store.tools.configure import (
    get_files_directory_path,
    get_skills_directory,
    get_tools_directory,
    get_snippets_directory,
    is_auto_detect_dependencies_enabled,
)
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.services.skills_service import SkillsService

logger = logging.getLogger(__name__)

prom_prefix = "sts_fastapi_skills_"
create_skill_counter = Counter(f"{prom_prefix}create_skill_counter", "Count number of skill create operations")
list_skills_counter = Counter(f"{prom_prefix}list_skills_counter", "Count number of skill list operations")
get_skill_counter = Counter(f"{prom_prefix}get_skill_counter", "Count number of skill get operations")
delete_skill_counter = Counter(f"{prom_prefix}delete_skill_counter", "Count number of skill delete operations")
update_skill_counter = Counter(f"{prom_prefix}update_skill_counter", "Count number of skill update operations")
search_skills_counter = Counter(f"{prom_prefix}search_skills_counter", "Count number of skill search operations")


def register_skills_api(
    app: FastAPI,
    tags: str = "skills",
    skills_descriptions: Optional[Description] = None,
    service: Optional[SkillsService] = None,
):
    if service is None:
        from skillberry_store.modules.object_handler import get_object_handler
        service = SkillsService(
            handler=get_object_handler("skill"),
            tools_handler=get_object_handler("tool"),
            snippets_handler=get_object_handler("snippet"),
            descriptions=skills_descriptions,
        )

    @app.post("/skills/", tags=[tags], openapi_extra={"x-cli-name": "create-skill"})
    async def create_skill(skill: Annotated[SkillSchema, Query()]):
        logger.info(f"Request to create skill: {skill.name}")
        create_skill_counter.inc()
        try:
            result = service.create(skill.to_dict())
            emit_content_added("skill", result["uuid"])
            return {"message": f"Skill '{result['name']}' created successfully.", "name": result["name"], "uuid": result["uuid"]}
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating skill '{skill.name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error creating skill: {str(e)}")

    @app.get("/skills/", tags=[tags], openapi_extra={"x-cli-name": "list-skills"})
    def list_skills():
        logger.info("Request to list skills")
        list_skills_counter.inc()
        try:
            return service.list_all()
        except Exception as e:
            logger.error(f"Error listing skills: {e}")
            raise HTTPException(status_code=500, detail=f"Error listing skills: {str(e)}")

    @app.get("/skills/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "get-skill"})
    def get_skill(uuid_or_name: str):
        logger.info(f"Request to get skill: {uuid_or_name}")
        get_skill_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=505, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving skill '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving skill: {str(e)}")

    @app.delete("/skills/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "delete-skill"})
    async def delete_skill(uuid_or_name: str):
        logger.info(f"Request to delete skill: {uuid_or_name}")
        delete_skill_counter.inc()
        try:
            skill = service.get(uuid_or_name)
            skill_uuid = skill["uuid"]
            service.delete(uuid_or_name)
            emit_content_deleted("skill", skill_uuid)
            return {"message": f"Skill with UUID or name '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting skill '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting skill: {str(e)}")

    @app.put("/skills/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "update-skill"})
    async def update_skill(uuid_or_name: str, skill: SkillSchema):
        logger.info(f"Request to update skill: {uuid_or_name}")
        update_skill_counter.inc()
        try:
            result = service.update(uuid_or_name, skill.to_dict())
            emit_content_updated("skill", result["uuid"])
            return {"message": f"Skill with UUID or name '{uuid_or_name}' updated successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating skill '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error updating skill: {str(e)}")

    @app.get("/search/skills", tags=[tags], openapi_extra={"x-cli-name": "search-skills"})
    def search_skills(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        logger.info(f"Request to search skills for: {search_term}")
        search_skills_counter.inc()
        if not skills_descriptions:
            raise HTTPException(status_code=503, detail="Skill search is not available")
        try:
            matched = skills_descriptions.search_description(search_term=search_term, k=max_number_of_results)
            filtered = [m for m in matched if float(m["similarity_score"]) <= similarity_threshold]
            skills_to_filter = []
            for m in filtered:
                name = m.get("filename") or m.get("name")
                if not name:
                    continue
                try:
                    d = service.get(name)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    skills_to_filter.append(d)
                except Exception:
                    pass
            result_skills = apply_search_filters(skills_to_filter, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
            result_skills.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [{"filename": s.get("name", ""), "similarity_score": s.get("similarity_score", 0.0)} for s in result_skills if s.get("name")]
        except Exception as e:
            logger.error(f"Error searching skills: {e}")
            raise HTTPException(status_code=500, detail=f"Error searching skills: {str(e)}")

    @app.post("/skills/import/anthropic", tags=[tags], openapi_extra={"x-cli-name": "import-anthropic-skill"})
    async def import_anthropic_skill(zip_file: UploadFile = File(...)):
        """Import a skill from an Anthropic-format zip file."""
        try:
            content = await zip_file.read()
            result = import_from_anthropic_skill(
                zip_content=content,
                skills_dir=get_skills_directory(),
                tools_dir=get_tools_directory(),
                snippets_dir=get_snippets_directory(),
                files_dir=get_files_directory_path(),
            )
            return result
        except Exception as e:
            logger.error(f"Error importing Anthropic skill: {e}")
            raise HTTPException(status_code=500, detail=f"Error importing skill: {str(e)}")

    @app.get("/skills/{uuid_or_name}/export/anthropic", tags=[tags], openapi_extra={"x-cli-name": "export-anthropic-skill"})
    def export_anthropic_skill(uuid_or_name: str):
        """Export a skill to Anthropic format zip."""
        try:
            skill = service.get(uuid_or_name)
            zip_bytes = export_skill_to_anthropic_format(skill)
            return Response(
                content=zip_bytes,
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={skill.get('name', uuid_or_name)}.zip"},
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error exporting skill '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error exporting skill: {str(e)}")
```

- [ ] **Step 6: Run full test suite**

```bash
pytest src/skillberry_store/tests/ -v -m "not integration" 2>&1 | tail -20
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/skillberry_store/services/skills_service.py \
        src/skillberry_store/tests/services/test_skills_service.py \
        src/skillberry_store/fast_api/skills_api.py
git commit -m "feat: extract SkillsService and refactor skills_api to thin wrapper"
```

---

## Task 3: ToolsService

**Files:**
- Create: `src/skillberry_store/services/tools_service.py`
- Create: `src/skillberry_store/tests/services/test_tools_service.py`
- Modify: `src/skillberry_store/fast_api/tools_api.py`

- [ ] **Step 1: Write failing tests**

Create `src/skillberry_store/tests/services/test_tools_service.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from skillberry_store.services.tools_service import ToolsService


def _handler(exists=False):
    h = MagicMock()
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = None
    h.resolve_to_uuid_or_error.return_value = "cccc-3333"
    h.read_dict.return_value = {
        "uuid": "cccc-3333", "name": "t1", "module_name": "t1.py",
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
        "dependencies": [],
    }
    h.list_all_dicts.return_value = [{"name": "a", "modified_at": "2024-02-01"}]
    h.read_file.return_value = "def hello(): pass"
    h.read_dicts.return_value = []
    h.get_existing_names.return_value = []
    return h


def test_create_generates_uuid_and_timestamps():
    svc = ToolsService(_handler())
    result = svc.create({"name": "t1"}, module_content=b"def f(): pass", module_filename="t1.py")
    assert "uuid" in result
    assert result["module_name"] == "t1.py"


def test_create_raises_on_duplicate():
    svc = ToolsService(_handler(exists=True))
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "t1"}, module_content=b"def f(): pass", module_filename="t1.py")


def test_get_returns_tool_dict():
    svc = ToolsService(_handler())
    result = svc.get("t1")
    assert result["name"] == "t1"


def test_get_raises_key_error_when_not_found():
    h = _handler()
    h.resolve_to_uuid_or_error.side_effect = HTTPException(status_code=404, detail="not found")
    svc = ToolsService(h)
    with pytest.raises(KeyError):
        svc.get("missing")


def test_list_all_sorted():
    svc = ToolsService(_handler())
    result = svc.list_all()
    assert len(result) == 1


def test_get_module_returns_file_content():
    svc = ToolsService(_handler())
    content = svc.get_module("t1")
    assert "def hello" in content


def test_delete_updates_cache_then_deletes():
    h = _handler()
    svc = ToolsService(h)
    svc.delete("t1")
    calls = [str(c) for c in h.mock_calls]
    update_idx = next(i for i, c in enumerate(calls) if "update_cache" in c)
    delete_idx = next(i for i, c in enumerate(calls) if "delete_object" in c)
    assert update_idx < delete_idx


def test_find_dependencies_returns_empty_for_no_deps():
    svc = ToolsService(_handler())
    result = svc.find_dependencies([], "t1")
    assert result == set()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest src/skillberry_store/tests/services/test_tools_service.py -v 2>&1 | head -10
```

- [ ] **Step 3: Implement ToolsService**

Create `src/skillberry_store/services/tools_service.py`:

```python
"""Business logic for tool CRUD and execution operations."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.modules.description import Description
from skillberry_store.modules.file_executor import detect_tool_dependencies
from skillberry_store.utils.utils import generate_or_validate_uuid
from skillberry_store.tools.configure import is_auto_detect_dependencies_enabled

logger = logging.getLogger(__name__)


class ToolsService:
    def __init__(self, handler: ObjectHandler, descriptions: Optional[Description] = None):
        self.handler = handler
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Tool '{uuid_or_name}' not found")
            raise

    def find_dependencies(self, dependencies: List[str], tool_uuid: str) -> Set[str]:
        """Recursively resolve all transitive dependency UUIDs."""
        found: Set[str] = set()
        if not dependencies:
            return found
        for dep_uuid in dependencies:
            if dep_uuid in found:
                continue
            found.add(dep_uuid)
            dep_dict = self.handler.read_dict(dep_uuid)
            nested = dep_dict.get("dependencies", [])
            if nested:
                found.update(self.find_dependencies(nested, dep_uuid))
        return found

    def create(self, data: Dict[str, Any], module_content: bytes, module_filename: str) -> Dict[str, Any]:
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"Tool with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(data["uuid"], data["name"])
        self.handler.write_file(data["uuid"], module_filename, module_content)
        data["module_name"] = module_filename
        if not data.get("dependencies") and is_auto_detect_dependencies_enabled():
            try:
                content_str = module_content.decode("utf-8") if isinstance(module_content, bytes) else module_content
                available = self.handler.get_existing_names()
                detected_names = detect_tool_dependencies(content_str, data["name"], available)
                if detected_names:
                    data["dependencies"] = [self.handler.name_to_uuid(n) for n in detected_names]
            except Exception as e:
                logger.warning(f"Failed to auto-detect dependencies: {e}")
        self.handler.write_dict(data["uuid"], data)
        self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"Tool '{data.get('name')}' created with UUID {data['uuid']}")
        return data

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        return self.handler.read_dict(uuid)

    def get_module(self, uuid_or_name: str) -> str:
        uuid = self._resolve_uuid(uuid_or_name)
        tool = self.handler.read_dict(uuid)
        module_name = tool.get("module_name")
        if not module_name:
            raise KeyError(f"Tool '{uuid_or_name}' has no module file")
        content = self.handler.read_file(uuid, module_name, raw_content=True)
        if not isinstance(content, str):
            raise RuntimeError(f"Invalid module content type for tool '{uuid_or_name}'")
        return content

    def list_all(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        items = self.handler.list_all_dicts()
        if filters:
            items = [i for i in items if all(i.get(k) == v for k, v in filters.items())]
        items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return items

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        existing = self.handler.read_dict(uuid)
        old_name = existing.get("name")
        old_parent = existing.get("parent")
        new_name = data.get("name") or old_name
        if new_name:
            data["parent"] = self.handler.get_cache_parent_for_head(uuid, new_name)
        merged = {**existing, **data}
        merged["uuid"] = existing.get("uuid", uuid)
        merged["created_at"] = existing.get("created_at")
        merged["modified_at"] = datetime.now(timezone.utc).isoformat()
        self.handler.write_dict(uuid, merged)
        if new_name:
            self.handler.update_cache(uuid, new_name=new_name, old_name=old_name, old_parent=old_parent)
        if self.descriptions and data.get("description"):
            old_desc = existing.get("description")
            if old_desc != data["description"]:
                try:
                    self.descriptions.delete_description(uuid)
                except Exception:
                    pass
                self.descriptions.write_description(uuid, data["description"])
        logger.info(f"Tool '{uuid_or_name}' updated")
        return merged

    def delete(self, uuid_or_name: str) -> None:
        uuid = self._resolve_uuid(uuid_or_name)
        try:
            d = self.handler.read_dict(uuid)
            name, parent = d.get("name"), d.get("parent")
        except Exception:
            name, parent = None, None
        if uuid and name:
            self.handler.update_cache(uuid, new_name=None, old_name=name, old_parent=parent)
        self.handler.delete_object(uuid)
        if self.descriptions:
            try:
                self.descriptions.delete_description(uuid)
            except Exception as e:
                logger.warning(f"Could not delete tool description for {uuid}: {e}")
        logger.info(f"Tool '{uuid_or_name}' deleted")
```

- [ ] **Step 4: Run service tests**

```bash
pytest src/skillberry_store/tests/services/test_tools_service.py -v
```
Expected: all PASS.

- [ ] **Step 5: Refactor tools_api.py**

In `src/skillberry_store/fast_api/tools_api.py`, make these targeted changes:

**a)** Add import at top:
```python
from skillberry_store.services.tools_service import ToolsService
```

**b)** Change `register_tools_api` signature and add service creation at the top of the function body, replacing `tool_handler = get_object_handler("tool")`:

```python
def register_tools_api(
    app: FastAPI,
    tags: str = "tools",
    tools_descriptions: Optional[Description] = None,
    service: Optional[ToolsService] = None,
):
    if service is None:
        service = ToolsService(get_object_handler("tool"), tools_descriptions)
    tool_handler = service.handler  # kept for execute_tool and add_tool_from_python which still need direct handler access
```

**c)** Replace `create_tool` body (keeping the file-read `await` in the API, delegating the rest):

```python
    @app.post("/tools/", tags=[tags], openapi_extra={"x-cli-name": "create-tool"})
    async def create_tool(
        tool: Annotated[ToolSchema, Query()],
        module: UploadFile = File(...),
    ) -> Dict[str, Any]:
        logger.info(f"Request to create tool: {tool.name}")
        create_tool_counter.inc()
        try:
            file_content = await module.read()
            module_filename = module.filename if module.filename else f"{tool.name}.py"
            result = service.create(tool.to_dict(), module_content=file_content, module_filename=module_filename)
            emit_content_added("tool", result["uuid"])
            return {"message": f"Tool '{result['name']}' created successfully.", "name": result["name"], "uuid": result["uuid"], "module_name": result["module_name"]}
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating tool '{tool.name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error creating tool: {str(e)}")
```

**d)** Replace `list_tools` body:

```python
    @app.get("/tools/", tags=[tags], openapi_extra={"x-cli-name": "list-tools"})
    def list_tools() -> List[Dict[str, Any]]:
        logger.info("Request to list tools")
        list_tools_counter.inc()
        try:
            return service.list_all()
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Error listing tools: {e}\n{error_traceback}")
            raise HTTPException(status_code=500, detail=f"Error listing tools: {str(e)}\n{error_traceback}")
```

**e)** Replace `get_tool` body:

```python
    @app.get("/tools/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "get-tool"})
    def get_tool(uuid_or_name: str) -> Dict[str, Any]:
        logger.info(f"Request to get tool: {uuid_or_name}")
        get_tool_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving tool '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving tool: {str(e)}")
```

**f)** Replace `get_tool_module` body — delegate MCP case to server_utils (stays in API since it's async and uses HTTP-layer helpers), delegate code case to service:

```python
    @app.get("/tools/{uuid_or_name}/module", tags=[tags], response_class=PlainTextResponse, openapi_extra={"x-cli-name": "get-tool-module"})
    async def get_tool_module(uuid_or_name: str) -> PlainTextResponse:
        logger.info(f"Request to get module file for tool: {uuid_or_name}")
        get_tool_module_counter.inc()
        try:
            tool_dict = service.get(uuid_or_name)
            if tool_dict.get("packaging_format") == "mcp":
                tools = await get_mcp_tools(tool_dict)
                if not tools:
                    raise HTTPException(status_code=404, detail=f"MCP tool '{uuid_or_name}' not found.")
                return PlainTextResponse(content=mcp_content(vars(tools[0])), media_type="text/plain")
            content = service.get_module(uuid_or_name)
            return PlainTextResponse(content=content, media_type="text/plain")
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving module for '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving module: {str(e)}")
```

**g)** Replace `delete_tool` body:

```python
    @app.delete("/tools/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "delete-tool"})
    async def delete_tool(uuid_or_name: str) -> Dict:
        logger.info(f"Request to delete tool: {uuid_or_name}")
        delete_tool_counter.inc()
        try:
            tool = service.get(uuid_or_name)
            tool_uuid = tool["uuid"]
            service.delete(uuid_or_name)
            emit_content_deleted("tool", tool_uuid)
            return {"message": f"Tool with UUID or name '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting tool '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting tool: {str(e)}")
```

**h)** Replace `update_tool` body:

```python
    @app.put("/tools/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "update-tool"})
    async def update_tool(uuid_or_name: str, tool: ToolSchema) -> Dict:
        logger.info(f"Request to update tool: {uuid_or_name}")
        update_tool_counter.inc()
        try:
            result = service.update(uuid_or_name, tool.to_dict())
            emit_content_updated("tool", result["uuid"])
            return {"message": f"Tool with UUID or name '{uuid_or_name}' updated successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating tool '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error updating tool: {str(e)}")
```

**i)** In `execute_tool`: extract `env_id` from headers (HTTP concern stays in API), then delegate execution logic using `service.handler` and `service.find_dependencies`. Replace the UUID/dict resolution at the top of `execute_tool`:

```python
    @app.post("/tools/{uuid_or_name}/execute", tags=[tags], openapi_extra={"x-cli-name": "execute-tool"})
    async def execute_tool(uuid_or_name: str, request: Request, parameters: Optional[Dict[str, Any]] = None) -> Dict:
        try:
            tool_dict = service.get(uuid_or_name)
            tool_uuid = tool_dict["uuid"]
            tool_name = tool_dict.get("name", uuid_or_name)
            execute_tool_counter.labels(name=tool_uuid).inc()
            start_time = time.time()
            headers_dict = dict(request.headers.items())
            skillberry_context = unflatten_keys(headers_dict).get(SKILLBERRY_CONTEXT.lower())
            env_id = skillberry_context.get("env_id") if skillberry_context else None
            if tool_dict.get("packaging_format") == "mcp":
                module_content = mcp_content_from_manifest(tool_dict)
            else:
                module_content = service.get_module(uuid_or_name)
            dep_uuids = service.find_dependencies(tool_dict.get("dependencies", []), tool_uuid)
            dep_dicts = service.handler.read_dicts(list(dep_uuids))
            dep_files = [service.handler.read_file(m["uuid"], m["module_name"], raw_content=True) for m in dep_dicts]
            file_executor = FileExecutor(name=tool_name, file_content=module_content, file_manifest=tool_dict, dependent_file_contents=dep_files, dependent_tools_as_dict=dep_dicts)
            result = await file_executor.execute_file(parameters=parameters or {}, env_id=env_id)
            if not (isinstance(result, dict) and "error" in result):
                duration = time.time() - start_time
                execute_successfully_tool_counter.labels(name=tool_uuid).inc()
                execute_successfully_tool_latency.labels(name=tool_uuid).observe(duration)
            else:
                error_message = result.get("error", "Unknown Error")
                status_code = 404 if "not found" in error_message.lower() else 500
                raise HTTPException(status_code=status_code, detail=error_message)
            return result
        except HTTPException:
            raise
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error executing tool '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error executing tool: {str(e)}")
```

**j)** Replace `search_tools` body:

```python
    @app.get("/search/tools", tags=[tags], openapi_extra={"x-cli-name": "search-tools"})
    def search_tools(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ) -> List:
        logger.info(f"Request to search tools for: {search_term}")
        search_tools_counter.inc()
        if not tools_descriptions:
            raise HTTPException(status_code=503, detail="Tool search is not available")
        try:
            matched = tools_descriptions.search_description(search_term=search_term, k=max_number_of_results)
            filtered = [m for m in matched if float(m["similarity_score"]) <= similarity_threshold]
            tools_to_filter = []
            for m in filtered:
                name = m.get("filename") or m.get("name")
                if not name:
                    continue
                try:
                    d = service.get(name)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    tools_to_filter.append(d)
                except Exception:
                    pass
            result_tools = apply_search_filters(tools_to_filter, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
            result_tools.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [{"filename": t.get("name", ""), "similarity_score": t.get("similarity_score", 0.0)} for t in result_tools if t.get("name")]
        except Exception as e:
            logger.error(f"Error searching tools: {e}")
            raise HTTPException(status_code=500, detail=f"Error searching tools: {str(e)}")
```

- [ ] **Step 6: Run full test suite**

```bash
pytest src/skillberry_store/tests/ -v -m "not integration" 2>&1 | tail -30
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/skillberry_store/services/tools_service.py \
        src/skillberry_store/tests/services/test_tools_service.py \
        src/skillberry_store/fast_api/tools_api.py
git commit -m "feat: extract ToolsService and refactor tools_api to thin wrapper"
```

---

## Task 4: VnfsService

**Files:**
- Create: `src/skillberry_store/services/vnfs_service.py`
- Create: `src/skillberry_store/tests/services/test_vnfs_service.py`
- Modify: `src/skillberry_store/fast_api/vnfs_api.py`

- [ ] **Step 1: Write failing tests**

Create `src/skillberry_store/tests/services/test_vnfs_service.py`:

```python
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from skillberry_store.services.vnfs_service import VnfsService


def _handler(exists=False):
    h = MagicMock()
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = None
    h.resolve_to_uuid_or_error.return_value = "dddd-4444"
    h.read_dict.return_value = {
        "uuid": "dddd-4444", "name": "v1", "port": 9000,
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
    }
    h.list_all_dicts.return_value = [{"uuid": "dddd-4444", "name": "v1", "port": 9000, "modified_at": "2024-02-01"}]
    return h


def _manager():
    m = MagicMock()
    runtime = MagicMock()
    runtime.port = 9000
    runtime.running = True
    runtime.export_path = "/tmp/export"
    m.add_server.return_value = runtime
    m.get_server.return_value = runtime
    return m


def test_create_returns_dict_with_port():
    svc = VnfsService(_handler(), _manager())
    result = svc.create({"name": "v1", "uuid": None})
    assert "uuid" in result
    assert result["port"] == 9000


def test_create_raises_on_duplicate():
    svc = VnfsService(_handler(exists=True), _manager())
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "v1", "uuid": None})


def test_list_includes_running_status():
    svc = VnfsService(_handler(), _manager())
    result = svc.list_all()
    assert result["virtual_nfs_servers"]


def test_delete_stops_runtime_then_removes_persistent():
    h = _handler()
    mgr = _manager()
    svc = VnfsService(h, mgr)
    svc.delete("v1")
    mgr.remove_server.assert_called_once()
    h.delete_object.assert_called_once()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest src/skillberry_store/tests/services/test_vnfs_service.py -v 2>&1 | head -10
```

- [ ] **Step 3: Implement VnfsService**

Create `src/skillberry_store/services/vnfs_service.py`:

```python
"""Business logic for virtual NFS server CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.modules.description import Description
from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager
from skillberry_store.utils.utils import generate_or_validate_uuid

logger = logging.getLogger(__name__)


class VnfsService:
    def __init__(
        self,
        handler: ObjectHandler,
        server_manager: VirtualNfsServerManager,
        descriptions: Optional[Description] = None,
    ):
        self.handler = handler
        self.server_manager = server_manager
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"vNFS server '{uuid_or_name}' not found")
            raise

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"vNFS server with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(data["uuid"], data["name"])

        from skillberry_store.schemas.vnfs_schema import VnfsSchema
        vnfs_obj = VnfsSchema(**{k: v for k, v in data.items() if k in VnfsSchema.model_fields})
        server = self.server_manager.add_server(vnfs_obj)
        data["port"] = server.port

        self.handler.write_dict(data["uuid"], data)
        if data.get("name"):
            self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"vNFS server '{data.get('name')}' created on port {server.port}")
        return data

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        d = self.handler.read_dict(uuid)
        try:
            runtime = self.server_manager.get_server(d.get("name", ""), d.get("uuid", ""))
            d["running"] = runtime is not None and runtime.running
            d["export_path"] = str(runtime.export_path) if runtime else None
        except Exception:
            d["running"] = False
            d["export_path"] = None
        return d

    def list_all(self) -> Dict[str, Any]:
        items = self.handler.list_all_dicts()
        servers = []
        for item in items:
            try:
                runtime = None
                try:
                    runtime = self.server_manager.get_server(item.get("name", ""), item.get("uuid", ""))
                except Exception:
                    pass
                info = {
                    "uuid": item.get("uuid"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "version": item.get("version"),
                    "state": item.get("state"),
                    "tags": item.get("tags", []),
                    "port": item.get("port"),
                    "skill_uuid": item.get("skill_uuid"),
                    "protocol": item.get("protocol", "webdav"),
                    "modified_at": item.get("modified_at", ""),
                    "running": runtime is not None and runtime.running,
                    "export_path": str(runtime.export_path) if runtime else None,
                }
                servers.append(info)
            except Exception as e:
                logger.warning(f"Error loading vnfs server '{item.get('name')}': {e}")
        servers.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return {"virtual_nfs_servers": {s["uuid"]: s for s in servers}}

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        existing = self.handler.read_dict(uuid)
        old_name = existing.get("name")
        old_parent = existing.get("parent")
        server_uuid = existing.get("uuid")
        data["modified_at"] = datetime.now(timezone.utc).isoformat()
        if not data.get("uuid"):
            data["uuid"] = server_uuid
        new_name = data.get("name")
        if new_name:
            data["parent"] = self.handler.get_cache_parent_for_head(data["uuid"] or "", new_name)
        try:
            self.server_manager.remove_server(old_name or "", server_uuid or "")
        except Exception as e:
            logger.warning(f"Could not stop old runtime server: {e}")

        from skillberry_store.schemas.vnfs_schema import VnfsSchema
        vnfs_obj = VnfsSchema(**{k: v for k, v in data.items() if k in VnfsSchema.model_fields})
        server = self.server_manager.add_server(vnfs_obj)
        data["port"] = server.port

        self.handler.write_dict(data["uuid"] or "", data)
        if new_name and old_name:
            self.handler.update_cache(data["uuid"] or "", new_name=new_name, old_name=old_name, old_parent=old_parent)
        if self.descriptions and data.get("description") and data.get("uuid"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"vNFS server '{new_name}' updated on port {server.port}")
        return data

    def delete(self, uuid_or_name: str) -> None:
        uuid = self._resolve_uuid(uuid_or_name)
        d = self.handler.read_dict(uuid)
        name = d.get("name")
        parent = d.get("parent")
        try:
            self.server_manager.remove_server(name or "", uuid or "")
        except Exception as e:
            logger.warning(f"Could not stop runtime server: {e}")
        if name and uuid:
            self.handler.update_cache(uuid, new_name=None, old_name=name, old_parent=parent)
        self.handler.delete_object(uuid)
        if self.descriptions:
            try:
                self.descriptions.delete_description(uuid)
            except Exception as e:
                logger.warning(f"Could not delete vnfs description for {uuid}: {e}")
        logger.info(f"vNFS server '{uuid_or_name}' deleted")
```

- [ ] **Step 4: Run service tests**

```bash
pytest src/skillberry_store/tests/services/test_vnfs_service.py -v
```
Expected: all PASS.

- [ ] **Step 5: Refactor vnfs_api.py**

Replace the full content of `src/skillberry_store/fast_api/vnfs_api.py` with:

```python
"""Virtual NFS Server API endpoints for the Skillberry Store service."""

import logging
from typing import Annotated, Optional
from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import Counter
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager
from skillberry_store.schemas.vnfs_schema import VnfsSchema
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.services.vnfs_service import VnfsService

logger = logging.getLogger(__name__)

prom_prefix = "sts_fastapi_vnfs_"
create_vnfs_counter = Counter(f"{prom_prefix}create_counter", "vNFS create operations")
list_vnfs_counter = Counter(f"{prom_prefix}list_counter", "vNFS list operations")
get_vnfs_counter = Counter(f"{prom_prefix}get_counter", "vNFS get operations")
delete_vnfs_counter = Counter(f"{prom_prefix}delete_counter", "vNFS delete operations")
update_vnfs_counter = Counter(f"{prom_prefix}update_counter", "vNFS update operations")
search_vnfs_counter = Counter(f"{prom_prefix}search_counter", "vNFS search operations")


def register_vnfs_api(
    app: FastAPI,
    sts_url: str,
    tags: str = "vnfs_servers",
    vnfs_descriptions: Optional[Description] = None,
    service: Optional[VnfsService] = None,
):
    if service is None:
        from skillberry_store.modules.object_handler import get_object_handler
        vnfs_handler = get_object_handler("vnfs")
        server_manager = VirtualNfsServerManager(sts_url=sts_url, app=app)
        service = VnfsService(vnfs_handler, server_manager, vnfs_descriptions)
    app.state.vnfs_server_manager = service.server_manager

    @app.post("/vnfs_servers/", tags=[tags], openapi_extra={"x-cli-name": "create-vnfs-server"})
    def create_vnfs_server(vnfs: Annotated[VnfsSchema, Query()], request: Request):
        logger.info(f"Request to create vnfs server: {vnfs.name}")
        create_vnfs_counter.inc()
        try:
            result = service.create(vnfs.to_dict())
            return {"message": f"vNFS server '{result['name']}' created successfully.", "name": result["name"], "uuid": result["uuid"], "port": result["port"]}
        except ValueError as e:
            status = 409 if "already exists" in str(e) or "not available" in str(e) else 500
            raise HTTPException(status_code=status, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating vnfs server '{vnfs.name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error creating vNFS server: {str(e)}")

    @app.get("/vnfs_servers/", tags=[tags], openapi_extra={"x-cli-name": "list-vnfs-servers"})
    def list_vnfs_servers():
        logger.info("Request to list vnfs servers")
        list_vnfs_counter.inc()
        try:
            return service.list_all()
        except Exception as e:
            logger.error(f"Error listing vnfs servers: {e}")
            raise HTTPException(status_code=500, detail=f"Error listing vNFS servers: {str(e)}")

    @app.get("/vnfs_servers/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "get-vnfs-server"})
    def get_vnfs_server(uuid_or_name: str):
        logger.info(f"Request to get vnfs server: {uuid_or_name}")
        get_vnfs_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving vnfs server '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving vNFS server: {str(e)}")

    @app.delete("/vnfs_servers/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "delete-vnfs-server"})
    def delete_vnfs_server(uuid_or_name: str):
        logger.info(f"Request to delete vnfs server: {uuid_or_name}")
        delete_vnfs_counter.inc()
        try:
            service.delete(uuid_or_name)
            return {"message": f"vNFS server '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting vnfs server '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting vNFS server: {str(e)}")

    @app.put("/vnfs_servers/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "update-vnfs-server"})
    def update_vnfs_server(uuid_or_name: str, vnfs: Annotated[VnfsSchema, Query()], request: Request):
        logger.info(f"Request to update vnfs server: {uuid_or_name}")
        update_vnfs_counter.inc()
        try:
            result = service.update(uuid_or_name, vnfs.to_dict())
            return {"message": f"vNFS server '{result.get('name')}' updated successfully.", "port": result["port"]}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating vnfs server '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error updating vNFS server: {str(e)}")

    @app.get("/search/vnfs_servers", tags=[tags], openapi_extra={"x-cli-name": "search-vnfs-servers"})
    def search_vnfs_servers(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        logger.info(f"Request to search vnfs servers for: {search_term}")
        search_vnfs_counter.inc()
        if not vnfs_descriptions:
            raise HTTPException(status_code=503, detail="vNFS search is not available")
        try:
            matched = vnfs_descriptions.search_description(search_term=search_term, k=max_number_of_results)
            filtered = [m for m in matched if float(m["similarity_score"]) <= similarity_threshold]
            to_filter = []
            for m in filtered:
                name = m.get("filename") or m.get("name")
                if not name:
                    continue
                try:
                    d = service.get(name)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    to_filter.append(d)
                except Exception:
                    pass
            result_items = apply_search_filters(to_filter, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
            result_items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [{"filename": s.get("name", ""), "similarity_score": s.get("similarity_score", 0.0)} for s in result_items if s.get("name")]
        except Exception as e:
            logger.error(f"Error searching vnfs servers: {e}")
            raise HTTPException(status_code=500, detail=f"Error searching vNFS servers: {str(e)}")
```

- [ ] **Step 6: Run full test suite**

```bash
pytest src/skillberry_store/tests/ -v -m "not integration" 2>&1 | tail -20
```

- [ ] **Step 7: Commit**

```bash
git add src/skillberry_store/services/vnfs_service.py \
        src/skillberry_store/tests/services/test_vnfs_service.py \
        src/skillberry_store/fast_api/vnfs_api.py
git commit -m "feat: extract VnfsService and refactor vnfs_api to thin wrapper"
```

---

## Task 5: VmcpService

**Files:**
- Create: `src/skillberry_store/services/vmcp_service.py`
- Create: `src/skillberry_store/tests/services/test_vmcp_service.py`
- Modify: `src/skillberry_store/fast_api/vmcp_api.py`

- [ ] **Step 1: Write failing tests**

Create `src/skillberry_store/tests/services/test_vmcp_service.py`:

```python
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from skillberry_store.services.vmcp_service import VmcpService


def _handler(exists=False):
    h = MagicMock()
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = None
    h.resolve_to_uuid_or_error.return_value = "eeee-5555"
    h.read_dict.return_value = {
        "uuid": "eeee-5555", "name": "vm1", "port": 8100,
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
        "skill_uuid": None,
    }
    h.list_all_dicts.return_value = [{"uuid": "eeee-5555", "name": "vm1", "port": 8100, "modified_at": "2024-02-01"}]
    return h


def _manager():
    m = MagicMock()
    runtime = MagicMock()
    runtime.port = 8100
    runtime.name = "vm1"
    runtime.description = ""
    runtime.tool_uuids = []
    m.add_server.return_value = runtime
    m.get_server.return_value = runtime
    m.get_server_details.return_value = {"port": 8100}
    return m


def test_create_returns_dict_with_port():
    skills_h = MagicMock()
    svc = VmcpService(_handler(), _manager(), skills_handler=skills_h)
    result = svc.create({"name": "vm1", "uuid": None}, env_id="")
    assert "uuid" in result
    assert result["port"] == 8100


def test_create_raises_on_duplicate():
    svc = VmcpService(_handler(exists=True), _manager(), skills_handler=MagicMock())
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "vm1", "uuid": None}, env_id="")


def test_list_includes_running_status():
    svc = VmcpService(_handler(), _manager(), skills_handler=MagicMock())
    result = svc.list_all()
    assert "virtual_mcp_servers" in result


def test_delete_stops_runtime_and_removes_persistent():
    h = _handler()
    mgr = _manager()
    svc = VmcpService(h, mgr, skills_handler=MagicMock())
    svc.delete("vm1")
    mgr.remove_server.assert_called_once()
    h.delete_object.assert_called_once()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest src/skillberry_store/tests/services/test_vmcp_service.py -v 2>&1 | head -10
```

- [ ] **Step 3: Implement VmcpService**

Create `src/skillberry_store/services/vmcp_service.py`:

```python
"""Business logic for virtual MCP server CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.modules.description import Description
from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager
from skillberry_store.utils.utils import generate_or_validate_uuid

logger = logging.getLogger(__name__)


class VmcpService:
    def __init__(
        self,
        handler: ObjectHandler,
        server_manager: VirtualMcpServerManager,
        skills_handler: ObjectHandler,
        descriptions: Optional[Description] = None,
    ):
        self.handler = handler
        self.server_manager = server_manager
        self.skills_handler = skills_handler
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"VMCP server '{uuid_or_name}' not found")
            raise

    def _resolve_skill_uuids(self, skill_uuid: Optional[str]):
        tool_uuids, snippet_uuids = [], []
        if not skill_uuid:
            return tool_uuids, snippet_uuids
        try:
            skill = self.skills_handler.read_dict(skill_uuid)
            tool_uuids = skill.get("tool_uuids", [])
            snippet_uuids = skill.get("snippet_uuids", [])
        except Exception as e:
            logger.warning(f"Error loading skill {skill_uuid}: {e}")
        return tool_uuids, snippet_uuids

    def create(self, data: Dict[str, Any], env_id: str = "") -> Dict[str, Any]:
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"VMCP server with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(data["uuid"], data["name"])
        tool_uuids, snippet_uuids = self._resolve_skill_uuids(data.get("skill_uuid"))
        server = self.server_manager.add_server(
            name=data.get("name") or "",
            uuid=data["uuid"],
            description=data.get("description") or "",
            port=data.get("port"),
            tools=tool_uuids,
            snippets=snippet_uuids,
            env_id=env_id,
        )
        data["port"] = server.port
        self.handler.write_dict(data["uuid"], data)
        if data.get("name"):
            self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"VMCP server '{data.get('name')}' created on port {server.port}")
        return data

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        d = self.handler.read_dict(uuid)
        try:
            runtime_details = self.server_manager.get_server_details(d.get("name", ""), d.get("uuid", ""))
            d["runtime"] = runtime_details
            d["running"] = True
        except Exception:
            d["running"] = False
            d["runtime"] = None
        return d

    def list_all(self) -> Dict[str, Any]:
        items = self.handler.list_all_dicts()
        servers = []
        for item in items:
            try:
                runtime = None
                try:
                    runtime = self.server_manager.get_server(item.get("name", ""), item.get("uuid", ""))
                except Exception:
                    pass
                info = {
                    "uuid": item.get("uuid"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "version": item.get("version"),
                    "state": item.get("state"),
                    "tags": item.get("tags", []),
                    "port": item.get("port"),
                    "skill_uuid": item.get("skill_uuid"),
                    "modified_at": item.get("modified_at", ""),
                    "running": runtime is not None,
                    "runtime": {"name": runtime.name, "description": runtime.description, "port": runtime.port, "tools": runtime.tool_uuids} if runtime else None,
                }
                servers.append(info)
            except Exception as e:
                logger.warning(f"Error loading vmcp server '{item.get('name')}': {e}")
        servers.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return {"virtual_mcp_servers": {s["uuid"]: s for s in servers}}

    def update(self, uuid_or_name: str, data: Dict[str, Any], env_id: str = "") -> Dict[str, Any]:
        uuid = self._resolve_uuid(uuid_or_name)
        existing = self.handler.read_dict(uuid)
        old_name = existing.get("name")
        old_parent = existing.get("parent")
        server_uuid = existing.get("uuid")
        data["modified_at"] = datetime.now(timezone.utc).isoformat()
        if not data.get("uuid"):
            data["uuid"] = server_uuid
        new_name = data.get("name")
        if new_name:
            data["parent"] = self.handler.get_cache_parent_for_head(data["uuid"] or "", new_name)
        try:
            self.server_manager.remove_server(old_name or "", server_uuid or "")
        except Exception as e:
            logger.warning(f"Could not stop old runtime server: {e}")
        tool_uuids, snippet_uuids = self._resolve_skill_uuids(data.get("skill_uuid"))
        server = self.server_manager.add_server(
            name=new_name or "",
            uuid=data["uuid"] or "",
            description=data.get("description") or "",
            port=data.get("port"),
            tools=tool_uuids,
            snippets=snippet_uuids,
            env_id=env_id,
        )
        data["port"] = server.port
        self.handler.write_dict(data["uuid"] or "", data)
        if new_name and old_name:
            self.handler.update_cache(data["uuid"] or "", new_name=new_name, old_name=old_name, old_parent=old_parent)
        if self.descriptions and data.get("description") and data.get("uuid"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"VMCP server '{new_name}' updated on port {server.port}")
        return data

    def delete(self, uuid_or_name: str) -> None:
        uuid = self._resolve_uuid(uuid_or_name)
        d = self.handler.read_dict(uuid)
        name = d.get("name")
        parent = d.get("parent")
        try:
            self.server_manager.remove_server(name or "", uuid or "")
        except Exception as e:
            logger.warning(f"Could not stop runtime server: {e}")
        if name and uuid:
            self.handler.update_cache(uuid, new_name=None, old_name=name, old_parent=parent)
        self.handler.delete_object(uuid)
        if self.descriptions:
            try:
                self.descriptions.delete_description(uuid)
            except Exception as e:
                logger.warning(f"Could not delete vmcp description for {uuid}: {e}")
        logger.info(f"VMCP server '{uuid_or_name}' deleted")
```

- [ ] **Step 4: Run service tests**

```bash
pytest src/skillberry_store/tests/services/test_vmcp_service.py -v
```
Expected: all PASS.

- [ ] **Step 5: Refactor vmcp_api.py**

Replace the full content of `src/skillberry_store/fast_api/vmcp_api.py` with:

```python
"""Virtual MCP Server API endpoints for the Skillberry Store service."""

import logging
from typing import Annotated, Optional
from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import Counter, Histogram
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager
from skillberry_store.schemas.vmcp_schema import VmcpSchema
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys
from skillberry_store.services.vmcp_service import VmcpService

logger = logging.getLogger(__name__)

prom_prefix = "sts_fastapi_vmcp_"
create_vmcp_counter = Counter(f"{prom_prefix}create_vmcp_counter", "Count number of vmcp create operations")
list_vmcp_counter = Counter(f"{prom_prefix}list_vmcp_counter", "Count number of vmcp list operations")
get_vmcp_counter = Counter(f"{prom_prefix}get_vmcp_counter", "Count number of vmcp get operations")
delete_vmcp_counter = Counter(f"{prom_prefix}delete_vmcp_counter", "Count number of vmcp delete operations")
update_vmcp_counter = Counter(f"{prom_prefix}update_vmcp_counter", "Count number of vmcp update operations")
search_vmcp_counter = Counter(f"{prom_prefix}search_vmcp_counter", "Count number of vmcp search operations")
invoke_vmcp_tool_counter = Counter(f"{prom_prefix}invoke_vmcp_tool_counter", "Count number of vmcp tool invoke operations", ["server_name", "tool_name"])
invoke_successfully_vmcp_tool_counter = Counter(f"{prom_prefix}invoke_successfully_vmcp_tool_counter", "Count number of vmcp tool invoked successfully operations", ["server_name", "tool_name"])
invoke_successfully_vmcp_tool_latency = Histogram(f"{prom_prefix}invoke_successfully_vmcp_tool_latency", "Histogram of invoke vmcp tool successfully latencies", ["server_name", "tool_name"])


def register_vmcp_api(
    app: FastAPI,
    sts_url: str,
    tags: str = "vmcp_servers",
    vmcp_descriptions: Optional[Description] = None,
    service: Optional[VmcpService] = None,
):
    if service is None:
        from skillberry_store.modules.object_handler import get_object_handler
        vmcp_handler = get_object_handler("vmcp")
        skills_handler = get_object_handler("skill")
        server_manager = VirtualMcpServerManager(sts_url=sts_url, app=app)
        service = VmcpService(vmcp_handler, server_manager, skills_handler, vmcp_descriptions)
    app.state.vmcp_server_manager = service.server_manager

    def _extract_env_id(request: Request) -> str:
        ctx = unflatten_keys(dict(request.headers)).get(SKILLBERRY_CONTEXT.lower())
        return ctx.get("env_id") if ctx else ""

    @app.post("/vmcp_servers/", tags=[tags], openapi_extra={"x-cli-name": "create-vmcp-server"})
    def create_vmcp_server(vmcp: Annotated[VmcpSchema, Query()], request: Request):
        logger.info(f"Request to create vmcp server: {vmcp.name}")
        create_vmcp_counter.inc()
        try:
            result = service.create(vmcp.to_dict(), env_id=_extract_env_id(request))
            return {"message": f"VMCP server '{result['name']}' created successfully.", "name": result["name"], "uuid": result["uuid"], "port": result["port"]}
        except ValueError as e:
            error_msg = str(e)
            if "already exists" in error_msg or "port" in error_msg.lower():
                raise HTTPException(status_code=409, detail=error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        except Exception as e:
            logger.error(f"Error creating vmcp server '{vmcp.name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error creating vmcp server: {str(e)}")

    @app.get("/vmcp_servers/", tags=[tags], openapi_extra={"x-cli-name": "list-vmcp-servers"})
    def list_vmcp_servers():
        logger.info("Request to list vmcp servers")
        list_vmcp_counter.inc()
        try:
            return service.list_all()
        except Exception as e:
            logger.error(f"Error listing vmcp servers: {e}")
            raise HTTPException(status_code=500, detail=f"Error listing vmcp servers: {str(e)}")

    @app.get("/vmcp_servers/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "get-vmcp-server"})
    def get_vmcp_server(uuid_or_name: str):
        logger.info(f"Request to get vmcp server: {uuid_or_name}")
        get_vmcp_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving vmcp server: {str(e)}")

    @app.delete("/vmcp_servers/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "delete-vmcp-server"})
    def delete_vmcp_server(uuid_or_name: str):
        logger.info(f"Request to delete vmcp server: {uuid_or_name}")
        delete_vmcp_counter.inc()
        try:
            service.delete(uuid_or_name)
            return {"message": f"VMCP server '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting vmcp server: {str(e)}")

    @app.put("/vmcp_servers/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "update-vmcp-server"})
    def update_vmcp_server(uuid_or_name: str, vmcp: Annotated[VmcpSchema, Query()], request: Request):
        logger.info(f"Request to update vmcp server: {uuid_or_name}")
        update_vmcp_counter.inc()
        try:
            result = service.update(uuid_or_name, vmcp.to_dict(), env_id=_extract_env_id(request))
            return {"message": f"VMCP server '{result.get('name')}' updated successfully.", "port": result["port"]}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error updating vmcp server: {str(e)}")

    @app.get("/search/vmcp_servers", tags=[tags], openapi_extra={"x-cli-name": "search-vmcp-servers"})
    def search_vmcp_servers(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        logger.info(f"Request to search vmcp servers for: {search_term}")
        search_vmcp_counter.inc()
        if not vmcp_descriptions:
            raise HTTPException(status_code=503, detail="VMCP search is not available")
        try:
            matched = vmcp_descriptions.search_description(search_term=search_term, k=max_number_of_results)
            filtered = [m for m in matched if float(m["similarity_score"]) <= similarity_threshold]
            to_filter = []
            for m in filtered:
                name = m.get("filename") or m.get("name")
                if not name:
                    continue
                try:
                    d = service.get(name)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    to_filter.append(d)
                except Exception:
                    pass
            result_items = apply_search_filters(to_filter, manifest_filter=manifest_filter, lifecycle_state=lifecycle_state)
            result_items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [{"filename": s.get("name", ""), "similarity_score": s.get("similarity_score", 0.0)} for s in result_items if s.get("name")]
        except Exception as e:
            logger.error(f"Error searching vmcp servers: {e}")
            raise HTTPException(status_code=500, detail=f"Error searching vmcp servers: {str(e)}")
```

- [ ] **Step 6: Run full test suite**

```bash
pytest src/skillberry_store/tests/ -v -m "not integration" 2>&1 | tail -20
```

- [ ] **Step 7: Commit**

```bash
git add src/skillberry_store/services/vmcp_service.py \
        src/skillberry_store/tests/services/test_vmcp_service.py \
        src/skillberry_store/fast_api/vmcp_api.py
git commit -m "feat: extract VmcpService and refactor vmcp_api to thin wrapper"
```

---

## Task 6: Refactor StoreAPI to proxy

**Files:**
- Modify: `src/skillberry_store/plugins/store_api.py`

- [ ] **Step 1: Replace store_api.py**

Replace the full content of `src/skillberry_store/plugins/store_api.py` with:

```python
"""Store API for plugin access to content.

Thin proxy that delegates to service layer. Provides a stable interface
for plugins without exposing internal implementation details.
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class StoreAPI:
    """Plugin interface — delegates to service layer."""

    def __init__(self, services: Dict[str, Any]):
        self.tools_service = services.get("tools")
        self.skills_service = services.get("skills")
        self.snippets_service = services.get("snippets")
        self.vnfs_service = services.get("vnfs")
        self.vmcp_service = services.get("vmcp")

    # ── Tools ──────────────────────────────────────────────────────────────

    def get_tool(self, uuid: str) -> Optional[Dict[str, Any]]:
        if not self.tools_service:
            return None
        try:
            return self.tools_service.get(uuid)
        except KeyError:
            return None

    def list_tools(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        if not self.tools_service:
            return []
        return self.tools_service.list_all(filter_criteria)

    def update_tool_tags(self, uuid: str, tags: List[str]) -> bool:
        if not self.tools_service:
            return False
        try:
            tool = self.tools_service.get(uuid)
        except KeyError:
            return False
        existing = set(tool.get("tags", []))
        tool["tags"] = list(existing.union(set(tags)))
        try:
            self.tools_service.handler.write_dict(uuid, tool)
            return True
        except Exception as e:
            logger.error(f"Failed to update tool tags for {uuid}: {e}")
            return False

    def update_tool_metadata(self, uuid: str, metadata: Dict[str, Any]) -> bool:
        if not self.tools_service:
            return False
        try:
            tool = self.tools_service.get(uuid)
        except KeyError:
            return False
        if "extra" not in tool:
            tool["extra"] = {}
        tool["extra"].update(metadata)
        try:
            self.tools_service.handler.write_dict(uuid, tool)
            return True
        except Exception as e:
            logger.error(f"Failed to update tool metadata for {uuid}: {e}")
            return False

    # ── Skills ─────────────────────────────────────────────────────────────

    def get_skill(self, uuid: str) -> Optional[Dict[str, Any]]:
        if not self.skills_service:
            return None
        try:
            return self.skills_service.get(uuid)
        except KeyError:
            return None

    def list_skills(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        if not self.skills_service:
            return []
        return self.skills_service.list_all(filter_criteria)

    def update_skill_tags(self, uuid: str, tags: List[str]) -> bool:
        if not self.skills_service:
            return False
        try:
            skill = self.skills_service.get(uuid)
        except KeyError:
            return False
        existing = set(skill.get("tags", []))
        skill["tags"] = list(existing.union(set(tags)))
        try:
            self.skills_service.handler.write_dict(uuid, skill)
            return True
        except Exception as e:
            logger.error(f"Failed to update skill tags for {uuid}: {e}")
            return False

    def update_skill_metadata(self, uuid: str, metadata: Dict[str, Any]) -> bool:
        if not self.skills_service:
            return False
        try:
            skill = self.skills_service.get(uuid)
        except KeyError:
            return False
        if "extra" not in skill or not isinstance(skill.get("extra"), dict):
            skill["extra"] = {}
        skill["extra"].update(metadata)
        try:
            self.skills_service.handler.write_dict(uuid, skill)
            return True
        except Exception as e:
            logger.error(f"Failed to update skill metadata for {uuid}: {e}")
            return False

    # ── Snippets ───────────────────────────────────────────────────────────

    def get_snippet(self, uuid: str) -> Optional[Dict[str, Any]]:
        if not self.snippets_service:
            return None
        try:
            return self.snippets_service.get(uuid)
        except KeyError:
            return None

    def list_snippets(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        if not self.snippets_service:
            return []
        return self.snippets_service.list_all(filter_criteria)

    def create_snippet(self, snippet_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.snippets_service:
            raise RuntimeError("Snippets service not available")
        return self.snippets_service.create(snippet_data)

    def update_snippet_tags(self, uuid: str, tags: List[str]) -> bool:
        if not self.snippets_service:
            return False
        try:
            snippet = self.snippets_service.get(uuid)
        except KeyError:
            return False
        existing = set(snippet.get("tags", []))
        snippet["tags"] = list(existing.union(set(tags)))
        try:
            self.snippets_service.handler.write_dict(uuid, snippet)
            return True
        except Exception as e:
            logger.error(f"Failed to update snippet tags for {uuid}: {e}")
            return False

    def _matches_filter(self, item: Dict[str, Any], filter_criteria: Dict) -> bool:
        return all(item.get(k) == v for k, v in filter_criteria.items())

# Made with Bob
```

- [ ] **Step 2: Run full test suite**

```bash
pytest src/skillberry_store/tests/ -v -m "not integration" 2>&1 | tail -20
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add src/skillberry_store/plugins/store_api.py
git commit -m "refactor: StoreAPI becomes thin proxy to service layer"
```

---

## Task 7: Wire services in server.py

**Files:**
- Modify: `src/skillberry_store/fast_api/server.py`

- [ ] **Step 1: Update SBS.__init__ to instantiate services and inject them**

In `src/skillberry_store/fast_api/server.py`, replace the plugin initialization block and the `register_*_api` calls with:

```python
        # Initialize services
        from skillberry_store.modules.object_handler import get_object_handler
        from skillberry_store.services.tools_service import ToolsService
        from skillberry_store.services.skills_service import SkillsService
        from skillberry_store.services.snippets_service import SnippetsService
        from skillberry_store.services.vnfs_service import VnfsService
        from skillberry_store.services.vmcp_service import VmcpService
        from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager
        from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager

        tools_service = ToolsService(get_object_handler("tool"), self.state.tools_descriptions)
        skills_service = SkillsService(
            handler=get_object_handler("skill"),
            tools_handler=get_object_handler("tool"),
            snippets_handler=get_object_handler("snippet"),
            descriptions=self.state.skills_descriptions,
        )
        snippets_service = SnippetsService(get_object_handler("snippet"), self.state.snippets_descriptions)
        vnfs_server_manager = VirtualNfsServerManager(sts_url=sts_url, app=self)
        vnfs_service = VnfsService(get_object_handler("vnfs"), vnfs_server_manager, self.state.vnfs_descriptions)
        vmcp_server_manager = VirtualMcpServerManager(sts_url=sts_url, app=self)
        vmcp_service = VmcpService(
            get_object_handler("vmcp"), vmcp_server_manager,
            get_object_handler("skill"), self.state.vmcp_descriptions,
        )

        # Initialize plugin system
        from skillberry_store.plugins.loader import PluginLoader
        from skillberry_store.plugins.store_api import StoreAPI

        store_api = StoreAPI({
            "tools": tools_service,
            "skills": skills_service,
            "snippets": snippets_service,
            "vnfs": vnfs_service,
            "vmcp": vmcp_service,
        })

        plugin_loader = PluginLoader(store_api=store_api)
        discovered = plugin_loader.discover_plugins()
        logger.info(f"Discovered {len(discovered)} plugins: {discovered}")
        self.state.plugin_loader = plugin_loader

        register_vmcp_api(self, sts_url=sts_url, tags="vmcp_servers", vmcp_descriptions=self.state.vmcp_descriptions, service=vmcp_service)
        register_vnfs_api(self, sts_url=sts_url, tags="vnfs_servers", vnfs_descriptions=self.state.vnfs_descriptions, service=vnfs_service)
        register_skills_api(self, tags="skills", skills_descriptions=self.state.skills_descriptions, service=skills_service)
        register_snippets_api(self, tags="snippets", snippets_descriptions=self.state.snippets_descriptions, service=snippets_service)
        register_tools_api(self, tags="tools", tools_descriptions=self.state.tools_descriptions, service=tools_service)
        register_admin_api(self, tags="admin")
        register_plugins_api(self, plugin_loader=plugin_loader, tags="plugins")
```

Also remove the now-unused local imports inside `__init__` that were for `get_object_handler` and `StoreAPI` (they are now at the service level above).

- [ ] **Step 2: Run full test suite**

```bash
pytest src/skillberry_store/tests/ -v -m "not integration" 2>&1 | tail -30
```
Expected: all pass.

- [ ] **Step 3: Run all service tests explicitly**

```bash
pytest src/skillberry_store/tests/services/ -v
```
Expected: all 5 service test files pass.

- [ ] **Step 4: Commit**

```bash
git add src/skillberry_store/fast_api/server.py
git commit -m "feat: wire service instances in server.py and share with StoreAPI"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Five service files (one per content API): Tasks 1–5
- ✅ FastAPI handlers become thin wrappers: Tasks 1–5, steps 6
- ✅ StoreAPI becomes proxy: Task 6
- ✅ server.py wiring: Task 7
- ✅ Service-level unit tests: Tasks 1–5, step 1/2
- ✅ Existing tests unchanged (only run, not modified): all tasks step 6/7
- ✅ `populate_objects` moves to SkillsService: Task 2
- ✅ Server lifecycle (vnfs/vmcp start/stop) moves to service: Tasks 4–5
- ✅ HTTP concerns (counters, emit events, HTTPException) stay in API: Tasks 1–5

**Placeholder scan:** None found.

**Type consistency:**
- `SnippetsService.create(data: Dict) -> Dict` used consistently in snippets_api and store_api
- `SkillsService(handler, tools_handler, snippets_handler, descriptions)` — same constructor signature in Task 2 step 3 and Task 7 step 1 ✅
- `VnfsService.list_all()` returns `Dict` (not `List`) to match the original `{"virtual_nfs_servers": ...}` shape ✅
- `VmcpService.list_all()` returns `Dict` with `"virtual_mcp_servers"` key ✅
- `VmcpService(handler, server_manager, skills_handler, descriptions)` — consistent ✅
