# skillberry-plugin-rossoctl-tools

Compose Skillberry Store skills from [rossoctl](https://github.com/rossoctl/rossoctl) tools, and generate
the rossoctl agent that uses them. Design: [docs/design/rossoctl-skills.md](../../docs/design/rossoctl-skills.md)
(revision 8, "option 0").

**rossoctl is not changed.** The plugin uses only rossoctl's existing `/api/v1/tools` API, and produces an
agent-create request made of existing fields.

## What it does

| Step | Route | Result |
|---|---|---|
| Import | `POST /plugins/rossoctl-tools/import` | One store **code** tool per MCP tool of each selected rossoctl tool. Its module is a generated proxy. Optionally, the skill too: an instructions snippet with a generated "Tools" section, and a `rossoctl-tools.json` snippet. |
| Test | `POST /tools/{id}/execute` (core) | The proxy runs in the store and calls rossoctl's `/invoke`. Needs `EXECUTE_PYTHON_LOCALLY=true`. |
| Deploy | `POST /plugins/rossoctl-tools/recipe` | The rossoctl `POST /api/v1/agents` body: `skills` plus `MCP_URLS`. Also the `rossoctl agents import` command and a pre-flight check. |
| Maintain | `POST /plugins/rossoctl-tools/check`, `/refresh` | Schema drift and per-namespace pre-flight; regenerating the skill's Tools section and `rossoctl-tools.json` |
| Browse | `GET /plugins/rossoctl-tools/tools?namespace=` | rossoctl's tools in a namespace |

### The recipe

```bash
curl -s -X POST $STORE/plugins/rossoctl-tools/recipe -H 'content-type: application/json' \
  -d '{"skill": "night-out-planner", "namespace": "team1", "agent": {"name": "night-out"}}'
```

```jsonc
{
  "ok": true, "missing": [], "not_ready": [],
  "preflight": [{"tool": "reservation-tool", "present": true, "ready": true, "port": 8000, "url": "http://reservation-tool-mcp.team1.svc.cluster.local:8000/mcp"}, …],
  "request": {                                   // POST /api/v1/agents
    "name": "night-out", "namespace": "team1", "deploymentMethod": "image",
    "containerImage": "ghcr.io/rossoctl/examples/generic_agent:latest",
    "skills": ["night-out-planner"],
    "envVars": [{"name": "MCP_URLS", "value": "http://reservation-tool-mcp.team1…/mcp,http://weather-tool-mcp.team1…/mcp"},
                {"name": "MCP_TRANSPORT", "value": "streamable_http"}], …
  },
  "cli": "rossoctl agents import from-image --name night-out …",
  "todo": ["Add the model settings (LLM_API_BASE, LLM_MODEL, LLM_API_KEY …) to envVars."]
}
```

- **Model settings and secrets.** The recipe never contains them. Add `LLM_*`, preferably as a `secretKeyRef`.
- **`agent.mode`:**
  - `direct` (default): one `MCP_URLS` entry per tool;
  - `gateway`: `MCP_URL`, the MCP Gateway address. The tools must be registered with the gateway, with the prefix given at import.
- **`agent.image`** overrides the default image. The default is `generic_agent`, the only stock agent that takes several MCP URLs and reads skills.

### The proxy code tool

Each imported MCP tool becomes an ordinary code tool:
- tags `mcp`, `rossoctl-proxy`, `rossoctl-tool:<name>` and `namespace:<ns>`;
- plugin metadata in `extra.rossoctl`.

Its module has one top-level function:
- **called by the store's executor:** it posts to rossoctl's `/invoke` when `ROSSOCTL_BACKEND_URL` is in the environment;
- **run as a script** (`python3 scripts/<tool>.py --<arg> …`): it speaks MCP over streamable HTTP to `<tool>-mcp.<namespace>.svc.cluster.local`, resolved in the caller's namespace.

It is standard-library only and embeds no credentials. Exit codes: `0` success, `1` tool error, `2` usage, `3` unreachable.

## Configuration

| Env | Default | Meaning |
|---|---|---|
| `ROSSOCTL_BACKEND_URL` | unset (plugin inactive) | e.g. `http://rossoctl-backend.rossoctl-system.svc.cluster.local:8000` |
| `ROSSOCTL_CLIENT_ID`, `ROSSOCTL_CLIENT_SECRET`, `ROSSOCTL_TOKEN_ENDPOINT` | unset | Client-credentials grant; leave unset when rossoctl runs without auth |
| `ROSSOCTL_ALLOWED_NAMESPACES` | `""` (any) | Comma-separated namespaces the plugin may target |
| `ROSSOCTL_TIMEOUT` | `30` | Seconds per backend call |
| `ROSSOCTL_AGENT_IMAGE` | `ghcr.io/rossoctl/examples/generic_agent:latest` | Default agent image in recipes |
| `ROSSOCTL_MCP_GATEWAY_URL` | `http://mcp-gateway-istio.gateway-system.svc.cluster.local:8080/mcp` | Gateway address for `mode: gateway` |
| `EXECUTE_PYTHON_LOCALLY` (core) | unset | `true` so store-side Execute of proxies reaches rossoctl `/invoke`. In Docker mode the proxy cannot see the store's environment. |

When the proxy runs as a script, it reads `ROSSOCTL_TOOL_<TOOL>_URL` (an override), `ROSSOCTL_NAMESPACE`, `ROSSOCTL_TOOL_<TOOL>_PORT`, `ROSSOCTL_TOOL_TIMEOUT`, `ROSSOCTL_MCP_GATEWAY_URL`, `MCP_PROXY_AUTH_HEADER`, `TRACEPARENT` and `TRACESTATE`. `<TOOL>` is the tool name upper-cased, with `_` for every non-alphanumeric character.

## Deploying with rossoctl's chart (existing values only)

```yaml
skillberryStore:
  image: {tag: "<release>-full"}
  extraEnv:
    - {name: ROSSOCTL_BACKEND_URL, value: "http://rossoctl-backend.rossoctl-system.svc.cluster.local:8000"}
    - {name: EXECUTE_PYTHON_LOCALLY, value: "true"}
    - {name: ROSSOCTL_CLIENT_ID,      valueFrom: {secretKeyRef: {name: rossoctl-api-oauth-secret, key: CLIENT_ID}}}
    - {name: ROSSOCTL_CLIENT_SECRET,  valueFrom: {secretKeyRef: {name: rossoctl-api-oauth-secret, key: CLIENT_SECRET}}}
    - {name: ROSSOCTL_TOKEN_ENDPOINT, valueFrom: {secretKeyRef: {name: rossoctl-api-oauth-secret, key: TOKEN_ENDPOINT}}}
apiOAuthSecret: {enabled: true}     # only with ui.auth.enabled=true
```

## Safety

- Proxy tools call live tools, including writes. Exclude the `rossoctl-proxy` tag from automatic runners such as the evaluator and DAST with `DAST_LIVE=1`.
- Store-side Execute uses the store's service identity. Keep `ROSSOCTL_ALLOWED_NAMESPACES` tight.

## Tests

```bash
source .venv/bin/activate
pytest plugins/skillberry-plugin-rossoctl-tools/tests                        # unit + e2e
ROSSOCTL_REPO=<rossoctl main> EXAMPLES_REPO=<rossoctl/examples> KUBECONFIG=<kwok> \
  plugins/skillberry-plugin-rossoctl-tools/tests/cluster/run-local-demo.sh   # cluster demo
```
