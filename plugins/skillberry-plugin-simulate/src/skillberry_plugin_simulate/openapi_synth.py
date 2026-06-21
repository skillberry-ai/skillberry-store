"""Synthesize an OpenAPI 3.0.3 spec from skill tool manifests.

operationId is emitted as the exact MCP tool name so the simulation harness
exposes tool names identical to the real vMCP (load-bearing — §4.5).
"""
from typing import Any, Dict, List, Protocol


class Synthesizer(Protocol):
    def synthesize(self, tools: List[Dict[str, Any]], title: str) -> Dict[str, Any]:
        ...


class OpenApiSynthesizer:
    """Default synthesizer: input-schema-only fidelity (D7 enhancement deferred)."""

    OPENAPI_VERSION = "3.0.3"

    def synthesize(self, tools: List[Dict[str, Any]], title: str) -> Dict[str, Any]:
        paths: Dict[str, Any] = {}
        for tool in tools:
            name = tool["name"]
            params = tool.get("params") or {"type": "object", "properties": {}}
            request_schema = dict(params)
            request_schema.setdefault("type", "object")
            paths[f"/{name}"] = {
                "post": {
                    "operationId": name,  # NOT execute_<name>
                    "summary": tool.get("description") or name,
                    "requestBody": {
                        "required": bool(request_schema.get("required")),
                        "content": {
                            "application/json": {"schema": request_schema}
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful tool execution",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            },
                        },
                        "400": {"description": "Bad request"},
                        "500": {"description": "Internal server error"},
                    },
                }
            }
        return {
            "openapi": self.OPENAPI_VERSION,
            "info": {"title": title, "version": "1.0.0"},
            "paths": paths,
        }
