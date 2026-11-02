"""A fake rossoctl backend: the ``/api/v1/tools`` endpoints the plugin calls,
plus a Keycloak-style token endpoint, with recorded responses.

Shapes follow rossoctl ``routers/tools.py`` (``get_tool``, ``connect_to_tool``,
``invoke_tool``) and ``models/responses.py`` (``ToolListResponse``). Every
request is recorded with its host, so tests can assert the plugin contacted
nothing else.
"""

import json
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, Form, Header, HTTPException, Request

BACKEND = "http://rossoctl-backend.test"
TOKEN_URL = "http://keycloak.test/realms/rossoctl/protocol/openid-connect/token"

WEATHER_SCHEMA = {
    "type": "object",
    "properties": {"city": {"type": "string", "title": "City"}},
    "required": ["city"],
}
SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": "string"},
        "cuisine": {"type": "string"},
        "party_size": {"type": "integer"},
    },
    "required": ["city"],
}
BOOK_SCHEMA = {
    "type": "object",
    "properties": {
        "restaurant_id": {"type": "string"},
        "date_time": {"type": "string"},
        "party_size": {"type": "integer"},
        "name": {"type": "string"},
        "phone": {"type": "string"},
        "email": {"type": "string"},
    },
    "required": ["restaurant_id", "date_time", "party_size", "name", "phone", "email"],
}


class FakeRossoctl:
    def __init__(self, require_auth: bool = True):
        self.require_auth = require_auth
        self.requests: List[Dict[str, Any]] = []
        self.tokens_issued = 0
        self.valid_tokens = set()
        self.reject_next_with_401 = False
        self.tools: Dict[str, Dict[str, Any]] = {
            "team1/weather-tool": {
                "port": 8000,
                "mcp": [
                    {
                        "name": "get_weather",
                        "description": "Get current weather for a city.",
                        "input_schema": WEATHER_SCHEMA,
                        "annotations": {"readOnlyHint": True},
                    }
                ],
            },
            "team1/reservation-tool": {
                "port": 8000,
                "mcp": [
                    {
                        "name": "search_restaurants",
                        "description": "Search restaurants.",
                        "input_schema": SEARCH_SCHEMA,
                    },
                    {
                        "name": "place_reservation",
                        "description": "Book a table.",
                        "input_schema": BOOK_SCHEMA,
                    },
                ],
            },
            "team1/other-search": {
                "port": 9090,
                "mcp": [
                    {
                        "name": "search_restaurants",
                        "description": "Another search.",
                        "input_schema": SEARCH_SCHEMA,
                    }
                ],
            },
            "team1/unreachable-tool": {"port": 8000, "mcp": None},
        }
        self.app = self._build()

    # A transport that serves both hosts and records every request.
    def transport(self) -> httpx.AsyncBaseTransport:
        inner = httpx.ASGITransport(app=self.app)
        fake = self

        class Recording(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                fake.requests.append(
                    {
                        "host": request.url.host,
                        "method": request.method,
                        "path": request.url.path,
                        "auth": request.headers.get("authorization"),
                    }
                )
                if request.url.host not in ("rossoctl-backend.test", "keycloak.test"):
                    raise httpx.ConnectError(f"unexpected host {request.url.host}")
                return await inner.handle_async_request(request)

        return Recording()

    def _check_auth(self, authorization):
        if not self.require_auth:
            return
        if self.reject_next_with_401:
            self.reject_next_with_401 = False
            raise HTTPException(status_code=401, detail="token expired")
        token = (authorization or "")[7:]
        if token not in self.valid_tokens:
            raise HTTPException(status_code=401, detail="missing or invalid token")

    def _tool(self, ns, name):
        tool = self.tools.get(f"{ns}/{name}")
        if tool is None:
            raise HTTPException(
                status_code=404, detail=f"Tool '{name}' not found in namespace '{ns}'"
            )
        return tool

    def _build(self) -> FastAPI:
        app = FastAPI()
        fake = self
        # Requests that arrive over a real socket (proxy tools run with urllib),
        # recorded like the transport records the plugin's own calls.
        self.http_requests: List[Dict[str, Any]] = []

        @app.middleware("http")
        async def record(request, call_next):
            fake.http_requests.append(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "auth": request.headers.get("authorization"),
                }
            )
            return await call_next(request)

        @app.post("/realms/rossoctl/protocol/openid-connect/token")
        async def token(
            grant_type: str = Form(...),
            client_id: str = Form(...),
            client_secret: str = Form(...),
        ):
            if grant_type != "client_credentials" or client_secret != "s3cret":
                raise HTTPException(status_code=401, detail="invalid_client")
            fake.tokens_issued += 1
            tok = f"tok-{fake.tokens_issued}"
            fake.valid_tokens.add(tok)
            return {"access_token": tok, "expires_in": 300, "token_type": "Bearer"}

        @app.get("/api/v1/tools")
        async def list_tools(
            namespace: str = "default", authorization: str = Header(None)
        ):
            fake._check_auth(authorization)
            items = []
            for key in sorted(fake.tools):
                ns, name = key.split("/")
                if ns == namespace:
                    items.append(
                        {
                            "name": name,
                            "namespace": ns,
                            "description": "",
                            "status": "Ready",
                            "labels": {"rossoctl.io/type": "tool"},
                            "createdAt": None,
                            "workloadType": "deployment",
                        }
                    )
            return {"items": items}

        @app.get("/api/v1/tools/{ns}/{name}")
        async def get_tool(ns: str, name: str, authorization: str = Header(None)):
            fake._check_auth(authorization)
            tool = fake._tool(ns, name)
            return {
                "metadata": {"name": name, "namespace": ns},
                "spec": {},
                "status": {},
                "readyStatus": "Ready",
                "workloadType": "deployment",
                "service": {
                    "name": f"{name}-mcp",
                    "type": "ClusterIP",
                    "clusterIP": "10.0.0.1",
                    "ports": [
                        {"name": "http", "port": tool["port"], "protocol": "TCP"}
                    ],
                },
            }

        @app.post("/api/v1/tools/{ns}/{name}/connect")
        async def connect(ns: str, name: str, authorization: str = Header(None)):
            fake._check_auth(authorization)
            tool = fake._tool(ns, name)
            if tool["mcp"] is None:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to connect to MCP server at http://{name}-mcp",
                )
            return {"tools": tool["mcp"]}

        @app.post("/api/v1/tools/{ns}/{name}/invoke")
        async def invoke(
            ns: str, name: str, request: Request, authorization: str = Header(None)
        ):
            fake._check_auth(authorization)
            tool = fake._tool(ns, name)
            if tool["mcp"] is None:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to connect to MCP server at http://{name}-mcp",
                )
            body = await request.json()
            args = body.get("arguments") or {}
            if body["tool_name"] == "get_weather":
                if args.get("city") == "Atlantis":
                    return {
                        "result": {
                            "content": [
                                {"type": "text", "text": "City Atlantis not found"}
                            ],
                            "isError": True,
                        }
                    }
                return {
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {"temperature": 52, "weathercode": 53}
                                ),
                            }
                        ],
                        "isError": False,
                    }
                }
            if body["tool_name"] == "search_restaurants":
                return {
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    [
                                        {"name": "Trattoria di Mare"},
                                        {"name": "Bella Napoli"},
                                    ]
                                ),
                            }
                        ],
                        "isError": False,
                    }
                }
            return {
                "result": {
                    "content": [{"type": "text", "text": "ok"}],
                    "isError": False,
                }
            }

        return app
