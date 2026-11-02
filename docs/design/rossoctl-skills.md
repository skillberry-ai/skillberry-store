# Skills that use rossoctl tools — Design

Status: **Implemented, revision 8 ("option 0")**
Owner: skillberry-store, `rossoctl-tools` plugin. **rossoctl: no change. skillberry-store core: C1 only.**

Revision notes:
* **r8:** the design and implementation are rebuilt around **option 0** ("step 0") of [the pitch](../rossoctl-skills-pitch.md#step-0--done-the-skill-and-its-tools-in-one-agent-request-no-rossoctl-change).
  - The skill is delivered by rossoctl as today.
  - The rossoctl tools it needs reach the agent as **MCP tools**, configured on the agent with the existing `MCP_URLS` / `MCP_URL` env vars, in the same create request that links the skill.
  - The plugin produces that create request (the **deployment recipe**).

  Proxy scripts stay in the package for agents that run scripts (and any non-rossoctl host), but nothing depends on them. r1–r7 are superseded; their history is in git.
* r7: evidence on how rossoctl agents use skills (kept as §2). r6: rossoctl tools as store code tools. r5: the core design principles. r4 and earlier: rossoctl changes, all dropped.

---

## 0. Principles

These hold from design through implementation. A section that contradicts them is a defect.

- **P-1. No changes in rossoctl.** Change rossoctl only when absolutely required, or when the alternative is extremely costly in effort or runtime performance. r8 changes nothing in rossoctl: no backend, UI, chart, operator, installer or docs change.
- **P-2. Store changes live in the plugin.** Core gets only generic must-have changes with value outside rossoctl. r8's core change is **C1** (an `isError` bug fix, §5.1), and this feature doesn't depend on it.

Outside both repos, the feature needs no change in `rossoctl/examples` either: option 0 works with the stock `generic_agent`.

## 1. What a user gets

Compose a skill in skillberry-store from tools already deployed in rossoctl. Then create an agent in rossoctl with the skill **and** its tools in one step, with a request the store generates.

1. **Import**: `POST /plugins/rossoctl-tools/import` reads the selected tools from rossoctl's backend. It creates one store tool per MCP tool, and optionally the skill with its instructions.
2. **Test from the store**: `POST /tools/{id}/execute` runs any of those tools from the store. The call goes through rossoctl's `/invoke`, so the tool is never contacted directly.
3. **Recipe**: `POST /plugins/rossoctl-tools/recipe {skill, namespace, agent}` returns:
   - a ready-to-send `POST /api/v1/agents` body: `skills: [<skill>]`, `envVars: [MCP_URLS=…, MCP_TRANSPORT=…]` and the agent image;
   - the equivalent `rossoctl agents import` command;
   - a pre-flight check that every required tool is deployed and ready in that namespace.
4. **Deploy**: send the body to rossoctl (UI, CLI or API). rossoctl's existing skill fetch puts the skill in the pod, and the agent connects to the tools over MCP. The skill's instructions tell it when and how to use each one.

## 2. Why option 0 (evidence)

Checked at `rossoctl/rossoctl@1cac9f3f` and `rossoctl/examples@f1fc5df2`.

- **The rossoctl agent contract has tools, not skills.** "Bring your own agent" requires A2A over HTTP plus `LLM_*`, `MCP_URL` (one address: a tool or the MCP Gateway) and `MCP_URLS` (several, comma-separated). `SKILL_FOLDERS` is set by the skill fetch, but no agent is obliged to read it.
- **No example agent executes skill scripts:**
  - `generic_agent` pastes SKILL.md and the scripts into the system prompt, and its only tools are MCP tools from `MCP_URLS`;
  - the LangGraph siblings (`weather_service` and others) ignore skills and take one `MCP_URL`;
  - the AG2, CrewAI and plain-LLM agents ignore skills;
  - `claude_agent` could run scripts, but is never pointed at the skill and isn't a console preset.

  So a script in a skill is, today, text the model reads.
- **This isn't a security rule.** The docs treat code-running agents as supported (the Sandboxes page; the internal skill-execution e2e), and they enforce policy at the AuthBridge sidecar regardless of agent code.
- **Consequence:**
  - On a stock rossoctl agent today, a skill's tools work only as **MCP tools wired on the agent**. The skill contributes the instructions.
  - Option 0 does exactly that, with no change anywhere. The store generates the wiring together with the skill, so the two stay consistent.

## 3. Overview

```
 skillberry-store (rossoctl-system)                         rossoctl (unchanged)                     team1
 ┌──────────────────────────────────┐  GET/POST /api/v1/tools ┌─────────────────────┐   MCP   ┌──────────────────────┐
 │ rossoctl-tools plugin            │  (list, get, connect,   │ rossoctl-backend    │───────▶ │ weather-tool-mcp     │
 │  /import → store tools + skill   │──── invoke) ───────────▶│                     │         │ reservation-tool-mcp │
 │  /recipe → POST /agents body     │                         │ skill autosync      │         └─────────▲────────────┘
 │  /check  → drift, pre-flight     │◀── GET /skills/ ────────│ + skill fetch init  │                   │ MCP (MCP_URLS)
 └──────────────────────────────────┘                         │   container         │         ┌─────────┴────────────┐
          │ recipe (JSON / CLI)                               └──────────┬──────────┘         │ agent pod            │
          ▼                                                              │ skill zip          │  SKILL_FOLDERS: skill│
     user ── POST /api/v1/agents {skills, envVars: MCP_URLS} ───────────▶└───────────────────▶│  MCP_URLS: the tools │
                                                                                              │  AuthBridge (egress) │
                                                                                              └──────────────────────┘
```

## 4. Decisions

All decisions taken in r8, numbered for reference. The implementation follows them.

| # | Decision | Reason |
|---|---|---|
| D1 | **No rossoctl change; no `rossoctl/examples` change.** | P-1. Option 0 works with stock agents. |
| D2 | **Core: C1 only.** Everything else from r4–r7 core (provider hook, contribution hooks, computed fields, core proxy generator) is reverted. | P-2. Not needed by option 0. |
| D3 | **The binding between a skill and its tools is the deployment recipe**, generated by the plugin, not anything inside rossoctl. | Option 0. The recipe uses only existing `CreateAgentRequest` fields (`skills`, `envVars`, `containerImage`, `deploymentMethod`, …). |
| D4 | **Tool addresses in the recipe:**<br>- **`direct`** (default): `MCP_URLS` = `http://<tool>-mcp.<ns>.svc.cluster.local:<port>/mcp` per required tool, with the port read live from `GET /tools/{ns}/{tool}`, plus `MCP_TRANSPORT=streamable_http`.<br>- **`gateway`**: `MCP_URL` = the MCP Gateway address (`ROSSOCTL_MCP_GATEWAY_URL`, default `http://mcp-gateway-istio.gateway-system.svc.cluster.local:8080/mcp`). | `direct` works on every install; only `generic_agent` takes several URLs. `gateway` serves single-`MCP_URL` agents, but needs the tools registered with the gateway by an operator; the recipe says so. |
| D5 | **The recipe targets `generic_agent` by default** (`ghcr.io/rossoctl/examples/generic_agent:latest`, `deploymentMethod: image`). The image is overridable. In `gateway` mode any MCP agent works. | It is the only stock agent that reads skills and accepts `MCP_URLS`. |
| D6 | **The recipe never carries LLM settings or secrets.** It leaves `LLM_*` to the user and lists them in `todo`. | The store doesn't know the cluster's model setup, and must not handle its keys. |
| D7 | **Pre-flight is part of the recipe:**<br>- for each required tool: present, `readyStatus`, Service port;<br>- a missing tool is reported in `missing`;<br>- the body still includes the present tools. | It replaces agent-create validation in rossoctl (P-1). |
| D8 | **Required tools are recorded on the skill** in `extra.rossoctl.required_tools`, a sorted list of rossoctl tool names. They are derived from the skill's rossoctl-imported tools when absent. | The recipe needs them. `extra` is opaque to core, so no core change is needed. |
| D9 | **Store tools are `code` tools** whose module is a generated **proxy**. As a function, the store calls rossoctl `/invoke` with the plugin's credential, read from the store's environment. As a CLI, an agent can run it, speaking MCP to the tool's Service. | Store-side testing and evaluation without a core hook (P-2). The script is also usable by script-running agents and non-rossoctl hosts. No credentials are embedded. |
| D10 | **Store-side execution needs the store's local execution mode** (`EXECUTE_PYTHON_LOCALLY=true`). In Docker mode the proxy can't see the store's environment, and calls the tool directly. | Core runs Docker execution with an empty environment. A per-tool env passthrough would be a core change (P-2), so it's deferred. |
| D11 | **Proxy tools are tagged `rossoctl-proxy`.** Operators should exclude them from automatic runners (evaluator, DAST live). | Store-side execution of a write tool has real side effects. |
| D12 | **SKILL.md guidance for the MCP path.** `/import` appends a generated "Tools" section to the skill's instructions snippet:<br>- the MCP tool names (`direct`) and their gateway-prefixed names (`gateway`, when a prefix is set);<br>- read-only and write markers;<br>- "ask the user before calling a write tool".<br>Its first line also tells script-capable agents about `scripts/`. | The agent learns the tools from MCP; the skill adds *when* and *how*. `/import` writes it once; `/refresh` regenerates it. |
| D13 | **Read-only marking comes from the import request** (`read_only: [...]`, default: none). | rossoctl's `/connect` returns no MCP annotations, and that won't change (P-1). |
| D14 | **Name collisions:** prefix on collision only (`<tool>__<name>`). | Store tool names are global. |
| D15 | **`rossoctl-tools.json` is a `file:` snippet** in the skill: `{schema, tools: [{tool, port, path, mcp_tools: [...]}]}`. It declares the dependency in the package, for people and other tooling. | No core hook. A plain file in the export. |
| D16 | **Credential:** client-credentials (`ROSSOCTL_CLIENT_ID/SECRET/TOKEN_ENDPOINT`), or none when rossoctl runs without auth. Deployment: existing chart keys (`skillberryStore.extraEnv`, `apiOAuthSecret`). | No chart change (P-1). |
| D17 | **Stage 2 (promoting store code tools to rossoctl tools) is deferred.** The r6 approach remains valid: existing `POST /tools` and a store-owned runner. | Out of option 0's scope. |
| D18 | **The demo runs against unmodified rossoctl `main`**, and is scripted in the plugin's tests. | It proves D1. |
| D19 | **The r4 rossoctl branch is retired.** The local `rossoctl-skills` branch of the fork is reset to `main`; the r4 commits are kept on `rossoctl-skills-r4-archive`. The remote fork is unchanged until the owner approves a push. | D1. Nothing is lost, and nothing changes on a shared remote without consent. |
| D20 | **The r4 `rossoctl/examples` commit** (Claude Code skill linking, the `run_skill_script` tool) stays on a local branch. It isn't part of option 0. It's the starting point for pitch step 1. | Option 0 needs no agent change. |
| D21 | **`generic_agent`'s MCP client (`langchain-mcp-adapters`) is a plugin dev dependency.** The e2e test uses it to prove the recipe's wiring works with the real agent's client, and it skips without it. | The strongest check available without an LLM. |
| D22 | **The instructions in the demo skill name MCP tools**, not scripts. The generated Tools section mentions the scripts for script-capable agents. | Option 0's agent path is MCP. |

## 5. skillberry-store

### 5.1 Core: C1 (independent fix)

`execute_mcp_tool` returned `content[0].text` and ignored `isError`. Now:
- an `isError` result becomes `{"error": …}`, which gives HTTP 500 at `/tools/{id}/execute`;
- all text items are joined;
- `structuredContent` is returned as `structured`.

It is in CHANGELOG. It affects only SSE `mcp` tools, which option 0 does not use.

Also in core: `tests/test_core_has_no_rossoctl.py`, which fails if core source mentions `rossoctl` or `svc.cluster.local`, and the CI job that runs core tests with no plugins installed.

### 5.2 Plugin `rossoctl-tools`

`plugins/skillberry-plugin-rossoctl-tools/`, extra `plugin-rossoctl-tools` (in `plugins-all`), dependency `httpx`. It is active when `ROSSOCTL_BACKEND_URL` is set.

| Module | Role |
|---|---|
| `backend.py` | Client for rossoctl `/api/v1/tools`:<br>- endpoints `list`, `get`, `connect`, `invoke`;<br>- a cached client-credentials token, refreshed once on 401;<br>- DNS-1123 name checks and `ROSSOCTL_ALLOWED_NAMESPACES`. |
| `proxy.py` | Generates the proxy module (D9). One top-level function, so core's executor and importer each see exactly one tool. Its two paths:<br>- **store:** stdlib HTTP to `/invoke`;<br>- **CLI:** stdlib MCP over streamable HTTP. |
| `skill.py` | The generated Tools section (D12) and `rossoctl-tools.json` (D15); the required-tools list (D8). |
| `recipe.py` | Pre-flight and the agent-create body (D3–D7). |
| `plugin.py` | Routes and UI action. |

**Routes** (all under `/plugins/rossoctl-tools`):

| Route | Permission | Behavior |
|---|---|---|
| `GET /tools?namespace=` | `tools:list` | Pass-through of rossoctl's tool list |
| `POST /import` | `tools:create` | Body: `{namespace, tools: [{name, read_only?: [str], gateway_prefix?}], skill?: {name, description, instructions?, tags?}}`. Creates the proxy tools, and optionally the skill:<br>- an instructions snippet (author text + the Tools section);<br>- the `rossoctl-tools.json` snippet;<br>- `extra.rossoctl`. |
| `POST /recipe` | `skills:get` | Body: `{skill, namespace, agent?: {name?, image?, mode?: "direct" \| "gateway"}}` → `{request, cli, preflight: [...], missing: [...], todo: [...]}` |
| `POST /check` | `tools:list` | `{skill?, tool_uuids?, namespaces?}` → schema drift (via `/connect`) and per-namespace pre-flight |
| `POST /refresh` | `skills:create` | Regenerates the Tools section and `rossoctl-tools.json` from the skill's current tools (new snippet versions, new skill version) |

**Plugin env:**
- `ROSSOCTL_BACKEND_URL`;
- `ROSSOCTL_CLIENT_ID`, `ROSSOCTL_CLIENT_SECRET`, `ROSSOCTL_TOKEN_ENDPOINT`;
- `ROSSOCTL_ALLOWED_NAMESPACES`, `ROSSOCTL_TIMEOUT`;
- `ROSSOCTL_AGENT_IMAGE` (default D5), `ROSSOCTL_MCP_GATEWAY_URL` (default D4).

### 5.3 Behavior without the plugin

| Situation | Behavior |
|---|---|
| Skills and tools the plugin created | They are ordinary code tools and snippets. Export, import and store UI all work. |
| Execute of a proxy tool | Works if `ROSSOCTL_BACKEND_URL` (and the credential) is still in the store's environment. Otherwise it calls the tool directly, which fails outside the cluster. |
| `/plugins/rossoctl-tools/*` | 404 |

## 6. Deployment (existing chart values only)

```yaml
featureFlags: {skills: true, externalSkills: true}
components: {skillberryStore: {enabled: true}}
skillberryStore:
  image: {tag: "<release>-full"}            # built with plugins-all
  extraEnv:
    - {name: ROSSOCTL_BACKEND_URL, value: "http://rossoctl-backend.rossoctl-system.svc.cluster.local:8000"}
    - {name: EXECUTE_PYTHON_LOCALLY, value: "true"}     # D10
    # with ui.auth.enabled=true, reuse the existing api-oauth-secret client (D16):
    - {name: ROSSOCTL_CLIENT_ID,      valueFrom: {secretKeyRef: {name: rossoctl-api-oauth-secret, key: CLIENT_ID}}}
    - {name: ROSSOCTL_CLIENT_SECRET,  valueFrom: {secretKeyRef: {name: rossoctl-api-oauth-secret, key: CLIENT_SECRET}}}
    - {name: ROSSOCTL_TOKEN_ENDPOINT, valueFrom: {secretKeyRef: {name: rossoctl-api-oauth-secret, key: TOKEN_ENDPOINT}}}
  autosync: {allowedTags: "rossoctl-approved"}
apiOAuthSecret: {enabled: true}
```

## 7. Security

- **The recipe** holds no secrets (D6). The user adds `LLM_*`, typically as a `secretKeyRef`.
- **The agent reaches the tools over MCP through its AuthBridge sidecar**, like any MCP-wired rossoctl agent. With token exchange, the user adds `outboundRoutes` as today.
- **Proxy scripts** embed no credentials. In the store they read the plugin's credential from the store's environment. In agents they never see one.
- **Store-side Execute** runs as the store's service identity. In `disabled` store ACL mode, anyone who can call the store can invoke a rossoctl tool through it. Keep `ROSSOCTL_ALLOWED_NAMESPACES` tight (D11).

## 8. Testing

| Layer | Tests |
|---|---|
| Core | C1 unit tests; the no-rossoctl guard; golden exports unchanged; the full `make test` |
| Plugin unit | Backend client vs a fake rossoctl backend (token, 401 refresh, host allowlist); proxy generation (safety, one function, core parser compatibility); recipe (`direct`/`gateway`, ports, missing tools, no secrets); the Tools section and `rossoctl-tools.json`; `/check` |
| Plugin e2e | The in-process store with the plugin against the fake backend: import → Execute (through `/invoke`) → recipe → export; the proxy CLI against a FastMCP streamable-HTTP fixture |
| Cluster e2e | `tests/cluster/run-local-demo.sh`, which runs §9 on a kwok control plane with **rossoctl `main` unmodified**. It plays the agent as `generic_agent` would: MCP calls to the recipe's `MCP_URLS`. |

## 9. Demo: night-out-planner

1. **Deploy the tools:** `weather-tool` and `reservation-tool` in `team1` (console presets, or `--with-examples` plus the Reservation Tool preset).
2. **Import** both into the store, with the skill `night-out-planner` (`rossoctl-approved`) and the read-only list.
3. **Store-side test:** Execute `search_restaurants {"city": "Boston", "cuisine": "Italian"}` → Trattoria di Mare.
4. **Generate the recipe** for `team1`:
   - pre-flight shows both tools ready;
   - `request.envVars` has `MCP_URLS` with both Services;
   - `skills: ["night-out-planner"]`.
5. **Create the agent** by posting the recipe (adding `LLM_*`). Autosync has already created the skill in `team1`, so the fetch init container delivers it and `generic_agent` puts it in its prompt.
6. **Chat:** "Plan dinner for 4 in Boston tomorrow at 7pm, Italian." The agent calls `get_weather`, `search_restaurants` and `check_availability` (19:00 is taken, so it offers 19:30), asks for confirmation, then calls `place_reservation`.
7. **Portability:** the recipe for `team2` (no reservation tool) reports `missing: ["reservation-tool"]` before anything is created.

User guide: [docs/demos/rossoctl-night-out-planner.md](../demos/rossoctl-night-out-planner.md).

## 9A. Runbook: the demo end to end on a laptop with Kind (for an agent to execute)

This section is written to be executed step by step by a coding agent, or by a person, on a laptop
where this branch is checked out. Every step names its **command**, its **check**, and what to do if
the check fails. The agent should stop at the first check it cannot make pass, and report.

### R0. Ground rules for the executing agent

- Work from the root of this repository (`skillberry-store`, branch `rossoctl-skills`).
- **Do not modify rossoctl.** Clone it at `main` and use its installer as is. The demo's purpose is to
  show that unmodified rossoctl works (D1).
- Create everything under `~/rossoctl-demo/` (`$DEMO`). Delete nothing outside it, and nothing outside
  the Kind cluster named `rossoctl`.
- Redirect long command output to `$DEMO/logs/<step>.log` and print only the result line. Read a log
  only when a check fails.
- Never print or commit an API key. Keys go into Kubernetes Secrets only.
- Ask the user before:
  - deleting an existing Kind cluster named `rossoctl`;
  - stopping a process that holds port 8080.

### R1. Prerequisites

| Tool | Check | Notes |
|---|---|---|
| Docker (or Podman) | `docker info >/dev/null && echo ok` | 8 GB RAM and 4 CPUs for the Docker VM |
| Kind ≥ 0.20 | `kind version` | |
| kubectl, Helm ≥ 3.12 | `kubectl version --client; helm version --short` | |
| Python 3.11+, `uv`, `jq`, `git`, `curl` | `python3 --version; uv --version; jq --version` | |
| Port 8080 free | `! lsof -iTCP:8080 -sTCP:LISTEN` | rossoctl's gateway listens there |
| An LLM for the agent | see R6 | Ollama on the laptop, or an OpenAI-compatible key |

```bash
export DEMO=~/rossoctl-demo; mkdir -p $DEMO/logs
export STORE_REPO=$(git rev-parse --show-toplevel)       # this checkout
git -C $STORE_REPO rev-parse --abbrev-ref HEAD            # expect: rossoctl-skills
```

### R2. Build a store image with the plugin

```bash
cd $STORE_REPO
python3 -m venv .venv && source .venv/bin/activate
make docker-build-full CUSTOM_TAG=rossoctl-tools > $DEMO/logs/r2-build.log 2>&1; echo "exit $?"
docker images --format '{{.Repository}}:{{.Tag}}' | grep 'skillberry-store:rossoctl-tools'
```

**Check:** one line, `ghcr.io/skillberry-ai/skillberry-store:rossoctl-tools`.

**If it fails:** the log ends with the failing build step.
- An SSH or git-subtree error in `skillberry-common` means the make wrapper needs `git` access to `github.com`; run `ssh -T git@github.com` first.
- If `make` itself is the problem, build directly:

  ```bash
  docker build --build-arg PLUGIN_EXTRAS=plugins-all -t ghcr.io/skillberry-ai/skillberry-store:rossoctl-tools .
  ```

Confirm the image contains the plugin:

```bash
docker run --rm --entrypoint sh ghcr.io/skillberry-ai/skillberry-store:rossoctl-tools -c \
  '.venv/bin/python -c "import skillberry_plugin_rossoctl_tools.plugin as p; print(p.SLUG)"'
```

**Check:** prints `rossoctl-tools`.

### R3. Get rossoctl `main` and rossoctl/examples

```bash
git clone --depth 1 https://github.com/rossoctl/rossoctl.git $DEMO/rossoctl
git clone --depth 1 https://github.com/rossoctl/examples.git $DEMO/rossoctl-examples
git -C $DEMO/rossoctl log -1 --oneline
```

**Check:** both clones exist. Record the rossoctl commit for the report.

### R4. Values for the store (existing chart keys only)

```bash
cat > $DEMO/store-values.yaml <<'EOF'
skillberryStore:
  image:
    repository: ghcr.io/skillberry-ai/skillberry-store
    tag: rossoctl-tools
    pullPolicy: IfNotPresent
  extraEnv:
    - {name: ROSSOCTL_BACKEND_URL, value: "http://rossoctl-backend.rossoctl-system.svc.cluster.local:8000"}
    - {name: ROSSOCTL_ALLOWED_NAMESPACES, value: "team1,team2"}
    - {name: EXECUTE_PYTHON_LOCALLY, value: "true"}
  autosync:
    allowedTags: "rossoctl-approved"
EOF
```

This install has no SPIRE, so UI auth and the backend's `ENABLE_AUTH` are off, and the plugin needs no
credential. To run with auth (`--with-spire` / `--with-all`), add the three
`ROSSOCTL_CLIENT_*`/`TOKEN_ENDPOINT` entries and `apiOAuthSecret: {enabled: true}` from §6.

### R5. Create the cluster and install rossoctl

```bash
cd $DEMO/rossoctl
kind get clusters | grep -qx rossoctl && echo "EXISTS - ask the user before deleting it"
kind create cluster --name rossoctl > $DEMO/logs/r5-kind.log 2>&1; echo "kind exit $?"
kind load docker-image ghcr.io/skillberry-ai/skillberry-store:rossoctl-tools --name rossoctl
scripts/kind/setup-rossoctl.sh --skip-cluster --with-skills --with-examples \
  --rossoctl-values $DEMO/store-values.yaml > $DEMO/logs/r5-install.log 2>&1; echo "install exit $?"
```

The installer takes about 10–15 minutes.
- `--with-skills` deploys the store and turns on skill autosync. It also turns on the backend and the UI.
- `--with-examples` deploys `weather-tool` (and the `weather-service` agent) in `team1`.

**Checks:**

```bash
kubectl -n rossoctl-system rollout status deploy/rossoctl-backend --timeout=300s
kubectl -n rossoctl-system rollout status deploy/skillberry-store --timeout=600s
kubectl -n team1 rollout status deploy/weather-tool --timeout=300s
kubectl -n rossoctl-system get deploy skillberry-store -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
curl -s http://rossoctl-ui.localtest.me:8080/api/v1/config/features | jq '{skills, externalSkills}'
```

Expect all three rollouts complete, the image `…:rossoctl-tools`, and `skills: true, externalSkills: true`.

**If the store pod restarts:** run `kubectl -n rossoctl-system logs deploy/skillberry-store --tail=50`.
- The first start can take minutes while the embedding model is downloaded.
- A `ModuleNotFoundError` for the plugin means R2 built the wrong image.

### R6. LLM for the agent

Choose one and record it for the report.

**Ollama** (no key):

```bash
ollama pull qwen2.5:7b          # a 7B+ model follows the tool procedure much better than 3B
OLLAMA_HOST=0.0.0.0 ollama serve &     # leave running
export LLM_API_BASE=http://host.docker.internal:11434/v1 LLM_MODEL=qwen2.5:7b LLM_KEY_SECRET=
```

On Linux without Docker Desktop, use `http://$(docker network inspect kind -f '{{(index .IPAM.Config 0).Gateway}}'):11434/v1`.

**OpenAI-compatible:**

```bash
read -rs OPENAI_KEY && kubectl -n team1 create secret generic openai-secret --from-literal=apikey="$OPENAI_KEY"
kubectl -n team2 create secret generic openai-secret --from-literal=apikey="$OPENAI_KEY"; unset OPENAI_KEY
export LLM_API_BASE=https://api.openai.com/v1 LLM_MODEL=gpt-4o-mini LLM_KEY_SECRET=openai-secret
```

### R7. Deploy the reservation tool in `team1`

```bash
kubectl apply -n team1 -f $STORE_REPO/plugins/skillberry-plugin-rossoctl-tools/deploy/reservation-tool.yaml
kubectl -n team1 rollout status deploy/reservation-tool --timeout=300s
kubectl -n team1 get svc weather-tool-mcp reservation-tool-mcp
```

**Check:** both Services exist. The console's **Tools → Import Tool → Reservation Tool** preset is an
equivalent alternative.

### R8. Reach the store API

```bash
kubectl -n rossoctl-system port-forward svc/skillberry-store 18000:8000 > $DEMO/logs/r8-pf.log 2>&1 &
export STORE=http://localhost:18000 ROSSOCTL=http://rossoctl-ui.localtest.me:8080
sleep 3; curl -s $STORE/plugins/ | jq -r '.[] | select(.slug=="rossoctl-tools") | "\(.slug): \(.status)"'
```

**Check:** prints `rossoctl-tools: Ready`. If it prints nothing, the image lacks the plugin (go back
to R2). If it prints `Disabled: set ROSSOCTL_BACKEND_URL`, R4's values were not applied: run
`kubectl -n rossoctl-system set env deploy/skillberry-store --list`.

### R9. Demo step 1: import the tools and compose the skill

```bash
jq -n --rawfile instr $STORE_REPO/docs/demos/rossoctl-night-out-planner/instructions.md '{
  namespace: "team1",
  tools: [{name: "weather-tool", read_only: ["get_weather"]},
          {name: "reservation-tool", read_only: ["search_restaurants","check_availability","list_reservations"]}],
  skill: {name: "night-out-planner",
          description: "Plan and book a restaurant evening in a city, taking current weather into account.",
          instructions: $instr, tags: ["rossoctl-approved"]}}' |
curl -s -X POST $STORE/plugins/rossoctl-tools/import -H 'content-type: application/json' -d @- \
  | tee $DEMO/logs/r9-import.json | jq '{tools: [.tools[].name], skill_uuid, errors}'
```

**Check:**
- `tools` lists `get_weather`, `search_restaurants`, `check_availability`, `place_reservation`, `cancel_reservation` and `list_reservations`;
- `skill_uuid` is set;
- `errors` is `[]`.

A 502 error for a tool means rossoctl's backend cannot reach that tool's MCP server; check that its pod is
Ready.

### R10. Demo step 2: store-side execution through rossoctl

```bash
curl -s -X POST $STORE/tools/search_restaurants/execute -H 'content-type: application/json' \
  -d '{"city":"Boston","cuisine":"Italian"}' | jq -r '."return value"' | jq -r '.[].name'
kubectl -n rossoctl-system logs deploy/rossoctl-backend --since=2m | grep -c 'reservation-tool/invoke'
```

**Check:** prints `Trattoria di Mare`, and the count is ≥ 1. The call went store → rossoctl `/invoke` →
tool.

If the error mentions `svc.cluster.local` or "unreachable", the store runs code in Docker mode:
`EXECUTE_PYTHON_LOCALLY` is missing (R4).

### R11. Demo step 3: the deployment recipe and pre-flight

```bash
curl -s -X POST $STORE/plugins/rossoctl-tools/recipe -H 'content-type: application/json' \
  -d '{"skill":"night-out-planner","namespace":"team1","agent":{"name":"night-out"}}' > $DEMO/recipe-team1.json
jq '{ok, missing, preflight: [.preflight[] | {tool, ready, port}], env: .request.envVars, skills: .request.skills}' $DEMO/recipe-team1.json
```

**Check:**
- `ok: true` and `missing: []`;
- both tools are ready, on port 8000;
- `MCP_URLS` lists `reservation-tool-mcp.team1…` and `weather-tool-mcp.team1…`;
- `skills: ["night-out-planner"]`.

### R12. Demo step 4: rossoctl autosync picks the skill up

```bash
for i in $(seq 1 30); do kubectl -n team1 get cm night-out-planner >/dev/null 2>&1 && break; sleep 5; done
kubectl -n team1 get cm night-out-planner -o jsonpath='{.metadata.labels.rossoctl\.io/source} {.metadata.labels.rossoctl\.io/auto-sync}'; echo
```

**Check:** prints `external true`. In the console, **Skills** lists `night-out-planner`.

**If it never appears**, autosync is not running against the store:

```bash
kubectl -n rossoctl-system get cm rossoctl-skill-autosync-config -o yaml   # enabled: "true", registry-url, allowed-tags
kubectl -n rossoctl-system logs deploy/rossoctl-backend | grep -i auto-sync | tail
```

The skill needs the tag `rossoctl-approved`; R9 sets it.

### R13. Demo step 5: create the agent from the recipe

Add the model settings to the recipe's request, then send it to rossoctl's existing agent API:

```bash
jq --arg base "$LLM_API_BASE" --arg model "$LLM_MODEL" --arg sec "$LLM_KEY_SECRET" '
  .request
  | .envVars += [{name:"LLM_API_BASE", value:$base}, {name:"LLM_MODEL", value:$model}]
  | .envVars += (if $sec == "" then [{name:"LLM_API_KEY", value:"dummy"}]
                 else [{name:"LLM_API_KEY", valueFrom:{secretKeyRef:{name:$sec, key:"apikey"}}}] end)' \
  $DEMO/recipe-team1.json > $DEMO/agent-team1.json
curl -s -X POST $ROSSOCTL/api/v1/agents -H 'content-type: application/json' -d @$DEMO/agent-team1.json | jq -r .message
kubectl -n team1 rollout status deploy/night-out --timeout=600s
```

**Checks:**

```bash
kubectl -n team1 get deploy night-out -o json | jq -r '.spec.template.spec.initContainers[].name, (.spec.template.spec.containers[] | select(.name=="agent") | .env[] | select(.name|test("MCP_|SKILL_")) | "\(.name)=\(.value)")'
kubectl -n team1 exec deploy/night-out -- ls /app/skills/night-out-planner /app/skills/night-out-planner/scripts
# skills and MCP tools are loaded on the first request; R14 checks the log again
kubectl -n team1 logs deploy/night-out -c agent --tail=50 | tail -3
```

Expect:
- a `fetch-skill-0` init container;
- `MCP_URLS` with both tools, `MCP_TRANSPORT=streamable_http`, and `SKILL_FOLDERS=/app/skills/night-out-planner`;
- `SKILL.md`, `rossoctl-tools.json` and `scripts/` in the pod;
- the agent's log shows it started. It loads the skill and the MCP tools on the first chat request (R14).

**If the init container fails:**
- `kubectl -n team1 logs deploy/night-out -c fetch-skill-0`;
- the store URL in the skill must be reachable from `team1`, and the store must be Ready.

If the agent pod is created without the init container, the skill ConfigMap did not exist yet: wait
for R12, delete the agent (`curl -s -X DELETE $ROSSOCTL/api/v1/agents/team1/night-out`), and repeat
R13.

### R14. Demo step 6: chat

In the console (`http://rossoctl-ui.localtest.me:8080`), open **Agents → night-out → Chat**, or use the API:

```bash
chat() { curl -s -X POST $ROSSOCTL/api/v1/chat/team1/night-out/send -H 'content-type: application/json' \
  -d "$(jq -n --arg m "$1" --arg s "${SID:-}" '{message:$m} + (if $s=="" then {} else {session_id:$s} end)')"; }
R=$(chat "Plan dinner for 4 in Boston tomorrow at 7pm, Italian, mid-range."); export SID=$(jq -r .session_id <<<"$R"); jq -r .content <<<"$R"
jq -r .content <<<"$(chat "Book Trattoria di Mare for 4 tomorrow at 7:30pm for Ada Lovelace, phone 555-0100, email ada@example.com.")"
jq -r .content <<<"$(chat "Yes, confirm the booking.")"
jq -r .content <<<"$(chat "What reservations do I have under ada@example.com?")"
```

**Checks:**
- The first answer mentions current weather and at least one Boston Italian restaurant, such as Trattoria di Mare.
- After "Yes", the answer contains a confirmation code (`RES…`).
- Ground truth, independent of the model's wording:

  ```bash
  kubectl -n team1 logs deploy/reservation-tool --since=15m | grep -E "search_restaurants|place_reservation|list_reservations" | tail
  kubectl -n team1 logs deploy/weather-tool --since=15m | grep -i -E "get_weather|city" | tail -3
  ```

  Expect `search_restaurants` and `place_reservation` calls in the tool's log. Those prove the agent used the tools it got through the recipe.

After the first message, the agent's log must show both loads:

```bash
kubectl -n team1 logs deploy/night-out -c agent | grep -E "Successfully loaded [0-9]+ (skill|MCP tool)"
# expect: "Successfully loaded 1 skill(s) …" and "Successfully loaded 6 MCP tool(s)"
```

**If the agent answers without calling tools:**
- check those two log lines; "0 MCP tool(s)" means `MCP_URLS` is unreachable from the pod;
- use a stronger model (R6).

Small models may also skip the confirmation step. That is a model-quality issue, not a wiring issue; note it in the report.

### R15. Demo step 7: portability and pre-flight in another namespace

```bash
curl -s -X POST $STORE/plugins/rossoctl-tools/recipe -H 'content-type: application/json' \
  -d '{"skill":"night-out-planner","namespace":"team2"}' | jq '{ok, missing}'
```

**Check:** `ok: false`, and `missing` lists both tools, since `team2` has neither. Then:

```bash
kubectl apply -n team2 -f $STORE_REPO/plugins/skillberry-plugin-rossoctl-tools/deploy/reservation-tool.yaml
kubectl -n team1 get deploy weather-tool -o yaml | sed 's/namespace: team1/namespace: team2/' \
  | grep -v -E 'resourceVersion|uid:|creationTimestamp|generation:' | kubectl apply -f - >/dev/null
kubectl -n team1 get svc weather-tool-mcp -o yaml | sed 's/namespace: team1/namespace: team2/' \
  | grep -v -E 'resourceVersion|uid:|creationTimestamp|clusterIP|clusterIPs' | kubectl apply -f - >/dev/null
kubectl -n team2 rollout status deploy/reservation-tool deploy/weather-tool --timeout=300s
curl -s -X POST $STORE/plugins/rossoctl-tools/recipe -H 'content-type: application/json' \
  -d '{"skill":"night-out-planner","namespace":"team2"}' | jq '{ok, missing}'
```

**Check:** `ok: true`. The same skill, unchanged, is deployable in `team2`.

**Optional:** repeat R13 and R14 with `team2` in place of `team1` (create the `openai-secret` there first if you use one).

### R16. rossoctl is unmodified

```bash
git -C $DEMO/rossoctl status --porcelain | wc -l      # expect 0
git -C $DEMO/rossoctl log -1 --format='%H %s'
```

### R17. Report

Report each step R2–R16 as **pass**, **fail** or **skipped**, with:
- the rossoctl commit, the store commit (`git -C $STORE_REPO rev-parse --short HEAD`) and the LLM used;
- for each failure: the check that failed, the last 20 lines of the step's log, and what you tried;
- the transcript of R14 and the tool-log lines that prove the calls.

### R18. Clean up (only when the user asks)

```bash
kill %1 2>/dev/null            # the port-forward from R8
kind delete cluster --name rossoctl
rm -rf $DEMO
```

## 10. Next steps

[The pitch](../rossoctl-skills-pitch.md) lists the next steps, ranked by how much each asks of rossoctl. Each one is opt-in and would get its own design:
1. **`rossoctl/examples` only:** `claude_agent` and `generic_agent` use the skills they're given, so the bundled proxy scripts become usable (D20);
2. **docs only:** describe skills in "Bring your own agent";
3. **a small, flagged backend change:** rossoctl wires a skill's tools at agent create. Only if steps 0–2 prove the pattern, and only with the rossoctl maintainers' agreement (P-1).

Stage 2, promotion (D17), is independent of these.
