from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from skillberry_store.fast_api.vnfs_api import register_vnfs_api


def _app(servers):
    app = FastAPI()
    svc = MagicMock()
    svc.list_all.return_value = {"virtual_nfs_servers": {s["uuid"]: s for s in servers}}
    register_vnfs_api(app, sts_url="http://test", service=svc)
    return TestClient(app)


SERVERS = [
    {
        "uuid": "v1",
        "name": "a",
        "skill_uuid": "sk1",
        "tags": [],
        "port": 9001,
        "description": None,
        "version": None,
        "state": None,
        "modified_at": "",
    },
    {
        "uuid": "v2",
        "name": "b",
        "skill_uuid": "sk2",
        "tags": [],
        "port": 9002,
        "description": None,
        "version": None,
        "state": None,
        "modified_at": "",
    },
]


def test_list_vnfs_servers_no_filter_returns_all():
    client = _app(SERVERS)
    resp = client.get("/vnfs_servers/")
    assert resp.status_code == 200
    assert len(resp.json()["virtual_nfs_servers"]) == 2


def test_list_vnfs_servers_skill_uuid_filter():
    client = _app(SERVERS)
    resp = client.get("/vnfs_servers/?skill_uuid=sk1")
    assert resp.status_code == 200
    uuids = list(resp.json()["virtual_nfs_servers"].keys())
    assert uuids == ["v1"]


def test_list_vnfs_servers_skill_uuid_no_match_returns_empty():
    client = _app(SERVERS)
    resp = client.get("/vnfs_servers/?skill_uuid=unknown")
    assert resp.status_code == 200
    assert resp.json()["virtual_nfs_servers"] == {}
