"""The deployment recipe: skill + its tools in one rossoctl agent-create request.

Design D3–D7. The output uses only fields rossoctl's existing
``POST /api/v1/agents`` (``CreateAgentRequest``) accepts, plus a pre-flight
report. It never contains model settings or secrets (D6).
"""

import json
import os
import shlex
from typing import Any, Dict, List, Optional

from .backend import (
    RossoctlBackend,
    RossoctlError,
    RossoctlNotFound,
    service_port,
    validate_label,
)

DEFAULT_AGENT_IMAGE = "ghcr.io/rossoctl/examples/generic_agent:latest"
DEFAULT_GATEWAY_URL = (
    "http://mcp-gateway-istio.gateway-system.svc.cluster.local:8080/mcp"
)
MODES = ("direct", "gateway")


def tool_url(tool: str, namespace: str, port: int, path: str = "/mcp") -> str:
    return f"http://{tool}-mcp.{namespace}.svc.cluster.local:{port}{path}"


async def preflight(
    backend: RossoctlBackend,
    namespace: str,
    tools: List[str],
    bearer: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Per required tool: present, ready, port, url (D7)."""
    out = []
    for tool in tools:
        entry: Dict[str, Any] = {
            "tool": tool,
            "present": False,
            "ready": False,
            "port": None,
            "url": None,
        }
        try:
            detail = await backend.get_tool(namespace, tool, bearer=bearer)
        except RossoctlNotFound:
            out.append(entry)
            continue
        except RossoctlError as e:
            entry["error"] = str(e)
            out.append(entry)
            continue
        port = service_port(detail)
        entry.update(
            {
                "present": detail.get("service") is not None,
                "ready": detail.get("readyStatus") == "Ready",
                "status": detail.get("readyStatus"),
                "port": port,
                "url": tool_url(tool, namespace, port),
            }
        )
        out.append(entry)
    return out


def agent_request(
    *,
    skill_name: str,
    namespace: str,
    agent_name: str,
    image: str,
    mode: str,
    checks: List[Dict[str, Any]],
    gateway_url: str,
) -> Dict[str, Any]:
    """The ``POST /api/v1/agents`` body (D3, D4, D5)."""
    env: List[Dict[str, str]] = []
    if mode == "gateway":
        env.append({"name": "MCP_URL", "value": gateway_url})
        env.append({"name": "MCP_URLS", "value": gateway_url})
    else:
        urls = [c["url"] for c in checks if c.get("present") and c.get("url")]
        if urls:
            env.append({"name": "MCP_URLS", "value": ",".join(urls)})
    env.append({"name": "MCP_TRANSPORT", "value": "streamable_http"})
    return {
        "name": agent_name,
        "namespace": namespace,
        "protocol": "a2a",
        "framework": "LangGraph",
        "deploymentMethod": "image",
        "containerImage": image,
        "workloadType": "deployment",
        "skills": [skill_name],
        "envVars": env,
        "servicePorts": [
            {"name": "http", "port": 8080, "targetPort": 8000, "protocol": "TCP"}
        ],
        "authBridgeEnabled": True,
    }


def cli_command(req: Dict[str, Any]) -> str:
    """The equivalent ``rossoctl agents import`` command."""
    parts = [
        "rossoctl agents import from-image",
        f"--name {shlex.quote(req['name'])}",
        f"--namespace {shlex.quote(req['namespace'])}",
        f"--containerImage {shlex.quote(req['containerImage'])}",
    ]
    for ev in req["envVars"]:
        parts.append(f"--envVar {shlex.quote(ev['name'] + '=' + ev['value'])}")
    parts.append(
        "--envVar LLM_API_BASE=<url> --envVar LLM_MODEL=<model> --envVar LLM_API_KEY=<key>"
    )
    parts.append(
        f"--additionalParameterJSON {shlex.quote(json.dumps({'skills': req['skills']}))}"
    )
    return " \\\n  ".join(parts)


async def build(
    backend: RossoctlBackend,
    *,
    skill_name: str,
    required: List[str],
    namespace: str,
    agent_name: Optional[str] = None,
    image: Optional[str] = None,
    mode: str = "direct",
    bearer: Optional[str] = None,
) -> Dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    backend.check_namespace(namespace)
    name = agent_name or skill_name
    validate_label(name, "agent name")
    checks = await preflight(backend, namespace, required, bearer=bearer)
    missing = [c["tool"] for c in checks if not c["present"]]
    not_ready = [c["tool"] for c in checks if c["present"] and not c["ready"]]
    req = agent_request(
        skill_name=skill_name,
        namespace=namespace,
        agent_name=name,
        image=image or os.getenv("ROSSOCTL_AGENT_IMAGE") or DEFAULT_AGENT_IMAGE,
        mode=mode,
        checks=checks,
        gateway_url=os.getenv("ROSSOCTL_MCP_GATEWAY_URL") or DEFAULT_GATEWAY_URL,
    )
    todo = [
        "Add the model settings (LLM_API_BASE, LLM_MODEL, LLM_API_KEY — the key as a secretKeyRef) to envVars.",
    ]
    if mode == "gateway":
        todo.append(
            "Register each required tool with the MCP Gateway (HTTPRoute + MCPServerRegistration) "
            "with the gateway prefix recorded on its tools."
        )
    if missing:
        todo.append(f"Deploy the missing tools in {namespace}: {', '.join(missing)}.")
    if not_ready:
        todo.append(f"Wait for these tools to become Ready: {', '.join(not_ready)}.")
    return {
        "request": req,
        "cli": cli_command(req),
        "preflight": checks,
        "missing": missing,
        "not_ready": not_ready,
        "ok": not missing and not not_ready,
        "todo": todo,
    }
