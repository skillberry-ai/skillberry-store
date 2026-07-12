from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from skillberry_store.fast_api.vmcp_api import register_vmcp_api

def _app(servers):
    app = FastAPI()
    svc = MagicMock()

    # Phase 3 (vmcp/vnfs): ``list_all`` now returns a bare list (or an
    # envelope when paginated). The other new query params (fields / search
    # / tags / state / sort / limit / offset) are accepted but ignored by
    # this mock — the tests only exercise the ``skill_uuid`` code path.
    def _list_all(
        skill_uuid=None,
        fields=None,
        search=None,
        tags=None,
        state=None,
        sort=None,
        limit=None,
        offset=None,
    ):
        matches = servers if skill_uuid is None else [
            s for s in servers if s.get("skill_uuid") == skill_uuid
        ]
        if limit is None and offset is None:
            return list(matches)
        return {
            "items": list(matches),
            "total": len(matches),
            "offset": offset or 0,
            "limit": limit,
        }

    svc.list_all.side_effect = _list_all
    register_vmcp_api(app, service=svc)
    return TestClient(app)

SERVERS = [
    {"uuid": "v1", "name": "a", "skill_uuid": "sk1", "tags": [], "port": 9001,
     "description": None, "version": None, "state": None, "modified_at": ""},
    {"uuid": "v2", "name": "b", "skill_uuid": "sk2", "tags": [], "port": 9002,
     "description": None, "version": None, "state": None, "modified_at": ""},
]

def test_list_vmcp_servers_no_filter_returns_all():
    client = _app(SERVERS)
    resp = client.get("/vmcp_servers/")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2

def test_list_vmcp_servers_skill_uuid_filter():
    client = _app(SERVERS)
    resp = client.get("/vmcp_servers/?skill_uuid=sk1")
    assert resp.status_code == 200
    body = resp.json()
    uuids = [s["uuid"] for s in body]
    assert uuids == ["v1"]

def test_list_vmcp_servers_skill_uuid_no_match_returns_empty():
    client = _app(SERVERS)
    resp = client.get("/vmcp_servers/?skill_uuid=unknown")
    assert resp.status_code == 200
    assert resp.json() == []
