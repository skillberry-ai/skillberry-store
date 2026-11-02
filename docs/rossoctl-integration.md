# rossoctl ↔ skillberry-store: Integration Notes

Findings from a source inspection of:

- [`rossoctl/rossoctl`](https://github.com/rossoctl/rossoctl) at `44ec9139` (2026-10-06). The repo was formerly `kagenti/kagenti`; both slugs resolve to GitHub id `956041323`.
- [`rossoctl/operator`](https://github.com/rossoctl/operator) at `10dd076` (2026-09-22).
- skillberry-store (this repo) at `70137bb`.

In rossoctl, all backend paths below are relative to `rossoctl/backend/app/`, UI paths to `rossoctl/ui-v2/src/`, and chart paths to `charts/rossoctl/`.

## TL;DR

- **Direction**: mostly reads, plus one indirect write path. rossoctl polls and fetches skills from skillberry-store. Behind the `dreaming` feature flag, it also submits jobs to the store's `ask-runspace` plugin. That job runs a Claude Code agent that **creates new skill versions in the store** through the store's control MCP.
- **Endpoints hit**:
  - `GET /skills/` and `GET /skills/{name}/export-anthropic`, always.
  - `POST /plugins/ask-runspace/run`, `GET /plugins/ask-runspace/status/{id}`, and MCP tool calls on `/control_sse`, when dreaming is on.
- **Identity passed**: none. All calls are anonymous HTTP with no auth headers and no token. skillberry-store has an access-control subsystem, but the integration only works with it in `disabled` mode (see [Identity on the integration path](#identity-on-the-integration-path)).
- **Scoping**: entirely client-side in rossoctl, after the full skill list arrives.
- **Versions**: rossoctl records the oldest version of each skill but agents fetch the newest, and version content can change in place (see [Skill versions](#skill-versions)).
- **Related resources**: rossoctl manages "tools" as Kubernetes workloads described by an `AgentRuntime` CR, not in skillberry-store. It does not manage prompts or snippets as resources.
- **Composition**: agents list skills as a first-class field. rossoctl tools are wired only through a single `MCP_URL` env var. Skills cannot declare a tool dependency.

## Value Proposition

### Today

rossoctl treats skillberry-store as an anonymous, read-only catalog:

1. Every 30 s the backend downloads the **entire** skill list.
2. It filters the list itself (`allowed-tags`, `namespace:` tags).
3. It writes one empty pointer ConfigMap per skill per namespace.
4. At pod start an init container downloads each skill's zip by name.

Downsides:

- **No security.** rossoctl sends no identity, so the store must run with access control disabled. Its whole API, including `purge-all` and `restore`, is open inside the cluster, and also outside it through the UI route, because the UI proxies the API.
- **Policy in the wrong place.** Which namespace sees which skill is decided in rossoctl, from tags anyone with write access to the store can change. The store cannot enforce it, and rossoctl keeps a per-namespace mirror in sync.
- **Inconsistent, unpinned versions.** The skill list contains every version of every skill, and rossoctl keeps one entry per name: the **oldest**. So rossoctl shows and distributes the oldest version's description, tags and version, while agents fetch the newest. New versions never trigger a resync, and the version rossoctl records is ignored at fetch time. Nothing guarantees a version's content stays fixed either: it can be edited in place, and rossoctl's change check does not look at content. See [Skill versions](#skill-versions).
- **Skills cannot use rossoctl tools.** A store skill's tools are local scripts, and its "remote" tools are bodiless stubs that only the store can run, over SSE. rossoctl tools are MCP services over streamable HTTP, and an agent can be linked to only one of them.

### Staged improvement

Each stage puts the work in skillberry-store and asks rossoctl for at most a few lines. Stages 1–2 (versions) and 3–4 (access control) are independent tracks. Stage 5 builds on both.

| Stage | skillberry-store adds | rossoctl changes | Value |
|---|---|---|---|
| **1. Consistent versions** *(immediate)* | A heads-only list mode (`GET /skills/?heads=true`, one entry per name). `export-anthropic` honors `?version=`: empty or `latest` means the head, otherwise the newest object with that version. | Add `heads=true` to the autosync `GET`. Add `?version=${SKILL_VERSION}` to the fetcher's `curl`. | What rossoctl shows and distributes is what agents run. New versions, including dream output, are picked up by autosync. The fetched content matches the version rossoctl recorded. Hand-created external skills (`registrySkillVersion`) can be held at a version. |
| **2. Immutable, semantically versioned objects** | Core data is locked at creation: skill name, description, tool and snippet references, and `file:` placement; tool module, params and packaging; snippet text. A PUT that changes a core field is rejected (422, naming the immutable fields). A PUT that resends core fields unchanged still succeeds. A new version is created explicitly, with a POST under the same name. Tags, namespaces and `state` stay mutable. Each object gets a core digest, and each export a digest (`ETag`). `version` is required semver: head = highest version, the server bumps automatically by diffing against the head, pre-releases are supported, and `name@range` resolves. | Compare the store's digest instead of rossoctl's own signature. Optional: verify the digest in the fetcher. | A uuid or `name@version` always means the same content, and every content change is detected. Fetches are verifiable and cacheable. Ranges let agents take compatible improvements automatically but not breaking ones. |
| **3. Trusted identity** | `delegated` mode that **verifies** tokens: Kubernetes ServiceAccount tokens (namespace from the token) and Keycloak JWTs (user and roles). Tokens map to store tenants and groups. | Send a projected ServiceAccount token with the audience `skillberry-store`, in two places: the autosync `GET` and the fetcher's `curl`. | The store runs with enforcement on. Every call is attributable to a namespace or user. The open API is closed. |
| **4. Namespaces and sharing in the store** | Enforced binding `scope:` (namespace intersection; untagged objects count as `default`). Tag changes guarded, so adding `namespace:X` requires a grant in X. An ACL API so bindings track namespaces, written through to the config file. | A small reconciler that upserts one binding per `rossoctl-enabled` namespace. | The store, not rossoctl, decides and enforces who sees what. A pod can fetch only what its namespace may see. rossoctl's tag filtering and distribution code can go. |
| **5. Skills that use rossoctl tools** | Streamable-HTTP MCP client. A rossoctl tool importer that creates tools from a tool's MCP schema. Export emits a **runnable** standard-library proxy CLI per tool, which resolves `<tool>-mcp.<pod-namespace>` at run time. Required tools are declared in the skill package. | None required: the proxy runs in the agent pod, and the AuthBridge sidecar handles auth. Optional: read the declared tools to add outbound routes. | Agents get any number of rossoctl tools through the skills list (no single-`mcpToolName` limit), with instructions on when and how to use them. One skill works in every namespace that runs the tools. |

The five stages add up to a few dozen lines in rossoctl. The store becomes the single place where skills are stored, versioned, shared and authorized, and rossoctl stays the place where they run.

### Dreaming

Skill dreaming (feature-flagged) already uses the store as rossoctl's skill-improvement engine. rossoctl sends an agent's trajectories to the store's `ask-runspace` plugin, whose agent writes improved versions back through the store's control MCP. Today those writes are anonymous and unrestricted. Because of the version mismatch above, rossoctl also keeps showing the oldest version while agents silently run the newest.

The stages fix this:
- **Stage 1:** dream output is reflected correctly in rossoctl.
- **Stage 2:** the store enforces "new version, never edit in place", instead of relying on the dream prompt. Dreaming can publish pre-releases (e.g. `1.3.0-dream.1`) that no default range selects. Promoting one becomes the approval step before agents receive it.
- **Stage 3:** the run executes under the triggering user's identity, with a short-lived token limited to creating new versions in that agent's namespace.
- **Stage 4:** new versions inherit the namespace placement of the version they replace.

## Call sites

### 1. Backend autosync poller

`services/skill_autosync.py:98-107`

```python
async def _fetch_registry_skills(registry_url: str) -> List[Dict[str, Any]]:
    """GET {registry_url}/skills/ and return the JSON array."""
    url = registry_url.rstrip("/") + "/skills/"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
```

**Request**
- A plain `GET` with no `headers=` and no query parameters. The store supports server-side `?tags=` filtering, but rossoctl does not use it.
- A non-list response raises `ValueError`.

**Error handling**
- Timeouts and connect errors are transient.
- HTTP status errors and bad payloads are permanent and logged as errors (lines 300-310).

**Configuration**
- `registry_url` comes from ConfigMap `rossoctl-skill-autosync-config` (`core/constants.py:195`).
- The backend reads that ConfigMap from the hard-coded namespace `rossoctl-system` (`skill_autosync.py:50`).
- Helm seeds it (`templates/skillberry-autosync-configmap.yaml`), rendered only when `components.skillberryStore.enabled` and `skillberryStore.autosync.enabled` are set. Keys:
  - `registry-url` defaults to `http://skillberry-store.<release-ns>.svc.cluster.local:<apiPort>`, with `apiPort` 8000.
  - `store-ui-url` is a browser-facing link target used by the rossoctl UI.
  - `allowed-tags` defaults to `""` in Helm. The `POST /skills/autosync` API defaults it to `["rossoctl-approved"]`.

**Polling**
- The loop (`run_skill_autosync_loop`, lines 351-368) runs only with `rossoctl_feature_flag_external_skills`.
- It polls every `sync-interval` seconds, default 30.

**Change detection**
- Each skill gets a content signature: sha256 over version, description, uuid and sorted tags (`_skill_signature`, lines 53-67).
- The signature is stored in annotation `rossoctl.io/registry-skill-hash`.
- A reference ConfigMap is re-patched when the hash or the version changes (`_patch_skill`, lines 214-232).

### 2. Init-container fetcher injected into agent pods

`routers/agents_skills.py:317-345` (`_SKILLBERRY_SH`):

```sh
apk add -q --no-cache curl unzip 2>/dev/null || true
URL="${REGISTRY_URL}/skills/${SKILL_NAME}/export-anthropic"
...
if curl -fsSL --max-filesize 52428800 -o /tmp/skill.zip "${URL}"; then
```

**What the script does**
- Retries 3 times with a 2s delay.
- Unzips the export and copies its first directory into `TARGET_DIR`.
- A `_GENERIC_SH` variant (lines 348-372) handles a tar.gz from a bare URL.

**How it is deployed**
- Both scripts live in ConfigMap `rossoctl-skill-fetcher-scripts` (`_ensure_fetcher_scripts_cm`, lines 380-399).
- The init container runs `/fetcher-scripts/${REGISTRY_TYPE}.sh` on image `alpine:3.21.3` (`SKILL_FETCHER_IMAGE`, `constants.py:192`).
- The image needs network access to the Alpine package mirrors.

Env vars passed to the init container (`agents_skills.py:468-474`):

```python
{"name": "REGISTRY_TYPE", "value": registry_type},
{"name": "REGISTRY_URL", "value": registry_url},
{"name": "SKILL_NAME", "value": registry_skill_name},
{"name": "SKILL_VERSION", "value": registry_skill_version},
{"name": "TARGET_DIR", "value": mount_path},
```

Only `REGISTRY_URL` and `SKILL_NAME` reach skillberry-store, and only in the URL path. `curl` sends no extra headers.

`SKILL_VERSION` is never sent, so every fetch returns whatever the store resolves for the name. `REGISTRY_URL` comes from the per-skill annotation `rossoctl.io/registry-url`.

The fetch runs in an init container, before the AuthBridge proxy is up, so the sidecar does not mediate it.

### 3. UI browse and links

`pages/ImportSkillPage.tsx:228` runs behind a 500 ms debounce, only when `registryType === 'skillberry'`:

```ts
fetch(`${registryUrl}/skills/`, { signal: controller.signal })
```

It is a bare `fetch`, with no `headers` and no `credentials` mode.

The UI also deep-links into the store's web UI. These are plain anchors, not API calls:
- `getSkillberryUiUrl` / `getSkillberryStoreUrl` in `utils/validation.ts:80-115` build the targets.
- They are used in `SkillCatalogPage.tsx`, `SkillDetailPage.tsx` ("Open in store") and `ImportSkillPage.tsx`.
- `AgentDetailPage.tsx:155` links to the store's `/plugins` page, for ask-runspace setup.

### 4. Skill dreaming (feature-flagged)

`services/dreaming.py` and `routers/dream.py` are gated by `rossoctl_feature_flag_dreaming` (`core/config.py:115-126`; Helm `featureFlags.dreaming: false`, "Requires the skillberry-store installed with the ask-runspace plugin").

A dream run reads an agent's recent trajectory spans from Phoenix GraphQL and builds a digest. It then submits the digest to the store:

```python
_RUN_PATH = "/plugins/ask-runspace/run"
_CONTROL_SSE_PATH = "/control_sse"
...
def store_mcp_servers(store_url):
    return {"skillberry-store": {"type": "sse", "url": store_url.rstrip("/") + _CONTROL_SSE_PATH}}
...
resp = await client.post(url, json={"request": request_text, "mcp_servers": mcp_servers})
```

**What the store-side agent is told.** The prompt (`compose_dream_request`, lines 175-193) tells it to improve the involved skills with `mcp__skillberry-store__*` tools. It must treat store objects as immutable: reuse the same name to create a **new version (new UUID)**, add snippets, or add a new skill.

**Status polling.** `get_run_status` (lines 217-233) polls `GET /plugins/ask-runspace/status/{run_id}`, with `run_id` allow-listed by regex.

**Store URL.** `resolve_store_url` (lines 287-300) takes the autosync ConfigMap's `registry-url`.

**State.** Per-agent watermarks live in ConfigMap `rossoctl-dream-state` in `rossoctl-system` (`services/dream_state.py`).

**Inbound routes.** These are Keycloak-role gated, under `/api/v1/dream/{ns}/{agent}`:
- trigger: operator role
- status: viewer role
- run status: viewer role
- thresholds: operator role

New versions flow back to agents through autosync (call site 1). None of the store calls carry headers or tokens.

## Endpoints called

| Endpoint | Method | Caller | Condition |
|---|---|---|---|
| `/skills/` | GET | autosync poller, UI import page | external-skills flag |
| `/skills/{name}/export-anthropic` | GET | init-container fetcher (returns a zip) | per external skill on an agent |
| `/plugins/ask-runspace/run` | POST | `dreaming.py` | dreaming flag |
| `/plugins/ask-runspace/status/{run_id}` | GET | `dreaming.py` | dreaming flag |
| `/control_sse` (MCP tool calls: create skill, create snippet, …) | SSE / JSON-RPC | the RunSpace agent spawned by ask-runspace, from the MCP config rossoctl supplies | dreaming flag |

## Scoping model (client-side only)

rossoctl fetches the *full* skill list, then filters it locally (`skill_autosync.py`):

- **`allowed-tags`** (lines 312-325): a skill passes if it has at least one allowed tag. An empty list means no filtering.
- **`namespace:<X>` tags** (`_get_namespace_tags` lines 110-113, `_namespace_distribution` lines 116-135): these decide which rossoctl namespaces receive a reference ConfigMap.
  - A skill with no `namespace:` tag, or with `namespace:default`, goes to **every** enabled namespace. Enabled means labeled `rossoctl-enabled=true`.
  - `namespace:X` tags send it to each listed namespace that exists. A skill can carry several such tags.
  - Tags naming unknown namespaces are ignored.

Both filters run *after* the response arrives. skillberry-store sees no per-tenant, per-namespace or per-user request context.

Autosync is cluster-wide:
- Enabling it fails with 409 if a skill already exists in any enabled namespace (`routers/skills.py:819-831`).
- Disabling it deletes auto-synced skills in all namespaces (lines 862-899).

User-supplied registry URLs go through an SSRF guard (`routers/skills.py:130-176`). It rejects private, loopback and link-local targets unless they are listed in `SKILL_REGISTRY_ALLOWED_HOSTS`. The Helm-seeded in-cluster URL is written straight to the ConfigMap and is not checked.

## Skill versions

**How the store keeps versions.** Objects with the same name form a chain through their `parent` field (`modules/object_handler.py`).
- A name resolves to the chain's **head**, the object most recently created or updated under that name.
- A PUT on any object, including an old one, re-attaches it as the head.
- When the head is ambiguous at startup, `_find_head_uuid` falls back to the first UUID found.
- The `version` field is free-form, mutable metadata. It plays no part in ordering, and nothing makes it unique.
- Core data can be edited in place: a PUT can change a skill's tool and snippet references, a tool's module or a snippet's text without minting a new uuid.

**`GET /skills/` returns every version, not one entry per name.** It sorts by `modified_at` descending by default (`services/list_query.py`).

**How rossoctl consumes this**

- **Autosync keeps the oldest version's metadata.** It builds `target_by_name = {s["name"]: s for s in target_skills}` (`skill_autosync.py:251`). Later list entries overwrite earlier ones, so each name maps to its **oldest-modified** version. rossoctl therefore records that version's description, version and hash, and distributes the skill by that version's `namespace:` tags.
- **New versions never trigger a resync.** Adding a version does not change the oldest one, so its hash stays the same.
- **The fetcher gets the head.** The init container fetches `/skills/{name}/export-anthropic` by name, which resolves to the **head**. The recorded `SKILL_VERSION` is not sent.
- **Content changes go unnoticed.** rossoctl's change signature covers version, description, uuid and tags, not content. An in-place edit of a tool or snippet is invisible to it.

The result: the skill rossoctl shows and distributes can differ from the skill agents run. Dreaming, which always adds versions under an existing name, makes this the normal case for any dreamed skill.

## Identity on the integration path

**rossoctl's own model**
- Users authenticate with Keycloak OIDC, realm `rossoctl`.
- The backend validates the JWT (`core/auth.py`) and applies a flat role hierarchy, `rossoctl-viewer ⊂ rossoctl-operator ⊂ rossoctl-admin`, through `require_roles(...)`.
- Workloads carry SPIFFE IDs `spiffe://<td>/ns/<namespace>/sa/<sa>`, registered as Keycloak clients.
- The AuthBridge sidecar can token-exchange outbound calls (RFC 8693) per `AgentRuntime.spec.auth.outbound`.

None of this reaches skillberry-store:
- The autosync poller has no user context and sends no token.
- The init container runs before the AuthBridge sidecar and sends no token.
- The dreaming client sends no token, and the MCP config it hands to the RunSpace agent has no `headers`.

**skillberry-store's side.** It ships an access-control subsystem (`src/skillberry_store/access_control/`, [design](design/access-control.md)) with modes `disabled` and `standalone`; `delegated` is reserved and rejected at startup. rossoctl's Helm chart deploys the store (`templates/skillberry-store.yaml`, image `ghcr.io/skillberry-ai/skillberry-store:0.2.0`) without an access-control config, so it runs in `disabled` mode.

Consequences:

- **Under `standalone`, every rossoctl call fails with 401.** On top of that, the MCP URL dreaming uses, `/control_sse`, does not exist in `standalone` mode. The store mounts only per-tenant `/control_sse/<tenant>` surfaces there (`fast_api/server.py:400-450`).
- **In `disabled` mode the whole store API is anonymous**, including `DELETE /admin/purge-all` and `POST /admin/restore`.
  - The chart's `HTTPRoute` exposes only the UI port (8002) outside the cluster.
  - However, the store's Vite server proxies every non-`/ui` path to the API (`ui/vite.config.ts:76-99`).
  - So that route also exposes the full API to anyone who can reach `skillberry-store.<domain>`.
- The chart's `skillberryStore.extraEnv` example sets `SBS_API_TOKEN` from a Secret. That configures the store side only; no rossoctl client sends a token.

## Implication for skillberry-store

If skillberry-store needs to authorize or partition responses by tenant, the rossoctl integration gives it no identifier to key on. Server-side scoping needs changes on both sides:
- rossoctl must attach an identity on each of the three call paths.
- skillberry-store must accept an identity it did not mint itself.

[Future integration based on extended access control](#future-integration-based-on-extended-access-control) works this through.

## Write direction

rossoctl has **no direct write path** to skillberry-store's resource endpoints. No rossoctl code issues `POST`/`PUT`/`PATCH`/`DELETE` against `/skills`, `/tools` or `/snippets`.

There is one **indirect write path**: skill dreaming.
1. rossoctl `POST`s a job to the store's `ask-runspace` plugin.
2. The job runs a Claude Code agent inside the store's environment.
3. That agent receives the store's control MCP (`/control_sse`) and creates skills, skill versions and snippets in the store.
4. The writes are anonymous, as everything is in `disabled` mode.
5. Under `standalone` they would run as whatever tenant the plugin resolves, not as the rossoctl user who triggered the dream.

Notes on false positives to watch for:

- **Naming trap**: `registryUrl` in `agents_*.py`, `tools.py` and `shipwright.py` refers to a *container image registry* (e.g. `registry.cr-system.svc.cluster.local:5000`, `quay.io/…`), not skillberry-store. It is distinct from `SKILL_REGISTRY_URL_ANNOTATION`.
- **`routers/skills.py`** has `POST`/`DELETE` FastAPI handlers. They are **inbound** routes on the rossoctl backend that change local ConfigMaps through the Kubernetes API. They do not proxy to skillberry-store, and the file imports no HTTP client (only `socket`, `ipaddress` and `urllib.parse` for the SSRF guard).
- **UI write calls**: all 39 `method: 'POST'|'PUT'|'PATCH'|'DELETE'` sites go through `apiFetch()`. It prepends `API_CONFIG.baseUrl` (the rossoctl backend) and attaches the Keycloak bearer (`services/api.ts:79-100`). None of them uses `registryUrl`.
- **Shell scripts**: their `curl -X` writes target Keycloak or the rossoctl backend, not skillberry-store.
- **No SDK**: no skillberry SDK or client wrapper (`skillberry_client`, `skillberry_store_sdk`) is imported anywhere.
- **Other backend HTTP clients** target other services:
  - `chat.py`, `acp_bridge.py` and `sidecar_manager.py` call agents.
  - `simulation_harness_client.py` calls the simulation harness.
  - `contexts.py` calls the Context Service.
  - `core/auth.py` calls Keycloak.

Search patterns used:
- `skillberry`, `registry_url`, `registryUrl`, `export-anthropic`, `/skills/`, `ask-runspace`, `control_sse`
- `(httpx|requests|urllib)\.(post|put|patch|delete)`
- `method: '(POST|PUT|PATCH|DELETE)'`
- `curl.*(-X|--request)`
- `fetch(...registryUrl`

skillberry-store is the authoritative registry. rossoctl consumes from it and materializes reference ConfigMaps. The only content it produces in the store comes from the dreaming agent.

## Related rossoctl resources

### Tools — workloads described by an `AgentRuntime` CR

Tools are a managed resource type in rossoctl, but they are **not** stored in skillberry-store or in a database. Each tool consists of:
- A `Deployment` or `StatefulSet` labeled `rossoctl.io/type=tool`.
- A Service named `<tool>-mcp` (`TOOL_SERVICE_SUFFIX`), which serves MCP over streamable HTTP at `/mcp`.
- An `AgentRuntime` CR with `spec.type: tool`.
- For source builds, Shipwright `Build`/`BuildRun` resources.
- An `HTTPRoute` for exposure.

`routers/tools.py:1170-1217` (`_ensure_tool_agentruntime`) calls the Kubernetes API directly:

```python
manifest = {
    "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
    "kind": "AgentRuntime",
    ...
    "spec": {"type": RESOURCE_TYPE_TOOL,
             "targetRef": {"apiVersion": "apps/v1",
                           "kind": kind_map.get(workload_type, "Deployment"),
                           "name": name}},
}
kube.create_custom_resource(group=CRD_GROUP, version=CRD_VERSION,
                            namespace=namespace, plural=AGENTRUNTIMES_PLURAL,
                            body=manifest)
```

**Constants** (`core/constants.py`):
- `CRD_GROUP` = `agent.rossoctl.dev`
- `CRD_VERSION` = `v1alpha1`
- `AGENTRUNTIMES_PLURAL` = `agentruntimes`
- `RESOURCE_TYPE_TOOL` = `tool`
- `TOOL_SERVICE_SUFFIX` = `-mcp`

**Builds.** Shipwright manifests are built in `services/shipwright.py` and `services/shipwright_builds.py`, and driven from `tools.py`.

**The `AgentRuntime` CRD.** It lives in `rossoctl/operator` (`api/v1alpha1/agentruntime_types.go`). It is a runtime/identity overlay on a workload:
- `type` (`agent|tool`), `targetRef`
- `authBridgeMode`, `mtlsMode`, `tlsBridgeMode`, `egressEnforcement`
- `auth.outbound[]` token-exchange routes
- `pluginPreset`, `plugins`

It has no tool-schema fields.

**Backend tool APIs.** The backend can list a tool's MCP schemas and invoke it, using the MCP SDK with `streamablehttp_client` and `headers={}`:
- `POST /tools/{ns}/{name}/connect` (`tools.py:2435-2513`) returns `{name, description, input_schema}` per MCP tool.
- `POST /tools/{ns}/{name}/invoke` (`tools.py:2516`) calls a tool.

There is no namespace-wide tool-schema catalog.

**Optional extras.**
- The Kuadrant MCP Gateway (experimental, `charts/rossoctl/templates/mcp-gateway.yaml`) can aggregate tools behind `mcp-gateway-istio.gateway-system.svc.cluster.local:8080/mcp`, registered with `MCPServerRegistration`.
- Simulated tools generated from OpenAPI live in `routers/simulation.py`.

**Contrast with skills.** Skills persist as Kubernetes ConfigMaps labeled `rossoctl.io/type=skill` (`routers/skills.py`):
- A **local** skill keeps one data key per file. `SKILL.md` is required, and a `/` in a path becomes `.` in the key.
- An **external or auto-synced** skill is a reference ConfigMap with `data={}`. It carries labels `rossoctl.io/source=external`, `rossoctl.io/registry-type`, `rossoctl.io/auto-sync=true` and `app.kubernetes.io/managed-by=rossoctl-autosync`, and annotations for registry URL, skill name, version, hash and description.
- The skill content is fetched at pod start.

Tools are workloads plus a CR; skills are ConfigMaps that point at an external source.

### Operator CRDs

Group `agent.rossoctl.dev/v1alpha1` (`charts/operator/crds/`):

| Kind | Purpose |
|---|---|
| `AgentRuntime` | Runtime, identity and AuthBridge config for an agent or tool workload. Status carries `card`, `configuredPods`, conditions and `linkedSkills`. `linkedSkills` is copied from the workload's `rossoctl.io/skills` annotation behind the `SkillDiscovery` feature gate; the operator reads that annotation and never sets it. |
| `AgentCard` | Deprecated in favor of `AgentRuntime.status.card`. Its `skills[]` are A2A skill *metadata* (id, name, tags, examples), not SKILL.md skills. |
| `AuthorizationPolicy` | Rego policy files scoped `global`, `namespace` or `client`. The operator's bundle service compiles them into OPA bundles for AuthBridge (data-plane authorization). |

There is no Skill, Tool or Prompt CRD.

### Snippets / prompts — not a managed resource

Snippets and prompt templates are **not** first-class resources in rossoctl.

- No prompts, snippets or templates router exists. `routers/` contains:
  - `acp.py`, `auth.py`, `chat.py`, `config.py`, `contexts.py`, `dream.py`, `namespaces.py`, `shipwright.py`, `simulation.py`, `skills.py`, `tools.py`
  - the agent modules `agents.py`, `agents_authbridge.py`, `agents_create.py`, `agents_env.py`, `agents_finalize.py`, `agents_manifests.py`, `agents_migration.py`, `agents_models.py`, `agents_shipwright.py`, `agents_skills.py`, `agents_status.py`
- No CRD, ConfigMap type, database table or external service stores prompt templates or reusable snippets.
- Prompts are assembled at runtime inside agent code. For example, `deployments/sandbox/skills_loader.py` builds a system prompt from CLAUDE.md plus skills; `skill_pack_loader.py` sits next to it.
- The only prompt rossoctl itself authors is the hard-coded dreaming prompt in `services/dreaming.py`.
- Prompts as composable components appear only in draft research docs (`docs/_internal/research/composable-agents-design.md`, `dynamic-agent-composition.md`).

### Backend persistence inventory

| Resource | Storage |
|---|---|
| Skills | Kubernetes ConfigMaps (`rossoctl.io/type=skill`). Local skills hold files; external and auto-synced skills are empty references into skillberry-store. |
| Skill fetcher scripts | ConfigMap `rossoctl-skill-fetcher-scripts` |
| Autosync config | ConfigMap `rossoctl-skill-autosync-config` (`rossoctl-system`) |
| Dream state | ConfigMap `rossoctl-dream-state` (`rossoctl-system`) |
| Tools | Deployment/StatefulSet + `-mcp` Service + `AgentRuntime` CR + Shipwright Build resources |
| Agents | Deployment/StatefulSet/Sandbox + `AgentRuntime` CR (see `routers/agents_*.py`) |
| Agent contexts (workspace, memory, knowledge, artifacts) | External Context Service (`routers/contexts.py`, `settings.context_service_url`), PVC-backed |
| Chat sessions / events | PostgreSQL via raw `asyncpg` (`services/session_db.py`, `models/event.py`) |
| Snippets / prompts | *(not stored; assembled at runtime)* |

PostgreSQL is used **only** for chat sessions and events, not for any control-plane resource type.

## Can a skill use tools? Agent-level composition

Two different "tool" concepts are in play:

- **skillberry-store tool**: a Python (or bash) module bundled *inside* the exported skill zip. Skills reference these by `tool_uuids` (see `gather_export_inputs`, `src/skillberry_store/services/skills_service.py:732`, and `export_anthropic`, `:781`). rossoctl sees them only as files under the agent's skill directory once the init container unpacks the zip.
- **rossoctl tool**: a running MCP server workload plus an `AgentRuntime` with `spec.type: tool`. It is a live networked service, not code.

Whether a skill can use a rossoctl tool comes down to how agents combine the two at runtime, and the wiring is **asymmetric**.

### Agent request model

`routers/agents_models.py:123` (`CreateAgentRequest`):
- `skills: Optional[List[str]] = None` (line 131): a list of skill ConfigMap names. This is first-class.
- `mcpToolName: Optional[str] = None` (line 133): a **single** MCP tool reference.
- `envVars: Optional[List[EnvVar]] = None` (line 130): free-form. Power users add extra tool URLs here.

There is no `tools: List[str]`, `toolRefs` or `mcpTools` array.

The `AgentRuntime` CRD has no `tools`, `linkedTools` or `mcpServers` field either. Its only skill-related field is `status.linkedSkills`, derived from the `rossoctl.io/skills` workload annotation. The backend sets that annotation to `json.dumps(request.skills)` (`agents_manifests.py:395, 596, 742, 850`).

### Skill wiring at runtime

`routers/agents_skills.py` turns each name in `request.skills` into one of:

- a **ConfigMap volume** mounted read-only at `{AGENT_SKILLS_MOUNT_ROOT}/<cm_name>`, for local skills (`_get_linked_skill_mounts`, lines 263-302; `AGENT_SKILLS_MOUNT_ROOT` = `/app/skills`); or
- an **init-container fetch** into an `emptyDir`, for external-registry skills (`_get_external_skill_data`, lines 402-499, running the `skillberry.sh` script).

All resolved paths are joined into a `SKILL_FOLDERS` env var (`agents_manifests.py:109-112`). The user can override it through `envVars`.

### Tool wiring at runtime: env var only

`services/agent_env_defaults.py`:

```python
# :19-27
def get_mcp_tool_url(tool_name, namespace, kube):
    service_name = f"{tool_name}{TOOL_SERVICE_SUFFIX}"
    port = lookup_service_port(service_name, namespace, kube, DEFAULT_IN_CLUSTER_PORT)
    if settings.is_running_in_cluster:
        base = f"http://{service_name}.{namespace}.svc.cluster.local:{port}"
    else:
        base = f"http://{tool_name}.{settings.domain_name}:8080"
    return f"{base}/mcp"

# :93-102
if mcp_tool and "MCP_URL" not in existing:
    env_vars.append(EnvVar(name="MCP_URL",
        value=get_mcp_tool_url(mcp_tool, request.namespace, kube)))
```

**How it is wired**
- This is gated by `rossoctl_feature_flag_agent_import_defaults`, default off.
- There is no sidecar, no MCP-servers JSON, no system-prompt injection and no CRD relationship.
- The agent process reads `MCP_URL` and connects over cluster DNS.

**More than one tool**
- The docs describe a convention of `MCP_URLS` (comma-separated) or pointing `MCP_URL` at the MCP Gateway. The agent framework interprets this, not rossoctl.
- Otherwise, using several tools means the user edits `envVars` by hand.

**Auth on tool calls.** The agent's AuthBridge sidecar exchanges the caller's token for one scoped to the tool, but only for destinations listed in `AgentRuntime.spec.auth.outbound`.

### Bottom line

- **A skill has no structural way to declare "I need tool X"** on the rossoctl side. The skill is a ConfigMap of files, or a pointer to a zip.
- **An agent can combine skills and rossoctl tools**, but lopsidedly. Skills are a first-class list. Tools are a single MCP URL env var, plus whatever is added to `envVars`.
- If a skill's instructions reference a tool, it works only when the agent hosting the skill was separately configured with a matching `mcpToolName` and, under token exchange, a matching outbound route. Nothing declares a dependency between skill and tool, and the operator neither enforces nor resolves one.

## Future integration based on extended access control

This section looks at three extensions to skillberry-store's access control:
- the reserved `delegated` mode;
- namespace scoping on bindings;
- a dynamic ACL API.

For each it asks what that buys the rossoctl integration. The store-side baseline is [design/access-control.md](design/access-control.md):
- Roles are pure `(resources, verbs)` bundles. Bindings attach tenants or groups to roles.
- Bindings already accept a `scope:` block (`namespaces`, `resourceNames`), which is parsed and not enforced.
- Namespaces are `namespace:<name>` tags on objects.
- The PEP is one FastAPI dependency whose bearer-resolution step (`access_control/deps.py:96-107`) is the documented seam for `delegated`.

### What a "tenant" is in rossoctl

Mapping rossoctl's tenants onto the store depends on what a rossoctl tenant is. **rossoctl has no tenant object.** Neither repo uses the word in code.

- **Users** are Keycloak identities. Their realm roles (viewer/operator/admin) are global, and groups are not used. The backend does not tie a user to a namespace: any operator can act in any enabled namespace, and namespace lists are not filtered per user.
- **The namespace is the de-facto tenant.** A Kubernetes namespace labeled `rossoctl-enabled=true` is the unit of:
  - placement (agents, tools and skill ConfigMaps live in it);
  - workload identity (the `ns/<namespace>` segment of every SPIFFE ID);
  - per-namespace AuthBridge config;
  - data-plane policy (`AuthorizationPolicy` with `scope: namespace`, e.g. "agents in NS-Finance may only talk to NS-Finance").
- **The one namespace-aware user check** in the backend is the ACP WebSocket (`routers/acp.py:55-79`). It requires the token's `aud` or `azp` to contain the namespace name, which implies one Keycloak client per namespace.
- **A namespace-tier "Tenancy Isolation" model** is planned in `docs/_internal/access-control/zero-trust.md` (draft).

So two identities can flow from rossoctl to the store:
- **Namespace identity**: the calling workload's SPIFFE ID, or a per-namespace client's `azp`. This applies to agent pods fetching skills and to dream runs on behalf of an agent.
- **User identity**: the Keycloak `sub` plus realm roles. This applies to UI and backend operations on behalf of a person.

The cleanest mapping uses both:

| rossoctl | skillberry-store |
|---|---|
| enabled namespace `team1` | tenant `ns:team1` (and store namespace `team1`) |
| realm role `rossoctl-viewer` / `-operator` / `-admin` | group of the same name → bound to `reader` / `content-author`+`tool-runner` / `admin` |
| Keycloak user `alice` | tenant `user:alice` (for audit and attribution); permissions come mostly from groups |

### 1. Delegated mode with rossoctl authentication

**Proposal.** Implement `delegated` so that skillberry-store trusts identities asserted by rossoctl, and stop draining the store into rossoctl.

**Does that make sense? Yes, with one correction.** The store design's `delegated` contract is *trusted headers* (`X-Tenant-Id`, `X-Tenant-Groups`), anchored by an mTLS peer identity. That fits only one of rossoctl's three call paths:

| Path | Caller | Trustworthy identity available | Fit |
|---|---|---|---|
| Autosync / UI catalog | rossoctl backend | Backend's SPIFFE ID or `rossoctl-api` client-credentials token; for UI-originated calls, the user's Keycloak JWT | Trusted headers work if the store can authenticate the backend as the only header-asserting peer |
| Skill fetch at pod start | init container in an agent pod | Projected ServiceAccount token or SPIFFE JWT-SVID (`ns/<ns>/sa/<sa>`) | Headers do **not** work. The pod is not trusted to assert its own tenant, so the store must verify a token. |
| Dreaming | store-side RunSpace agent, triggered by the backend | The triggering user's JWT (forwarded by the backend), or a token the store mints for the run | Needs a token, plus a store-side rule for whose authority the run uses |

`delegated` should therefore be defined as "identity established by an external IdP; the store **verifies** it". There are two verifiers behind the same seam:
- **(a) JWT/OIDC.** Validate signature, issuer, expiry and audience against rossoctl's Keycloak JWKS (the same endpoint rossoctl's `core/auth.py` uses). Map configured claims to `tenant_id` and `groups`: for example `azp`, the SPIFFE namespace segment, or `sub` → tenant, and `realm_access.roles` → groups. This is the "Providers: OIDC / JWT-with-JWKS" later phase of the store design, merged into `delegated`.
- **(b) Trusted headers** from an mTLS-authenticated peer, for deployments with an auth gateway in front.

Option (a) is what rossoctl needs. The issuer can be Keycloak, or the cluster's own ServiceAccount issuer. A projected ServiceAccount token with audience `skillberry-store` carries the pod's namespace in its claims, verifiable against the cluster's OIDC JWKS. It needs no Keycloak or SPIFFE setup, so it is the smallest change for rossoctl's backend and fetcher. The store then gets an audience of its own (e.g. `skillberry-store`). Agent egress already supports exactly this: when the store host appears in an agent's `AgentRuntime.spec.auth.outbound`, AuthBridge exchanges the user's token for one with `aud=skillberry-store`, `sub=<user>` and `act.sub=<agent SPIFFE ID>`. The store would see both who the agent acts for and which agent it is.

**Delegating skill management instead of draining.** rossoctl does not copy skill *content* even today; reference ConfigMaps are empty and content is fetched at pod start. What it drains is:
- the **catalog** (the full `GET /skills/` every 30 s);
- the **visibility policy** (`allowed-tags` plus `namespace:` distribution, computed in rossoctl);
- a **per-namespace mirror** (one ConfigMap per skill per namespace, with create, patch and delete reconciliation).

With `delegated` plus namespace scoping (§2 below), all three move to the store:
- **Catalog**: the rossoctl skill list and the import page query the store *as the namespace*. They get back exactly what that namespace may see, and paging, search and facets are served by the store. The 30 s poll, the hash annotations, the 409-on-enable rule and the delete-all-on-disable behavior go away.
- **Agent skill references** name store skills directly (name, or name plus version/uuid). The init container fetches them with the pod's token, and the store authorizes the fetch. `export-anthropic` is already gated by `("skills", "get")`.
- **Policy** lives in one place, in the store. rossoctl only maps its identity onto store tenants and groups.

**What still argues for some Kubernetes-side object.** `request.skills` and the `rossoctl.io/skills` annotation feed `AgentRuntime.status.linkedSkills`, and operators expect `kubectl` visibility. A thin **projection** may stay, but the store now decides what it contains, and rossoctl only mirrors it. See [Better skill and prompt integration](#better-skill-and-prompt-integration), stage 2, for a typed version of that projection.

**Additional value**

1. **Closing the anonymous write hole.** The store must run in `disabled` mode today, so the whole API is anonymous inside the cluster. Through the Vite proxy behind the UI `HTTPRoute`, it is anonymous from outside too, including `purge-all` and `restore`. `delegated` lets the store run with enforcement on and still serve rossoctl.
2. **Accountable dreaming.** A dream run currently writes anonymously, with unrestricted create rights. Under `delegated`:
   - The store mints the RunSpace agent's MCP token from the *triggering* identity, with a narrow role (create new versions of skills in the agent's namespace only). The plugin-identity machinery already mints such tokens (`StoreAPI.internal_token`, `mcp_sse_config`).
   - Every new version is attributed to the user and agent that caused it.
3. **Per-namespace execution control.** The store's `execute` verb (`/tools/{id}/execute`, vMCP `start`) becomes grantable per namespace, which matters once store tools proxy rossoctl tools (next section).
4. **Single sign-on to the store UI.** rossoctl's UI already deep-links into the store ("Open in store"). With Keycloak validation in the store, the same login works there, and the store needs no separate user list (`standalone.users`) for rossoctl deployments.
5. **Audit.** Store-side decisions log the rossoctl user and namespace instead of nothing.

**What it takes**

- **Store**
  - Accept `mode: delegated` and add the JWT verifier at the `deps.py` seam (small).
  - Rework the per-tenant control MCP mounts (`server.py:415-450`). They are built at startup from known tenants, and delegated tenants are not known in advance. Use a single `/control_sse` with per-call enforcement (already how tool calls are gated), or create mounts lazily per tenant.
  - Keep `internal_token` minting for plugins in delegated mode.
  - Disable `/auth/login` in delegated mode.
- **rossoctl**
  - Attach a token on each path: client credentials in the autosync loop, a projected or SPIFFE token in the fetcher init container, and the user's token on dream triggers.
  - Add the store as an outbound audience.
  - Make the dreaming MCP config carry `headers`.

### 2. Namespace isolation and sharing

**How rossoctl isolates and shares**

- **Isolation is placement.**
  - Every agent, tool and local skill lives in a namespace.
  - Workload identity, AuthBridge config and copied Secrets are per namespace.
  - Data-plane calls can be restricted per namespace with `AuthorizationPolicy` Rego (`scope: namespace`, combined with global and client tiers, default deny).
  - The control plane does **not** isolate users by namespace. That is still the planned tier in `zero-trust.md`.
- **Sharing exists only for skills, and only through skillberry-store tags.**
  - No `namespace:` tag, or `namespace:default`, means shared with every enabled namespace.
  - One or more `namespace:X` tags means shared with exactly those namespaces.
  - `allowed-tags` (default `rossoctl-approved`) is a cluster-wide publication gate.
  - Agents and tools are not shared across namespaces. Their reachability across namespaces is a network and data-plane policy question.

**Mapping into skillberry-store.** The store deliberately uses the same representation: namespaces are `namespace:<name>` tags on objects, not properties of tenants. rossoctl's sharing rules therefore translate directly into enforced `scope:` on bindings.

| rossoctl concept | skillberry-store mechanism |
|---|---|
| Namespace `team1` | binding `ns-team1`: subjects `[tenant ns:team1]`, roles `[reader, tool-runner]`, `scope.namespaces: [team1, default]` |
| Skill tagged `namespace:team1`, `namespace:team2` (shared with two namespaces) | visible to any subject whose scope intersects `{team1, team2}` |
| Skill with no namespace tag / `namespace:default` (shared with all) | store convention: untagged objects belong to `default`, and every namespace binding includes `default` in its scope |
| `allowed-tags: [rossoctl-approved]` (publication gate) | a further scope filter: tags (already listed as a future `scope:` filter), or better the object's lifecycle `state` (e.g. only `approved` visible to runtime subjects) |
| Operator in `team1` authors a skill | binding with `content-author` scoped to `team1` |

Design points this mapping surfaces for the store's `scope:` work:

1. **Intersection, not AND.**
   - A subject sees an object when *the object's namespace set intersects the subject's scope*.
   - The current `_matches_tags` is AND-only (`services/list_query.py:29-38`), which is the gotcha the ACL design calls out.
   - rossoctl's multi-tag sharing makes the intersection rule mandatory.
2. **Defining "untagged".**
   - rossoctl treats untagged as shared with all. A naive scope filter would make untagged objects invisible to every scoped subject.
   - The store should define untagged as `namespace:default` explicitly.
   - Dropping the last namespace tag must not hide an object or widen its reach by accident.
3. **Tag writes are sharing decisions.**
   - Tags are free-form, so anyone with `update` on an object can add `namespace:prod` and publish it into another namespace.
   - With scope enforced, adding or removing a `namespace:X` tag must require a grant (e.g. `create`) *in X*.
   - This is the store equivalent of "you can only place objects into namespaces you can write to".
4. **Versions inherit placement.**
   - Dreaming creates new immutable versions under the same name. A new version must inherit the namespace tags of the version it supersedes.
   - Otherwise an improvement in `team1` silently drops out of `team1`, or leaks into `default`.
5. **Composite objects.**
   - Exporting a skill bundles its tools and snippets (`gather_export_inputs`).
   - Either a grant on the skill covers its components (closure semantics, simplest for agents), or each component is checked.
   - Mixed placement (skill in `team1`, tool only in `team2`) needs a defined answer before scope is enforced.
6. **Per-user namespace roles.**
   - rossoctl's user roles are global today, so the store can be ahead of rossoctl here.
   - Keycloak groups such as `/ns/team1/operator` can be mapped to store groups and bound with `scope.namespaces: [team1]`.
   - The store would then enforce the per-namespace user tier rossoctl's own zero-trust doc plans, at least for skills.

Once scope is enforced, rossoctl needs none of its own distribution logic. "Which skills does `team1` see" becomes `GET /skills/` as `ns:team1`.

### 3. Dynamic ACL configuration API

**Proposal.** An API for roles, permissions, scopes, role bindings and tenants. It replaces "edit YAML and restart" and makes the ACL object model reachable at runtime, which the ACL design anticipated: "the same in-memory data model must be reachable later via a REST config API".

**Why it matters for rossoctl.** rossoctl's tenancy is dynamic:
- Namespaces are enabled by label.
- They are created by Helm or by users.
- They come and go at runtime.

With a static YAML file, every namespace onboarding means an edit and a store restart. In `standalone` the restart also drops every in-memory session.

**Use cases**

1. **Namespace onboarding and offboarding.**
   - A rossoctl reconciler watches `rossoctl-enabled` namespaces.
   - For each one it upserts the binding `ns-<X>`: tenant `ns:<X>`, roles `[reader, tool-runner]`, `scope.namespaces: [<X>, default]`.
   - It deletes the binding when the namespace is disabled.
2. **Extrapolating rossoctl's ACL.**
   - rossoctl's role model is small and static: three hierarchical roles and the namespace dimension. The *roles* can be created once, via API or the shipped YAML:
     - `rossoctl-viewer` → reader-equivalent
     - `rossoctl-operator` → content-author plus tool-runner
     - `rossoctl-admin` → admin
     - `rossoctl-agent-runtime` → `skills:get/list` only, for skill fetch
     - `rossoctl-dreamer` → `skills:create`, `snippets:create`, scoped
   - The dynamic part is **bindings and scopes**, which follow namespaces and Keycloak groups. So the API's value is concentrated in bindings, not role CRUD.
3. **Time-bound grants.**
   - A dream run needs write access to one namespace for minutes.
   - A binding with an expiry, created at trigger time, is safer than a standing `content-author` grant.
4. **Delegated-mode trust settings.**
   - In `delegated` mode tenants are not provisioned; they arrive in tokens.
   - The API's "tenants" surface is then really the **claim mapping and trust configuration**: issuer, JWKS URL, audience, and which claim gives the tenant and which the groups.
   - Being able to configure these at runtime matters when the Keycloak realm or client layout changes.
5. **Access review.**
   - A `can-i` style endpoint, e.g. `POST /auth/access-review {subject, resource, verb, object}`, modeled on SubjectAccessReview.
   - The rossoctl UI could use it to show "which namespaces see this skill" and to grey out actions, without copying the policy.

**Persisting across reboots.** Two complementary approaches:
- **Store-side persistence.** API writes go through to the ACL file on the store's PVC. Use the same atomic, comment-preserving round-trip write `scripts/setup_user.py` already does, or a store-managed file next to it. The store restarts with what rossoctl last programmed.
- **Idempotent declarative reconciliation from rossoctl.**
  - The reconciler re-asserts desired state at startup and on change.
  - It does so with whole-object `PUT` calls on objects it owns, marked e.g. `managed_by: rossoctl`. Operator-authored objects are left untouched.
  - This is cheap and self-healing even if the store's file is lost.

  With both in place, rossoctl does not *need* to reprogram the store at every reboot, and is still safe when it does.

**Requirements this places on the API**

- **Optimistic concurrency.** A version or `resourceVersion` on each object, so rossoctl and a human editing the same file cannot silently overwrite each other.
- **Escalation prevention.** A caller may not create a binding granting permissions it does not itself hold, as in Kubernetes' `escalate`/`bind` verbs. The rossoctl reconciler should get a role over `rbac` objects limited to its managed partition, not `admin`.
- **Live reload inside the store.** The ACL config is read once in `SBS.__init__` and captured by the enforcement dependency and the per-tenant MCP mounts. A dynamic API needs a swappable config object and dynamic MCP mounts. This is the same work `delegated` mode needs, and the two should land together.

**An alternative to weigh.** The store could watch a Kubernetes object (a ConfigMap or a small CRD) holding the bindings, instead of rossoctl calling a store API. That is GitOps-friendly and persisted by etcd, but it ties the store to Kubernetes. A REST API keeps the store platform-neutral, and a thin rossoctl controller can still offer the declarative Kubernetes face on top of it.

### Summary

| Extension | Unblocks for rossoctl | Depends on |
|---|---|---|
| `delegated` (JWT/OIDC verification) | Store runs with enforcement on; attributable dreaming writes; SSO to the store UI | rossoctl attaching tokens on all three paths; dynamic MCP mounts |
| Namespace `scope:` enforcement | Store-side visibility per namespace; removes rossoctl's catalog drain and distribution logic | Intersection semantics, untagged = `default`, guarded namespace-tag writes |
| Dynamic ACL API | Bindings that follow rossoctl namespaces and Keycloak groups; time-bound grants; access review | Live config reload; write-through persistence; escalation checks |

The three are most valuable together. `delegated` without scope gives only role-level, all-or-nothing access. Scope without a dynamic API cannot follow rossoctl's namespaces.

## Better skill and prompt integration

### Stage 1: store skills that include rossoctl tools through proxy scripts

**Goal.** A skillberry-store skill bundles a proxy script per rossoctl tool. Agents in rossoctl that receive the skill can then call rossoctl tools through it.

**How the store proxies remote tools**

The mcp-importer plugin (`plugins/skillberry-plugin-mcp-importer`, `POST /plugins/mcp-importer/import-tools`) does this. The simulate plugin uses the same pattern with its harness.

1. **Import.** The plugin connects to an MCP server, lists its tools, and creates one store tool per remote tool, with `packaging_format: "mcp"` and `packaging_params: {mcp_url, mcp_tool_name}`. It then creates a skill aggregating them.
2. **The stored module is a stub.** It is generated by `mcp_content()` (`fast_api/server_utils.py:8-51`) and holds only a function signature and docstring, with no body.
3. **Execution happens in the store.** `FileExecutor` sees `packaging_format == "mcp"` and opens an MCP session to `mcp_url` itself (`modules/file_executor.py:382-540`). vMCP servers re-expose these tools the same way.

**Why this does not yet work for rossoctl**

1. **Exported proxies are not runnable.**
   - `export-anthropic` writes the stub to `scripts/<tool>.py`, and does not include the tool manifest (`packaging_params`).
   - An agent in rossoctl receives a script that defines a function with no body and no entry point.
   - The proxy works only when the store executes it, not when the agent does.
2. **Transport mismatch.**
   - The store's MCP client is SSE-only (`sse_client` in both `file_executor.py` and the importer).
   - rossoctl tools serve **streamable HTTP** at `/mcp`, as rossoctl's own backend uses `streamablehttp_client`. So does the MCP Gateway.
   - The importer cannot list a rossoctl tool, and the store cannot execute one.
3. **Location.**
   - A rossoctl tool's URL is namespace-specific, `http://<tool>-mcp.<ns>.svc.cluster.local:<port>/mcp`.
   - A skill shared across namespaces cannot carry one fixed `mcp_url`.
4. **Auth.**
   - The store's remote-tool path has no field for credentials or headers.
   - rossoctl tools behind AuthBridge may require a token exchanged for the tool's audience.

**What stage 1 needs in skillberry-store**

1. **A self-contained proxy at export time.**
   - For tools with a remote packaging, the exporter emits an executable script, not the stub. It is a CLI (`python scripts/<tool>.py --arg value` or JSON on stdin) that performs `initialize` + `tools/call` over streamable HTTP and prints the result. Agents in Anthropic-format skills run scripts; they do not import functions.
   - Ideally it depends only on the standard library (`urllib` + JSON-RPC), since agent images may not have the `mcp` package.
   - The store already has the generator hook: the stub is regenerated from the manifest at export (`get_module`).
2. **Late-bound tool location.**
   - Store a rossoctl tool reference rather than a URL, e.g. `packaging_params: {rossoctl_tool: "weather-tool", mcp_tool_name: "get_weather", namespace?: "team1"}`.
   - The proxy resolves the endpoint at run time, in this order:
     1. explicit env (`ROSSOCTL_TOOL_WEATHER_TOOL_URL`);
     2. the MCP Gateway when configured;
     3. `http://<tool>-mcp.<ns>.svc.cluster.local:<port>/mcp`, with `<ns>` read from `/var/run/secrets/kubernetes.io/serviceaccount/namespace`.

     The same skill then works in every namespace that runs the tool.
3. **No credentials in the proxy.**
   - The script runs in the agent container, and its egress goes through the AuthBridge sidecar.
   - When the tool host is in the agent's `spec.auth.outbound`, the sidecar attaches a token exchanged for that tool, carrying the user as `sub`.
   - The store should not invent a secret mechanism for this path.
4. **Streamable-HTTP support in the store's MCP client.** This covers importing, and executing in the store for testing and evaluation. Pick the transport per `packaging_params`, or by probing.
5. **A rossoctl tool importer.**
   - It is a variant of mcp-importer that lists tools through rossoctl's `POST /tools/{ns}/{name}/connect`, which returns `{name, description, input_schema}`, or directly over streamable HTTP.
   - It creates the reference-packaged tools, plus a skill with instructions for using them.
6. **A declared dependency in the export.**
   - Write the required rossoctl tools into the skill package, e.g. SKILL.md frontmatter `metadata.requires-tools: [weather-tool]` or a small `requirements.json`.
   - rossoctl can then act on it at agent creation: validate that the tools exist in the namespace, inject `MCP_URLS` or outbound routes, and show the dependency in the UI.

**Value**

- **Many tools per agent through the skills list.**
  - rossoctl's agent model allows one `mcpToolName`, but any number of skills.
  - A skill that carries tool proxies gives an agent several rossoctl tools without per-agent MCP configuration.
- **Tools loaded with the skill.**
  - Tool descriptions are disclosed progressively, with the skill, instead of every MCP tool schema sitting in the agent's context.
  - The skill's instructions can say *when and how* to use a tool, which raw MCP listings cannot.
- **Optimizable tool use.**
  - Dreaming already rewrites skills from trajectories.
  - With tool usage inside skills, it can improve instructions around real rossoctl tools, and the store can evaluate those skills against the live tools.
- **Policy stays with the tool.** The real tool call still goes through rossoctl's identity and OPA path. The proxy is only a client.

**Caveats**
- The proxy turns structured MCP calls into script invocations. The LLM sees a CLI, not a typed tool schema, so the SKILL.md must document arguments; the store can generate that text from the schema.
- The schema snapshot can drift from the live tool. The proxy can compare a schema hash at `tools/list`, or the importer can re-sync, as autosync does for skills.
- An agent that also has the tool as a native MCP server sees it twice. The skill should say which path to prefer.

### Stage 2: skills and prompts as first-class rossoctl resources

**What exists.** Nothing in either rossoctl repo defines a Skill or Prompt CRD. The precedents:

- `AgentRuntime.status.linkedSkills` is a list of skill *names* copied from a JSON annotation. Parse errors surface only as events.
- A since-removed `AgentRuntime.spec.skills []SkillImageRef{name, image, mountPath}` once mounted skills as OCI ImageVolumes. This is the only time a skill appeared in a CRD spec.
- `AgentCard` A2A `skills[]` are capability metadata, unrelated to SKILL.md skills. A new kind must be named to avoid that clash.
- Draft research docs (`composable-agents-design.md`, `dynamic-agent-composition.md`) treat tools, skills, prompts and policies as signed components in a "Component Registry", with a proposed `AgentCompositionRequest` CR. They define no per-component CRD.
- The operator's direction is a smaller CRD surface: `AgentCard` was folded into `AgentRuntime.status`. A new kind therefore needs a clear case.

**High-value points of stage 2**

1. **Pinned, reproducible skill versions.**
   - The store has immutable versions (uuid), and dreaming produces new ones continuously.
   - rossoctl's fetcher, however, ignores `SKILL_VERSION`, so agents get whatever version the name resolves to at pod start.
   - A `Skill` resource with `spec.source: {registry, name, version | uuid, digest}` makes agent deployments reproducible.
   - The store's export is already a deterministic zip (`build_deterministic_zip`), so a content digest is stable and verifiable.
2. **Governed rollout of improved skills.**
   - This closes the dreaming loop with a control point. A new store version appears; a person or policy approves it by updating the resource.
   - A controller rolls it to the agents that reference it, possibly canary first.
   - `status` shows which version each agent runs.
   - Today, an improvement goes live at the next pod start, with no gate.
3. **Typed references and validation.**
   - An agent or `AgentRuntime` names skills through typed `skillRefs`, not a JSON annotation.
   - Admission can reject unknown skills.
   - Status conditions (`SkillResolved`, `SkillFetchFailed`, version in use) replace silent init-container failures.
4. **Kubernetes RBAC for skills.**
   - A dedicated resource type gives per-namespace create/update/delete permissions through ordinary Role/RoleBinding.
   - Today skills are ConfigMaps, and the backend's ClusterRole grants ConfigMap access across the board.
   - This is the namespace authorization tier rossoctl does not yet have, for free and Kubernetes-native.
5. **A skill→tool dependency the operator can enforce.**
   - `spec.requires.tools: [toolRef]` makes stage 1's declared dependency actionable.
   - The operator verifies the tools exist, injects `MCP_URLS`, and adds the tools to the agent's `spec.auth.outbound` so token exchange works.
   - Status reports missing tools.
   - This removes the single-`mcpToolName` limitation without changing the agent API.
6. **Discovery and observability.**
   - `kubectl get skills -A` with printer columns: version, source, required tools, consuming agents.
   - `status.usedBy` answers "which agents run this skill", which nothing answers today.
7. **Supply-chain verification.**
   - `AgentCard` already verifies JWS signatures and Sigstore bundles.
   - A `Skill` with a digest and optional signature extends the same treatment to skill content.
8. **Prompts as a resource.**
   - System prompts, personas and guardrail prompts are currently invisible: assembled inside agent code or hard-coded in the backend (the dreaming prompt).
   - A `Prompt` resource, referenced by agents, makes them versioned and reviewable, and policy can require them (e.g. a namespace mandates a guardrail prompt).
   - It also makes them optimizable by the same loop that improves skills.
   - Store snippets that only live inside a skill do not need a resource. Stand-alone prompts do.

**Design guidance**
- **Metadata and reference, not content.** Kubernetes objects are limited to roughly 1 MiB, and skills bundle code and files. The resource should carry the reference, digest, required tools and approvals. Content stays in the store, or in an OCI artifact if ImageVolume mounting returns.
- **Split ownership to avoid a dual master.**
  - The store is authoritative for *content and versions*.
  - The rossoctl resource is authoritative for *deployment intent*: which version a namespace uses, and whether it is approved.
  - A resource then reads as "namespace X uses store skill S at version V". That is a natural successor to today's reference ConfigMap and to the projection mentioned in the access-control section.
- **Access is still decided by the store.** The resource does not grant access to store content. The store authorizes the fetch with the delegated identity (previous section). Kubernetes RBAC on the resource governs who may *change deployment intent*.

**Implications for skillberry-store.** Stage 2 is mostly rossoctl work, but it relies on the store for:

1. **Stable addressing.**
   - Export by uuid already works (`/skills/{uuid_or_name}/export-anthropic`).
   - The store should also expose the **content digest** of the deterministic export, for example in the skill manifest and as an `ETag` on the export response. A resource can then pin it and the fetcher can verify it.
2. **Version lineage.**
   - "Newer version of the same logical skill" must be queryable, so a controller can offer upgrades and show what changed.
   - The store's `parent` field and name-plus-versions model cover most of this. An explicit "versions of S" listing, with the rationale dreaming records, would complete it.
3. **Change notification instead of polling.**
   - A controller wants events. A store-side change feed (the store has `/changes`) or a webhook would replace the 30 s full-list poll.
4. **Optional OCI export.**
   - Publishing a skill as an OCI artifact would let the operator mount it as an ImageVolume: no init container, no network fetch at pod start, kubelet caching, and registry-native signing.
   - That revives the removed `SkillImageRef` path with the store as the producer.
5. **Prompt export.**
   - Stand-alone snippets (by tag or type) exported as `Prompt` resources, or fetched by reference, with the same digest and versioning treatment as skills.
6. **Write-back from Kubernetes (later).**
   - If users may author skills as Kubernetes resources with inline content, a controller would push them into the store.
   - That needs the delegated identity and namespace scoping from the access-control section, so the push lands in the right namespace under the right principal.

## Key files referenced

rossoctl repo (`rossoctl/backend/app/` unless noted):

- `services/skill_autosync.py`
- `services/dreaming.py`, `services/dream_state.py`, `routers/dream.py`
- `services/agent_env_defaults.py`
- `routers/agents_skills.py` (fetcher scripts, skill mounts, init containers, lines ~263–499)
- `routers/agents_manifests.py` (`SKILL_FOLDERS`, `rossoctl.io/skills` annotation)
- `routers/agents_models.py` (`CreateAgentRequest`, line 123)
- `routers/skills.py` (`SkillAutoSyncRequest`, ConfigMap CRUD, SSRF guard)
- `routers/tools.py` (tool workloads, `AgentRuntime`, MCP connect/invoke)
- `routers/acp.py` (namespace audience check)
- `routers/contexts.py`
- `core/auth.py`, `core/constants.py`, `core/config.py`
- `services/shipwright.py`, `services/shipwright_builds.py`
- `rossoctl/ui-v2/src/pages/ImportSkillPage.tsx`, `SkillCatalogPage.tsx`, `SkillDetailPage.tsx`, `AgentDetailPage.tsx`
- `rossoctl/ui-v2/src/utils/validation.ts`
- `charts/rossoctl/templates/skillberry-autosync-configmap.yaml`
- `charts/rossoctl/templates/skillberry-store.yaml`
- `docs/_internal/access-control/zero-trust.md`, `docs/_internal/research/composable-agents-design.md`

rossoctl operator repo (`operator/`):

- `api/v1alpha1/agentruntime_types.go`, `agentcard_types.go`, `authorizationpolicy_types.go`
- `internal/controller/agentruntime_controller.go` (`AnnotationSkills`, `readLinkedSkills`)
- `cmd/token-broker/`, `cmd/bundle-service/`

skillberry-store (this repo):

- `src/skillberry_store/services/skills_service.py:732` (`gather_export_inputs`) and `:781` (`export_anthropic`). Together they bundle `tool_uuids` and `snippet_uuids` into the zip returned by `/skills/{name}/export-anthropic`.
- `src/skillberry_store/tools/anthropic/exporter.py` (zip layout, deterministic zip)
- `src/skillberry_store/access_control/` (`config.py`, `deps.py`, `pdp.py`), `docs/design/access-control.md`, `docs/design/plugin-identity.md`
- `src/skillberry_store/fast_api/server.py:400-450` (control MCP mounts)
- `src/skillberry_store/fast_api/server_utils.py` (`mcp_content`), `src/skillberry_store/modules/file_executor.py` (MCP execution)
- `plugins/skillberry-plugin-mcp-importer/`, `plugins/skillberry-plugin-ask-runspace/`

## Update - 20261007

What changed since this document was first written, found by re-inspecting rossoctl at `44ec9139`, the operator at `10dd076` and this repo at `70137bb`:

- **New write path.** Skill dreaming (rossoctl PR #2198, feature-flagged) POSTs to `/plugins/ask-runspace/run`, polls `/plugins/ask-runspace/status/{id}`, and hands the store-side agent the store's `/control_sse` MCP, through which it creates new skill versions and snippets. The earlier statements "rossoctl never writes" and "only two GET endpoints" no longer hold.
- **`agents.py` was split** into `agents_skills.py`, `agents_manifests.py`, `agents_models.py`, `agents_create.py`, `agents_finalize.py` and others (#2388). The init-container script, env list, skill mounts, `SKILL_FOLDERS` and `CreateAgentRequest` moved there, so all earlier `agents.py:~NNNN` references are replaced.
- **Init-container fetcher**: the script content is unchanged. It now has a retry loop, lives in the `rossoctl-skill-fetcher-scripts` ConfigMap, and runs on `alpine:3.21.3`. It still ignores `SKILL_VERSION`.
- **Autosync**:
  - Reference ConfigMaps are created with `data={}`. The earlier description of rossoctl seeing tools "as files inside the ConfigMap it materializes" is corrected: content is unpacked into the pod at start.
  - Change detection uses a content hash annotation, not just the version (#2212).
  - Errors are classified as transient or permanent.
  - Helm adds `store-ui-url`.
  - The API default `allowedTags` is `rossoctl-approved`.
- **UI**: the browse `fetch` is unchanged. Deep links into the store UI were added. The count of UI write calls is 39, not "60+". `PromptInspector.tsx` was removed (commit e6ec0e25), so it is no longer cited.
- **Backend routers** now number 22. New ones include `contexts.py`, `dream.py` and `simulation.py`.
- **Persistence**: added the Context Service, the `rossoctl-dream-state` and fetcher-scripts ConfigMaps, and the autosync config ConfigMap to the inventory.
- **Operator**: documented the full CRD set (`AgentRuntime`, deprecated `AgentCard`, `AuthorizationPolicy`) and the `SkillDiscovery` gate on `linkedSkills`. `AgentRuntime` gained `auth.outbound` token-exchange routes and plugin presets. Bundle service and token broker are folded into the operator image (#540).
- **skillberry-store**: `export_anthropic` is at `skills_service.py:781`; the bundling it relies on is `gather_export_inputs` at `:732`. The store has an access-control subsystem (`disabled` / `standalone`), and the new section *Identity on the integration path* records how the rossoctl integration relates to it: it works only in `disabled` mode, and the UI route exposes the API.
- **Tool wiring**: the `get_mcp_tool_url` / `MCP_URL` code is unchanged. Added the `MCP_URLS` convention, the MCP Gateway option, and AuthBridge outbound token exchange.
- **Skill versions**: documented that `GET /skills/` returns all versions, that rossoctl's name-keyed autosync keeps the oldest version's metadata while the fetcher gets the head, and that content can change in place without rossoctl noticing.
- **Value Proposition**: added a pitch for a staged integration (versions, identity, namespaces, tools), with dreaming treated separately.
- **New sections**: *Identity on the integration path*, *Future integration based on extended access control* (delegated mode, namespace isolation and sharing, dynamic ACL API), and *Better skill and prompt integration* (tool proxies in store skills; Skill and Prompt resources in rossoctl).
