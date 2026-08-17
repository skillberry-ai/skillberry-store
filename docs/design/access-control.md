# Access Control — Design

Status: **Proposal (revision 13)**
Owner: skillberry-store
Scope: `skillberry-store` FastAPI service (per-endpoint access control for tenants), extensible to per-object / per-namespace in later work.

Revision notes:
* r13 — **Fail-safe defaults via `@requires`**. Removed the method/path→verb rule table and the tag→resource fallback in the mapper. Every REST endpoint now declares its ``(resource, verb)`` explicitly with the ``@requires(resource, verb)`` decorator (`access_control/decorator.py`). ``SBS.__init__`` runs two startup helpers after every route (including plugin sub-routers) is registered: ``stamp_rbac_markers`` copies each handler's marker to its ``APIRoute.openapi_extra`` (so the OpenAPI schema publishes ``x-rbac-*`` for tooling), and ``audit_rbac_coverage`` refuses to boot when any non-allow-listed route lacks a marker — a missing decorator is now a *loud* deploy-time failure rather than a silent fall-through to some default. All 51 non-allowlisted endpoints across `skills_api`, `tools_api`, `snippets_api`, `vmcp_api`, `vnfs_api`, `admin_api`, and `plugins_api` were stamped in the same commit (`/auth/*`, `/health*`, `/admin/metrics` remain unauth-allowlisted and skip the audit). `mcp_plan.py` simplified: verb is method-independent now (a single marker per route), so `verb_for_method_path` was replaced by `verb_for_route`. §6 and §8 rewritten; §13 file inventory updated.
* r12 — Refactored the PEP from a Starlette `BaseHTTPMiddleware` to a **single FastAPI dependency** installed on `router.dependencies` before any route is registered. Bearer extraction moved to FastAPI's `HTTPBearer` security scheme — the OpenAPI schema now advertises `securitySchemes.HTTPBearer` and per-route `security: [{HTTPBearer: []}]` (Swagger UI "Authorize" button and per-route lock icons). Removed the ad-hoc `Authorization` parser and hand-rolled 401 `JSONResponse` in favor of `HTTPBearer(auto_error=False)` + `HTTPException`. Kept the mapper's manual route-walk (it still runs on synthetic requests for the MCP-planning path and unit tests, but production calls now benefit from `request.scope["route"]` being populated because the dep fires after routing). Modules removed: `access_control/middleware.py`, `access_control/idp.py`. Module added: `access_control/deps.py`. §8 and §13 rewritten. Behavior unchanged — same allow/deny surface, same 401 with `WWW-Authenticate: Bearer`, same per-tenant MCP mounts.
* r11 — Implementation-nit sweep before hand-off: (a) documented that `bcrypt.checkpw` and `bcrypt.hashpw` must run via `asyncio.to_thread` to avoid blocking the event loop, (b) called out that `sessions.py` needs an injectable time source for fast unit tests, (c) fixed the CLI-E2E test-isolation env var (`SBS_CONFIG_HOME` → `XDG_CONFIG_HOME`, which is what `restish` actually reads), (d) corrected the "invalid token" error-message example to `invalid_credentials`, (e) reworded §10.4's endpoint table to reflect that all three `/auth/*` endpoints (login/logout/whoami) exist, not just whoami, (f) renumbered §16 to eliminate the "7b." Markdown quirk, (g) moved the resolved MCP question out of §17.
* r10 — Kept 12h `session_ttl_seconds` default. Documented the MCP token-refresh workflow explicitly in §10.2 (login → paste token in `claude_desktop_config.json` → restart MCP client when it expires); noted that raising the TTL is a one-value config change and added long-lived API tokens as §16 item 7b for the graduation path.
* r9 — Final-pass gap fixes: made the middleware route-matching mechanism explicit (§6/§8), documented that the Control MCP works in **all** modes via the middleware transparently (FastApiMCP re-dispatches through `httpx.ASGITransport(app)` and forwards `Authorization` by default), clarified `Subject` vs `whoami`, fixed stale references (`standalone.tokens` → `standalone.users`, `signIn(token)` → `signIn(username, password)`, `/changes` moved out of the unauth allow-list), added operator-quickstart `hash_password.py` example, and pinned env-var precedence rules.
* r8 — Corrected CLI story: the `sbs` CLI is a **`restish`** shim ([sdk_cli.py](../../client/python/skillberry_store_sdk/skillberry_store_sdk/sdk_cli.py)), not an SDK-based client. `sbs login` writes the session token into restish's per-API auth header entry (`~/.config/restish/apis.json`) — restish then auto-injects it on every command. Followed the industry-standard "plaintext file at `chmod 0600` + env-var override" pattern used by `gh` / `aws` / `kubectl` / `gcloud` / `az`. Documented that the OpenAPI-generated Python SDK will pick up the new `/auth/*` endpoints automatically on next regen — no design decision, just a release step.
* r7 — Added a dedicated **§14 Test plan** covering all in-scope modes (`disabled`, `standalone`) with unit, integration, and E2E layers. Deferred features (`delegated` mode, `scope:` enforcement, session persistence, UI cookie hardening) have their tests deferred to the same iteration that lands the code. E2E cases explicitly start from `POST /auth/login` and drive both success and failure paths.
* r6 — Replaced pre-provisioned tokens with **username/password login** (for demo UX). `POST /auth/login` validates credentials against `bcrypt` password hashes in the YAML and returns an **opaque in-memory session token** with a TTL. Kept as simple as possible: no JWT, no refresh tokens, no persistent session store — session tokens are lost on server restart (acceptable for demo).
* r5 — Mode discovery for the UI switched from a runtime API call to **build-/start-time injection via `vite.config.ts`**. The UI runs as its own Vite process ([ui_manager.py](../../src/skillberry_store/modules/ui_manager.py), [vite.config.ts](../../src/skillberry_store/ui/vite.config.ts)) that has filesystem access to `access_control_config.yaml`; it reads `mode` there and inlines it as `import.meta.env.VITE_ACL_MODE`. `GET /auth/config` is removed. `GET /auth/whoami` stays.
* r4 — Added UI login flow (§10.4) and two supporting endpoints (`GET /auth/config`, `GET /auth/whoami`). In `standalone` mode the UI starts on a login screen. Change-size estimate updated (§13) to include UI work.
* r3 — Roles are now pure `(resources, verbs)` bundles; **all target-object scoping** (namespaces, resourceNames, and future filters) is unified under a single `scope:` block on the binding. `scope` is designed but **deferred** — step 1 ships roles + subject-to-role bindings only.
* r2 — Deferred `delegated` mode to a future iteration; step 1 ships `disabled` and `standalone` only. Refined verb taxonomy to cover import / export / execute. Clarified CLI, MCP, and dev-mode behavior around namespace-based access.

---

## 1. Goals & Non-Goals

### Goals
1. Control **which REST endpoints** a tenant may call.
2. Provide a foundation that can later be **refined** to per-resource, per-namespace, or per-operation policy — without redesign.
3. Support **two deployment modes in step 1** (a third mode is designed but not implemented):
   * `disabled` — no access control; all endpoints reachable (backward compatible).
   * `standalone` — skillberry-store authenticates the caller and enforces access.
   * *(future)* `delegated` — an upstream trusted system supplies the `tenant_id`; skillberry-store enforces access.
4. Adopt **Kubernetes-style RBAC** (Role + RoleBinding) for scalable, familiar management.
5. Configuration lives in a **single YAML file** initially; the same in-memory data model must be reachable later via a REST config API.
6. **Minimal code change** in this iteration.
7. Follow **industry best practice** (NIST RBAC / K8s RBAC, PEP–PDP separation) and leave room for TLS / mTLS / OIDC / OPA later.

### Non-Goals (this iteration)
* `delegated` mode implementation (design contract preserved; code deferred).
* Encryption of transport (add later behind reverse proxy / TLS in the gateway).
* **All target-object scoping** on bindings — `scope:` (namespaces, resourceNames, future filters) is designed but not implemented. Step 1 enforces role membership only, and every binding is effectively `scope: *`. See §11.
* Auditing pipeline beyond structured log lines.
* Persisting RBAC config in a database.

---

## 2. Terminology (aligned with K8s and NIST)

| Term | Meaning |
|---|---|
| **Subject** | The entity making the request. In this design a subject is a `tenant_id` (and optionally a set of `groups`). |
| **Resource** | The kind of REST object controlled by a rule: `skills`, `tools`, `snippets`, `vmcp_servers`, `vnfs_servers`, `admin`, `plugins`, plus meta-resources `facets`, `system` (`/health`, `/changes`). Extensible later to namespace-scoped resources. |
| **Verb** | The action being performed. Base set: `list`, `get`, `create`, `update`, `delete`, `search`. Additional verbs for higher-risk operations: `execute`, `admin`. See §6. |
| **Rule** | `(resources[], verbs[])` — a pure permission tuple. **Divergence from K8s**: object-selection filters (`resourceNames`, `namespaces`, and any future ones) do NOT live on the rule; they live on the binding's `scope` block (see §5.1). This keeps roles reusable across scopes. |
| **Role** | Named set of rules — a pure `(resources, verbs)` permission bundle, reusable across bindings. |
| **RoleBinding** | Binds a set of subjects (tenants and/or groups) to one or more roles, optionally with a `scope` narrowing which target objects the grant applies to. In step 1, `scope` is not implemented; every binding is effectively `scope: *`. |
| **Scope** | *(future, deferred)* A block on the binding that filters target objects: `{ namespaces: [...], resourceNames: [...], ... }`. All object-selection filters live here so roles stay generic. |
| **Mode** | One of `disabled`, `standalone` (in step 1). `delegated` is reserved for a later iteration. |
| **Identity Provider (IdP)** | Component that turns an inbound request into a `(tenant_id, groups)` tuple — swappable per mode. |
| **PEP** (Policy Enforcement Point) | A single FastAPI dependency installed on `router.dependencies`; runs on every route. Detail in §8. |
| **PDP** (Policy Decision Point) | Pure function `authorize(subject, resource, verb) → Decision`. Stateless, cachable, unit-testable. |
| **Namespace** | A logical grouping applied to store objects via a `namespace:<name>` tag on the object. Namespaces belong to objects, not tenants. Tenants gain access to a namespace via a role binding (future refinement). |

---

## 3. Modes

The user's original names were `off / authentication / access-control-only`. Two nouns for the same underlying difference ("who authenticated?") make the design fuzzy. This design uses:

| Name | Availability | Meaning |
|---|---|---|
| **`disabled`** | step 1 | No PEP mounted. Every route reachable. No tenant identity is attached. |
| **`standalone`** | step 1 | skillberry-store's bundled IdP authenticates the request (bearer token) and RBAC is then applied. |
| **`delegated`** | *deferred* | Upstream trusted component authenticates; store would read `X-Tenant-Id` (and optionally `X-Tenant-Groups`) headers and apply RBAC. **Not implemented in step 1.** See §12. |

The mode name only changes the **IdP implementation**. The RBAC evaluator, config schema, and PEP are identical across `standalone` and (future) `delegated` — this preserves the user's observation that both funnel into the same core.

---

## 4. High-level architecture

```
                         ┌─────────────────────────────────────────────┐
                         │                 skillberry-store            │
                         │                                             │
Request ─► CORS ─► routing ─► │  enforce dep (global)                       │
                              │    │  (HTTPBearer scheme → OpenAPI security)  │
                              │    ▼                                        │
                              │  bearer token → SessionStore.resolve → ────┤
                              │    │   step 1: disabled | standalone       │
                              │    ▼   (delegated: future)                 │
                              │  Subject(tenant_id, groups)                │
                              │    │                                        │
                              │    ▼                                        │
                              │  RouteMapper: (method, path)                │
                              │    → (resource, verb)                       │
                              │    │                                        │
                              │    ▼                                        │
                              │  PDP.authorize(subject, resource, verb)     │
                              │    │                                        │
                              │    ├─ allow → request.state.subject = ...   │
                              │    │            forward to endpoint         │
                              │    └─ deny  → 401 (no identity)             │
                              │              or 403 (identity but no perm)  │
                              └─────────────────────────────────────────────┘
```

### Why a single global `Depends`, not a Starlette middleware, not per-route `Depends`?

* **Zero endpoint edits** — meets the "minimal change" requirement. All ~50 endpoints are enforced by one dep on `router.dependencies`; handlers stay ACL-free.
* Route → resource mapping is **derived from the OpenAPI tag** already declared on every endpoint (`skills`, `tools`, `snippets`, `vmcp_servers`, `vnfs_servers`, `admin`, `plugins`). No new registration boilerplate.
* Using FastAPI's own dependency machinery instead of `BaseHTTPMiddleware` lets us hand bearer-extraction to the `HTTPBearer` security scheme. FastAPI then auto-populates `components.securitySchemes` and per-route `security` in the generated OpenAPI (Swagger UI "Authorize" button, generated SDKs, lock icons) — none of which a middleware-based enforcement would give us for free.
* One dep, not fifty `Depends(require("skills", "create"))` calls. Per-route deps would require touching every endpoint definition and would drift as endpoints come and go — the "central mapper + one dep" shape scales without maintenance.
* Adding per-endpoint refinement later (e.g. `x-rbac-verb: execute` in `openapi_extra`, which every route already carries) requires no framework change.

---

## 5. Configuration

Single YAML file, mirroring K8s RBAC layout.

Location: `access_control_config.yaml`; overridable via `SBS_ACCESS_CONTROL_CONFIG`, following the precedent set by [import_auth_config.yaml](../../import_auth_config.yaml) and [endpoint_auth.py](../../src/skillberry_store/tools/endpoint_auth.py).

### 5.1 Schema

```yaml
# access_control_config.yaml
mode: standalone            # disabled | standalone   (delegated: reserved / future)

# Endpoints ALWAYS reachable regardless of mode/rbac.
# Kubernetes liveness/readiness probes and Prometheus scraping require this.
unauthenticated_paths:
  - GET  /health
  - GET  /health/ready
  - GET  /admin/metrics      # Prometheus scrape
  - POST /auth/login         # unauthenticated by definition — users log in here
  - GET  /docs
  - GET  /openapi.json
  - GET  /redoc
  - GET  /control_sse             # MCP SSE handshake — tool calls carry their own bearer (see §10.2)
  - POST /control_sse/messages    # MCP JSON-RPC transport — bearer on each message is forwarded to the underlying route

# --- Mode-specific: standalone only ---------------------------------
standalone:
  # Username/password credentials. Passwords are stored as bcrypt hashes.
  # An admin CLI (`skillberry hash-password`) mints the hash; the plaintext
  # is set once by the admin and never lives in the config file.
  session_ttl_seconds: 43200            # 12h default; env override: SBS_SESSION_TTL
                                         # Increase for MCP demos where re-login every 12h is friction.
                                         # See §10.2 for the token-refresh flow MCP clients need.
  users:
    - username: alice
      tenant_id: alice                  # tenant_id == username by default; can differ
      password_hash: "$2b$12$..."       # bcrypt
      groups: [team-blue]
    - username: bob
      tenant_id: bob
      password_hash: "$2b$12$..."
      groups: [team-red, admins]

# --- RBAC ------------------------------------------------------------
# Roles are pure (resources, verbs) permission bundles. No object-selection
# filters here — those belong to `scope:` on the binding (see §11, deferred).
roles:
  - name: reader
    rules:
      - resources: [skills, tools, snippets, vmcp_servers, vnfs_servers,
                    facets, plugins, system]
        verbs: [list, get, search]

  - name: content-author
    rules:
      - resources: [skills, tools, snippets]
        verbs: [list, get, search, create, update, delete]

  - name: tool-runner
    rules:
      - resources: [tools]
        verbs: [execute]
      - resources: [vmcp_servers, vnfs_servers]
        verbs: [execute]

  - name: server-operator
    rules:
      - resources: [vmcp_servers, vnfs_servers]
        verbs: [list, get, create, update, delete, execute]

  - name: admin
    rules:
      - resources: ["*"]
        verbs: ["*"]

# Bindings tie subjects to roles.
# `scope:` is designed but DEFERRED — step 1 accepts it in the schema but
# ignores it, treating every binding as scope-* (all target objects). See §11.
bindings:
  - name: alice-authoring
    subjects:
      - kind: tenant
        name: alice
    roles: [reader, content-author, tool-runner]
    # scope:                        # (future) all target-object filters
    #   namespaces:    [prod]       # matches on `namespace:prod` tag
    #   resourceNames: []           # omitted / empty = no restriction

  - name: red-team-admin
    subjects:
      - kind: group
        name: admins
    roles: [admin]
```

Notes:
* In `disabled` mode, `standalone.users`, `roles`, and `bindings` are all ignored — the PEP dependency is not installed at all, and the OpenAPI schema publishes no `securitySchemes`. Session tokens are not minted either (no `/auth/login` traffic is expected). There is no need to keep the standalone block consistent when mode is `disabled`.
* In step 1, the same role can be reused across many bindings without duplication (that is the point of the role/binding split); once `scope:` lands, the same role scales to per-namespace and per-object grants without any role-schema change.

### 5.2 Validation

* Config is loaded once at startup and cached (same pattern as `endpoint_auth.get_config`).
* Malformed / missing file with `mode: disabled` → warn + continue.
* Malformed / missing file with `mode: standalone` → **hard fail at startup** ("fail closed"). Rather than boot in an unsafe state, refuse to start.
* Unknown resource / verb names in rules → warning, rule dropped (fail-safe, does not brick startup for a typo).
* `"*"` is supported for both `resources` and `verbs`.

### 5.3 Environment variable precedence

Two env vars are read by the server; both override the YAML on conflict (env-first, following the FastAPI/Pydantic-settings convention already in use in [server.py `SBSettings`](../../src/skillberry_store/fast_api/server.py)):

| Variable | Effect | Precedence |
|---|---|---|
| `SBS_ACCESS_CONTROL_CONFIG` | Path to the config YAML. | Env > default (`./access_control_config.yaml`). |
| `SBS_SESSION_TTL` | Session TTL in seconds. | **Env > YAML `standalone.session_ttl_seconds` > built-in default (43200 / 12h).** |

### 5.4 Reload

* `SIGHUP` re-reads the file (nice-to-have; not required in step 1).
* `POST /admin/rbac/reload` is a natural fit for the future REST API iteration.

### 5.5 Operator quickstart (demo)

1. Generate a password hash:
   ```
   $ python scripts/hash_password.py alice
   Password: ****
   Confirm:  ****
   Copy this into access_control_config.yaml under standalone.users:
     $2b$12$8f7a...
   ```
   (The script uses `getpass` for no-echo entry, `bcrypt.hashpw(..., bcrypt.gensalt(rounds=12))` for hashing, and prints the hash to stdout. It never modifies the config file.)

2. Paste the hash into `access_control_config.yaml`:
   ```yaml
   mode: standalone
   standalone:
     users:
       - username: alice
         tenant_id: alice
         password_hash: "$2b$12$8f7a..."
         groups: [team-blue]
   roles: [...]
   bindings: [...]
   ```

3. Start the store — validation runs at startup; unresolved references (a binding pointing at a role that doesn't exist, a subject referring to an unknown group) surface as hard errors so you see them immediately.

4. Log in: `sbs login` (CLI) or the UI's `/login` page.

---

## 6. Route → (resource, verb) mapping

Every endpoint declares its ``(resource, verb)`` explicitly via ``@requires(resource, verb)`` above ``@app.<method>(...)`` (see `access_control/decorator.py`). ``SBS.__init__`` stamps the marker onto the matched ``APIRoute.openapi_extra`` at startup (``x-rbac-resource`` / ``x-rbac-verb``); the mapper reads it back at request time. There is **no** method/path→verb rule table and **no** tag→resource fallback — a route that arrives at the enforce dep without markers is a bug, and ``audit_rbac_coverage`` refuses to boot when it happens (§8).

At request time the mapper is trivial: given the matched `APIRoute`, read the two keys.

```python
def resource_for(route):
    extra = route.openapi_extra or {}
    r = extra.get("x-rbac-resource")
    if not r: raise UnmarkedRouteError(...)
    return r

def verb_for_route(route):
    extra = route.openapi_extra or {}
    v = extra.get("x-rbac-verb")
    if not v: raise UnmarkedRouteError(...)
    return v
```

Finding the matched route: on the production path the enforce dep runs *after* Starlette routing, so `request.scope["route"]` is already the matched `APIRoute` — no walk. `map_request` prefers that fast path and falls back to walking `request.app.routes` only when `scope["route"]` isn't populated (synthetic `Request` objects in `test_mapper.py`). Cost on the request path: O(1) attribute reads.

`access_control/mcp_plan.py` is a separate offline caller: it enumerates `app.routes` at startup to compute the per-tenant MCP surface and calls `resource_for(route)` / `verb_for_route(route)` directly — no `Request`, no `map_request`, no walk.

### 6.1 The @requires decorator

Placement is above ``@app.<method>``:

```python
@requires("skills", "create")
@app.post(
    "/skills/",
    tags=["skills"],
    openapi_extra={"x-cli-name": "add-skill", "x-mcp-tool": True},
)
async def create_skill(...): ...
```

Ordering matters — `@app.post` runs first (registers the route, returns the wrapped function), then `@requires` sets a marker attribute (`fn.__rbac_requires__`) on the returned function. At startup, ``stamp_rbac_markers(app)`` walks `app.routes` and copies each marker onto the route's `openapi_extra` so the mapper and the generated OpenAPI schema both see it. `x-rbac-*` remains a valid manual override too — a hand-written `openapi_extra` marker takes precedence over the decorator (useful for one-off cases where the decorator can't be applied cleanly).

### 6.2 Verb taxonomy (unchanged from r11)

The verb set stays the same: CRUD-plus-search (`list`, `get`, `create`, `update`, `delete`, `search`) plus two higher-risk verbs (`execute`, `admin`). Nothing about r13 changes what verbs exist — only *how* each endpoint's verb is decided (explicit declaration, not inference).

The per-endpoint marker inventory below is the source of truth. Import ≡ `create` and export ≡ `get` are conventions the author applies when writing `@requires`, not rules the mapper enforces.

| Endpoint | @requires |
|---|---|
| `POST /skills/` | `("skills", "create")` |
| `GET  /skills/` | `("skills", "list")` |
| `GET  /skills/{uuid_or_name}` | `("skills", "get")` |
| `DELETE /skills/{uuid_or_name}` | `("skills", "delete")` |
| `PUT  /skills/{uuid_or_name}` | `("skills", "update")` |
| `POST /skills/detect-anthropic-skills` | `("skills", "create")` *(precursor to import)* |
| `POST /skills/import-anthropic` | `("skills", "create")` |
| `GET  /skills/{uuid_or_name}/export-anthropic` | `("skills", "get")` |
| `GET  /facets/skills` | `("skills", "list")` |
| `GET  /search/skills` | `("skills", "search")` |
| `POST /tools/`, `POST /tools/add`, `POST /tools/add_code` | `("tools", "create")` |
| `POST /tools/{uuid_or_name}/execute` | `("tools", "execute")` |
| `GET  /tools/{uuid_or_name}/module` | `("tools", "get")` |
| `GET  /tools/`, `GET /facets/tools`, `GET /search/tools`, `GET /tools/{id}`, `DELETE /tools/{id}`, `PUT /tools/{id}` | list / list / search / get / delete / update |
| Snippets (7 endpoints) | mirror of skills (`create`, `list`, `get`, `delete`, `update`, `list` for facets, `search`) |
| `POST /vmcp_servers/{uuid_or_name}/start`, `POST /vnfs_servers/{uuid_or_name}/start` | `execute` |
| Other vmcp / vnfs (14 total) | CRUD + list/search as in the earlier inventory |
| `GET  /admin/metrics`, `/health`, `/health/ready` | *(unauthenticated allow-list — no `@requires`)* |
| `DELETE /admin/purge-all`, `GET /admin/backup`, `POST /admin/restore` | `("admin", "admin")` |
| `GET  /changes` | `("admin", "list")` |
| `GET  /plugins/`, `GET /plugins/{name}`, `PATCH /plugins/{name}` | `list` / `get` / `update` |
| `POST /auth/login`, `POST /auth/logout`, `GET /auth/whoami` | *(unauthenticated allow-list — no `@requires`)* |

---

## 7. Identity providers

Bearer resolution lives inside the `enforce` dependency (see §8). Rather than a separate `IdentityProvider` interface, the two supported modes are two branches in the wiring step:

* `disabled` — no dep installed; every request runs with no `Subject`.
* `standalone` — the `enforce` dep resolves an opaque bearer token against the in-memory `SessionStore` and constructs `Subject(tenant_id, groups)` from the resolved session. Any of missing/malformed/expired token → `HTTPException(401, ..., headers={"WWW-Authenticate": "Bearer"})`.

A future `delegated` mode reads `X-Tenant-Id` (and optionally `X-Tenant-Groups`) at the same seam; the PDP, RouteMapper, and RBAC config schema stay unchanged.

```python
# Subject = dataclass(tenant_id: str | None, groups: list[str])
```

**`Subject` vs `whoami`.** `Subject` is the internal, authoritative representation carried in `request.state.subject`. `GET /auth/whoami` returns an **enriched, serialized view** on top of it: `{tenant_id, groups, roles}`, where `roles` is computed from the loaded bindings (`cfg.roles_for(subject)`) rather than stored on `Subject`. Bindings can change (config reload) without invalidating minted sessions, which is why roles are derived at request time, not baked into `Subject` at login. This split is important to keep in mind when writing `auth_api.py` and the whoami tests in §14.

### 7.1 `disabled`
No `Subject` is constructed. In `disabled` mode the PEP dependency is not installed at all, so the PDP is never consulted. The tenant identity is simply absent for the request's lifetime.

### 7.2 `standalone`

Two steps. First, users authenticate; then requests carry an opaque session token.

**Login — `POST /auth/login`** (unauthenticated):

```
POST /auth/login
Content-Type: application/json
{ "username": "alice", "password": "..." }

200 OK
{ "token": "<opaque-32-byte-urlsafe>", "expires_at": "2026-07-28T09:00:00Z", "tenant_id": "alice" }

401 Unauthorized  (bad username OR bad password — same message, no user enumeration)
{ "detail": "invalid_credentials" }
```

Server side:
1. Look up `username` in `standalone.users`.
2. `bcrypt.checkpw(password, user.password_hash)` — constant-time. **Must run via `await asyncio.to_thread(bcrypt.checkpw, …)`**: bcrypt at cost=12 takes ~250–500 ms on modern hardware and would otherwise block the asyncio event loop for the full duration of every login attempt, serializing concurrent logins and making brute-force attempts a self-DoS. Same goes for `bcrypt.hashpw` in `scripts/hash_password.py` (there it's fine synchronously — it's a one-shot CLI).
3. Mint an opaque session token: `secrets.token_urlsafe(32)`.
4. Store in a **module-level `dict[str, Session]`** keyed by token: `Session(tenant_id, groups, expires_at)`. Purely in-memory — the store is a plain Python dict, and its content is lost on server restart. This is a conscious simplicity trade for step 1: demo users log in again after a restart; no session store, no persistence, no cross-process concerns.
5. Return the plaintext token to the client.

**Subsequent requests — identity extraction (in the enforce dependency):**

1. Read `Authorization: Bearer <token>`.
2. Look up the token in the session dict.
3. If found and not expired → `Subject(tenant_id, groups)`.
4. If missing or expired → 401 with `WWW-Authenticate: Bearer` (client re-logs in).

Expired sessions are lazily pruned on lookup. A tiny background task can also sweep periodically (~10 LOC, optional).

**Logout — `POST /auth/logout`** (auth-required): remove the presented token from the dict. Idempotent.

This is intentionally the smallest thing that works. No JWT, no refresh, no rotation, no persistent store. Trade-offs:
- **Restart loses sessions** — acceptable for demo; noted in §15 backward compatibility and §16 later phases.
- **Single-process only** — if the store later runs behind multiple gunicorn workers, sessions won't be shared. That's outside step 1's scope; today the store runs uvicorn single-process.
- **No revocation across all users** — for a demo, restarting the server IS the "revoke everything" button.

### 7.3 `delegated` *(deferred to a later iteration)*
Placeholder in the design so the config schema, IdP interface, and RBAC engine do not need to change when it lands. When implemented, it will read `X-Tenant-Id` (and optionally `X-Tenant-Groups`) headers, following the K8s API server `--requestheader-*` pattern with an added trust anchor (peer-cert CN or SPIFFE ID). Not shipped in step 1.

---

## 8. Enforcement (PEP)

A single FastAPI dependency, installed on `FastAPI(dependencies=[...])` **before any route is registered**, so every route on the app (and every plugin sub-router included via `app.include_router`) inherits it at `add_api_route` time. Bearer extraction is delegated to FastAPI's `HTTPBearer` security scheme — the OpenAPI schema then advertises `components.securitySchemes.HTTPBearer` and per-route `security: [{HTTPBearer: []}]` automatically, giving Swagger UI the "Authorize" button and per-route lock icons for free.

Pseudocode (see [access_control/deps.py](../../src/skillberry_store/access_control/deps.py) for the real thing):

```python
bearer_scheme = HTTPBearer(auto_error=False)  # let enforce shape the 401 body + WWW-Authenticate

def make_enforce_dependency(cfg, sessions):
    async def enforce(
        request: Request,
        creds: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    ) -> None:
        # 1. Allow-list bypass (health, metrics, docs, /auth/*).
        if cfg.is_unauthenticated(request.method, request.url.path):
            return

        # 2. Identity.
        if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
            raise HTTPException(401, "missing_authorization",
                                headers={"WWW-Authenticate": "Bearer"})
        session = sessions.resolve(creds.credentials)
        if session is None:
            raise HTTPException(401, "invalid_or_expired_token",
                                headers={"WWW-Authenticate": "Bearer"})
        subject = Subject(tenant_id=session.tenant_id, groups=list(session.groups))

        # 3. Route → (resource, verb). Unmapped routes (typos, mounts) pass
        # through — FastAPI produces the normal 404.
        mapped = try_map_request(request)
        if mapped is None:
            request.state.subject = subject
            return
        resource, verb, _ = mapped

        # 4. Decision.
        decision = authorize(subject, resource, verb, cfg)
        if not decision.allowed:
            raise HTTPException(403, decision.reason)

        request.state.subject = subject   # exposed to handlers
    return enforce
```

Wiring in `SBS.__init__` (see [server.py](../../src/skillberry_store/fast_api/server.py)):

```python
acl_cfg = get_acl_config()
sessions = SessionStore()
acl_deps = []
if acl_cfg.mode == "standalone":
    acl_deps = [Depends(make_enforce_dependency(acl_cfg, sessions))]

super().__init__(
    lifespan=_sbs_lifespan,
    generate_unique_id_function=custom_generate_unique_id,
    dependencies=acl_deps,               # global gate, propagates to every route
)
```

**Failure model:** 401 = no valid identity (retry with credentials, `WWW-Authenticate: Bearer` present); 403 = valid identity but no permission (do not retry).

In `disabled` mode no dependency is installed at all. The OpenAPI schema publishes no `securitySchemes` and no per-route `security`, matching the pre-ACL baseline exactly. Request-path overhead is zero: no extra call in the dep chain, no lookup, no branch.

**Fail-safe defaults via the startup audit (r13).** After every route (including plugin sub-routers) is registered, ``SBS.__init__`` runs two helpers from `access_control/audit.py`:

  1. ``stamp_rbac_markers(app)`` — walks `app.routes` and copies each handler's ``@requires`` marker onto its ``APIRoute.openapi_extra`` under ``x-rbac-resource`` / ``x-rbac-verb``. The mapper reads those keys at request time; the OpenAPI schema publishes them to downstream tooling.
  2. ``audit_rbac_coverage(app, cfg)`` — verifies every non-allowlisted `APIRoute` on the app carries the ``x-rbac-*`` markers. Any missing marker raises ``AccessControlConfigError`` and prevents startup, listing every offender in one message. The audit runs in **both** modes (`disabled` and `standalone`) so that missing markers are caught in tests and dev — not the day someone flips a production deployment to `standalone`.

This closes the fail-open failure mode the pre-r13 rule table had: a new endpoint whose method/path shape didn't quite fit the rules used to derive some default `(resource, verb)` and become authorizable under whatever role happened to grant that default. With `@requires` mandatory and the audit gating startup, forgetting to declare intent breaks the server loudly at deploy time, not silently at request time.

**Unauth allow-list and OpenAPI.** Because the enforce dep declares `HTTPBearer` as a security param, FastAPI decorates *every* route it covers with `security: [{HTTPBearer: []}]` — including the unauthenticated allow-list (`/auth/*`, `/health*`, `/admin/metrics`). This is misleading to schema consumers (Swagger UI, generated SDKs). The obvious workaround — `openapi_extra={"security": []}` per-route — does not work: FastAPI's `deep_dict_update` **concatenates** lists rather than replacing them, so an empty list is a no-op. Instead, `custom_openapi` in [server.py](../../src/skillberry_store/fast_api/server.py) post-processes the generated schema and strips `security` from any operation whose `(method, path)` matches `cfg.is_unauthenticated(...)`. The runtime allow-list is the single source of truth for both enforcement and the published schema.

**MCP re-dispatch (unchanged from r10).** `FastApiMCP` mounts SSE endpoints as Starlette `Mount` objects. Mounts do not receive FastAPI router-level dependencies, so the SSE handshake and JSON-RPC transport pass through without going near the enforce dep — matching the requirement to leave those paths open. When an MCP tool call is forwarded, `FastApiMCP` re-enters the app via `httpx.ASGITransport(app)` as a full ASGI request against the underlying REST route; that request hits the enforce dep on the target route and is authorized per call. The `Authorization` header is forwarded by default, so bearer-based auth Just Works over MCP.

---

## 9. Decision engine (PDP)

Pure function; no I/O:

```python
def authorize(subject: Subject, resource: str, verb: str, cfg: RBACConfig) -> Decision:
    for role_name in cfg.roles_for(subject):    # union across all bindings
        role = cfg.role(role_name)
        for rule in role.rules:
            if match(rule.resources, resource) and match(rule.verbs, verb):
                return Decision(allowed=True, reason=f"granted by {role_name}")
    return Decision(allowed=False,
                    reason=f"no role grants {verb} on {resource} to {subject.tenant_id}")

def match(patterns, value):   # "*" is wildcard
    return "*" in patterns or value in patterns
```

Complexity is O(#rules) per request; roles are small and the PDP result is cachable by `(tenant_id, resource, verb)`. Well within the noise on top of existing endpoint work.

### Future-proofing hooks (schema in, enforcement later)

Rules stay pure `(resources, verbs)`. **All object-selection filters live on the binding's `scope` block**, so roles remain reusable across scopes.

```yaml
bindings:
  - name: alice-in-prod
    subjects: [{kind: tenant, name: alice}]
    roles: [content-author]                # reusable role, no scope inside
    scope:                                 # (future) all target filters here
      namespaces:    ["prod"]              # per-namespace refinement
      resourceNames: ["skill-abc-uuid"]    # per-object refinement
      # future: tags, created_by, lifecycle_state, ...

  - name: alice-in-dev
    subjects: [{kind: tenant, name: alice}]
    roles: [content-author]                # SAME role, reused
    scope:
      namespaces: ["dev"]
```

Step 1 parses `scope:` if present (so configs written today are forward-compatible) but does not enforce it — every binding behaves as `scope: *`. When enforcement lands, the PDP signature does not change: the change is in the `Decision`, which will carry the effective scope (union of `scope` across matching bindings) alongside the allow/deny. §11 explains how that feeds into the service-layer filters.

---

## 10. Interaction with CLI, Control MCP, plugins

### 10.1 CLI

The `sbs` CLI ([sdk_cli.py](../../client/python/skillberry_store_sdk/skillberry_store_sdk/sdk_cli.py)) is a thin shim over **[restish](https://rest.sh/)** — a generic OpenAPI-driven REST CLI. It configures restish once against `<API_URL>/openapi.json` and delegates every user command via subprocess. It is *not* built on the Python SDK — the SDK lives in the same repo but the CLI does not import it.

**Access-control alignment:**

* **`disabled` mode:** every CLI command works, no credentials required (backward compatible).
* **`standalone` mode:** users run **`sbs login`** — the CLI prompts for username + password (via `getpass`, no echo), POSTs to `/auth/login`, and on success writes the returned session token into restish's own per-API config at `~/.config/restish/apis.json`:
  ```jsonc
  {
    "sbs": {
      "base": "http://0.0.0.0:8000",
      "spec_files": ["…/openapi.json"],
      "headers": { "Authorization": "Bearer <token>" }     // ← added by sbs login
    }
  }
  ```
  Restish auto-injects that header on every subsequent request, so no other CLI code changes. `sbs logout` removes the header entry and POSTs `/auth/logout`.

  **`$SBS_TOKEN` is a read-only override for CI / scripting**: when set, `sbs <command>` uses it as the Bearer token (injected into the invocation's environment for restish) and skips reading the stored token. It does **not** get written on `sbs login` and does **not** get cleared on `sbs logout` — those subcommands ignore the env var entirely and only affect the on-disk config. This mirrors how `GH_TOKEN` behaves in `gh`.
* **`delegated` mode (future):** the tenant id will be injected via the trusted-header pattern; the CLI never invents it.

**Token persistence — following industry norms.** Persisting the token after login is the CLI's responsibility, not the user's. The chosen approach — plaintext file with `chmod 0600` — matches what `gh`, `aws`, `kubectl`, `gcloud`, `az`, and `docker` do. `sbs login` explicitly chmods `~/.config/restish/apis.json` to `0600` after writing. OS-keyring integration and per-host credential helpers are deferred (see §16); env-var override (`SBS_TOKEN`) is included in step 1.

**No 401-driven interactive re-login in step 1.** Restish surfaces the server's 401 as a non-zero exit; `sbs` maps that to a printed "session expired or invalid — run `sbs login`" and exits non-zero. Automatic interactive prompt-on-401 is a nice-to-have; not required for the demo.

**SDK regeneration is a normal release step.** The Python SDK ([client/python/skillberry_store_sdk/](../../client/python/skillberry_store_sdk/)) is generated from the OpenAPI schema. Adding `/auth/login`, `/auth/logout`, and `/auth/whoami` will produce matching SDK methods on next regen — no manual SDK code to write. Not a design decision, just a release checklist item.

### 10.2 Control MCP

**MCP works in all access-control modes with zero MCP-specific code.**

This is not a design compromise — it falls out of how [FastApiMCP](https://github.com/tadata-org/fastapi_mcp) is implemented. Verified against the installed version:

1. `FastApiMCP` constructs an internal `httpx.AsyncClient(transport=httpx.ASGITransport(app=self.fastapi))` ([fastapi_mcp/server.py:115-116](.venv/lib/python3.11/site-packages/fastapi_mcp/server.py#L115-L116)). Every MCP tool invocation is re-issued as an HTTP call **through the app's own ASGI stack** — which means our `AccessControlMiddleware` fires on it.
2. `FastApiMCP`'s `headers` constructor parameter is a forward-allowlist for headers from the inbound MCP message; **it defaults to `['authorization']`** ([fastapi_mcp/server.py:82-83](.venv/lib/python3.11/site-packages/fastapi_mcp/server.py#L82-L83)). So a client that includes `Authorization: Bearer <token>` on its MCP JSON-RPC messages gets that header transparently forwarded to the underlying REST call.

**End-to-end flow in `standalone` mode:**

```
MCP client                          skillberry-store
    │                                     │
    ├─ SSE GET /control_sse ──────────────►   (session established)
    │                                     │
    ├─ POST /control_sse/messages         │
    │  { call_tool "list_skills" }        │
    │  Authorization: Bearer <token>      │
    │  ─────────────────────────────────► FastApiMCP.handle_call_tool
    │                                     │       │
    │                                     │       ▼ (forwards Authorization)
    │                                     │  httpx.ASGITransport → GET /skills/
    │                                     │       │
    │                                     │       ▼
    │                                     │  AccessControlMiddleware
    │                                     │       │  (bearer → subject → PDP)
    │                                     │       ▼
    │                                     │  route handler runs (or 401/403)
    │                                     │       │
    │  ◄──────────────────────────────── result of the REST call
```

**Behavior by mode (falls out for free):**

| Mode | MCP behavior |
|---|---|
| `disabled` | Middleware is not installed. Every MCP tool call goes straight to its route handler. All operations available. |
| `standalone` | Every MCP tool call is authorized by the same enforce dependency. Tools succeed if the tenant's role grants the corresponding `(resource, verb)`; otherwise 403. Client must include a session token on its MCP messages, obtained via `POST /auth/login` just like a REST client. |
| `delegated` *(future)* | Same as `standalone` but with the trusted-header pattern instead of a session token. |

**Configuration knobs:**

* `/control_sse` and `/control_sse/messages` are **added to `unauthenticated_paths`** (and are Starlette `Mount` objects, so router-level dependencies don't reach them anyway — the allow-list entry is defensive belt-and-braces). The SSE handshake and JSON-RPC transport itself is unauthenticated; authorization happens at the tool-call layer via the forwarded `Authorization` header. This matches how the enforce dep treats `POST /auth/login` — the outer surface is open, the operation is gated where it matters.
* No changes to `server.py`'s `FastApiMCP(self, include_operations=…)` invocation. The default `headers=['authorization']` allowlist is already what we need.
* Nothing needed inside `AccessControlMiddleware` — it does not have to know whether a request came from a REST client or from FastApiMCP's re-dispatch.

**Client experience:** an MCP client (e.g. Claude Desktop, an agent, a script) obtains a token via `POST /auth/login` and configures its MCP transport to send `Authorization: Bearer <token>` on every JSON-RPC message. The MCP tool surface then automatically reflects that tenant's permissions — a `reader` tenant sees `list-skills` succeed but `create-skill` return 403.

**Setup example** — Claude Desktop's `claude_desktop_config.json` after the user obtains a token via `sbs login` (or the UI's `/login` page):

```json
{
  "mcpServers": {
    "skillberry": {
      "url": "http://localhost:8000/control_sse",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

**Token lifecycle for MCP clients.** The token pasted into the MCP config is a regular session token with the same TTL as any other session (`standalone.session_ttl_seconds`, default 12h — §5.1). When it expires, the MCP client will start receiving 401s on tool calls. The user's workflow is:

1. `sbs login` (or re-login via the UI) → obtain a fresh token.
2. Update the token value in the MCP client's config file.
3. Restart the MCP client (Claude Desktop, agent process, …) so the new header takes effect.

This is friction on long-running MCP setups and matches the pattern used by pre-shared-token MCP servers today (GitHub, Linear, Notion — same "paste-a-token" model). If the friction becomes a demo blocker, raising `session_ttl_seconds` (or `SBS_SESSION_TTL`) is a one-value config change — no code change needed. A dedicated long-lived-token endpoint (`POST /auth/api-tokens`) is the natural graduation and lives in §16 later phases if we need it.

**Deferred (not needed for step 1):** authenticating the SSE handshake itself (currently permitted unauthenticated on the theory that establishing an empty session is harmless); per-session tenant caching to avoid re-resolving the token on every tool call.

### 10.3 Plugin routers

`plugin_loader.mount_routers(self)` adds routes via `app.include_router(...)`. FastAPI propagates `app.router.dependencies` to routes included this way, so the enforce dep gates plugin routes automatically without any per-plugin wiring. Plugin authors should either declare a `plugins/<slug>` tag or set `x-rbac-resource` on their routes to opt into a specific resource; unmapped routes default to `resource=plugins`.

### 10.4 UI (React SPA)

The store ships a React single-page app under [ui/](../../src/skillberry_store/ui/) that talks to the same REST surface via `services/api.ts`. The UI is a REST client just like the CLI, so it too must be aligned with the access rules.

**Behavior per mode:**

* **`disabled` mode:** UI loads directly, no login screen — identical to today's behavior.
* **`standalone` mode:** UI **starts on a login screen** (`/login`) with **username + password fields**. On submit, it POSTs to `/auth/login`, receives the session token, stores it in `sessionStorage`, and redirects to `/`. All subsequent API calls include `Authorization: Bearer <token>`. A 401 response at any point clears the stored token and redirects back to `/login`.
* **`delegated` mode (future):** UI is expected to run behind the same trusted gateway that authenticates other traffic; the gateway injects `X-Tenant-Id` on the way in. No login screen in-store.

**Mode discovery — build-/start-time, not runtime.** The UI is not a static site served by FastAPI. It runs as its own Vite process ([modules/ui_manager.py](../../src/skillberry_store/modules/ui_manager.py) spawns `npx vite --host 0.0.0.0 --port <ui_port>`) that proxies `/api/*` to the FastAPI backend ([vite.config.ts](../../src/skillberry_store/ui/vite.config.ts)). That Vite process is Node.js code with direct filesystem access to `access_control_config.yaml`. Rather than pay a runtime HTTP round-trip on every page load, `vite.config.ts` reads the config at start-up and inlines the mode into the bundle:

```ts
// vite.config.ts additions
import { readFileSync, existsSync } from 'fs';
import yaml from 'js-yaml';

function readAclMode(): 'disabled' | 'standalone' {
  const path = process.env.SBS_ACCESS_CONTROL_CONFIG || 'access_control_config.yaml';
  if (!existsSync(path)) return 'disabled';                       // same default as backend
  const cfg = yaml.load(readFileSync(path, 'utf-8')) as any;
  return cfg?.mode === 'standalone' ? 'standalone' : 'disabled';
}

export default defineConfig({
  // ...
  define: {
    'import.meta.env.VITE_ACL_MODE': JSON.stringify(readAclMode()),
  },
});
```

The SPA reads `import.meta.env.VITE_ACL_MODE` as a compile-time constant. No HTTP call on load; no `/auth/config` endpoint on the server.

**Colocation requirement.** This design assumes the Vite process and the FastAPI process share access to the same `access_control_config.yaml`. Today's deployment does this by construction — [main.py](../../src/skillberry_store/main.py) starts both processes together, and both honor `SBS_ACCESS_CONTROL_CONFIG` (or its default). If a future deployment separates them (static UI hosted elsewhere), the operator must ship the same file — or its `mode` — to both. Documenting this is enough for step 1.

**Mode changes require a Vite restart** (or a rebuild for a static-hosted UI). This is acceptable because mode is a deploy-time decision, not a runtime toggle; switching modes already requires a FastAPI restart to pick up the new config, and both are typically restarted together via `main.py`.

**Server endpoints backing the UI flow.** Three endpoints live in `fast_api/auth_api.py` (~90 LOC total, per §13.1). `POST /auth/login` and `POST /auth/logout` are the primary flow (specified in §7.2); the UI additionally uses `GET /auth/whoami` as a post-login diagnostic:

| Endpoint | Auth | Role in the UI flow |
|---|---|---|
| `POST /auth/login` | none (allow-listed) | Called by `AuthContext.signIn(username, password)`. See §7.2 for the contract. |
| `POST /auth/logout` | required | Called by `AuthContext.signOut()`. See §7.2. |
| `GET /auth/whoami` | required | Called by the UI after login to validate the token, populate the "Signed in as ..." indicator, and drive future RBAC-aware UI hiding. Also useful as a CLI diagnostic. Returns `{"tenant_id": "...", "groups": [...], "roles": [...]}`. |

**Client-side pieces (in `src/skillberry_store/ui/src/`):**

* `contexts/AuthContext.tsx` — token state; exposes `signIn(username, password)` (POSTs `/auth/login`), `signOut()` (POSTs `/auth/logout`, then clears local state — client-side clearing runs even when the server call fails, so a network-down `signOut()` still logs the user out locally), and `whoami()`. Reads `mode` once from `import.meta.env.VITE_ACL_MODE` (compile-time). Persists the token in `sessionStorage` (per-tab, cleared on tab close; safer default than `localStorage` for step 1 — see security note below).
* `pages/LoginPage.tsx` — form with `username` + `password` fields. On submit: `POST /auth/login`, store the returned token in `AuthContext`, redirect to `/`. Shows the server's `invalid_credentials` message inline on failure.
* `components/AuthGate.tsx` — route wrapper. If `mode === "standalone"` and no token, redirect to `/login` (except for `/login` itself). If the user visits `/login` **while already signed in**, redirect to `/` instead of showing an empty form. No HTTP call — mode is a compile-time constant.
* `components/UserBadge.tsx` — dropdown in the app header showing tenant id + a **Sign out** action. Rendered only when a `Subject` is present.
* `services/api.ts` (modified) — a `fetch` wrapper that (a) injects `Authorization: Bearer <token>` from `AuthContext` when set, (b) treats a 401 response by calling `signOut()` and navigating to `/login`.
* `App.tsx` (modified) — add the `/login` route, wrap the existing `<Routes>` in `<AuthGate>`.
* `vite.config.ts` (modified) — read `access_control_config.yaml` and inject `VITE_ACL_MODE` (see snippet above). Add `js-yaml` to `devDependencies`.

**UX details:**

* Failed login shows the server's 401 message inline (e.g. `invalid_credentials` per §7.2) — no `alert()` dialogs.
* Token is masked in the form (`type="password"`).
* Sign-out clears `sessionStorage` and returns to `/login`.
* The "Signed in as ..." badge is intentionally minimal for step 1; role/permission-driven UI hiding is a later phase.

**Security note (documented, deferred):** storing a bearer token in `sessionStorage` is vulnerable to XSS. The long-term hardening is to have the server issue an **HttpOnly, Secure, SameSite=Strict cookie** on `POST /auth/login` — JavaScript cannot read it, and the browser attaches it automatically. That change requires CSRF handling (double-submit cookie or `Origin`/`Referer` check on state-changing requests) and is out of scope for step 1. `sessionStorage` is chosen over `localStorage` because it clears on tab close, narrowing the exposure window.

**UX consequence of `sessionStorage`:** a user who opens the UI in a second browser tab has to log in again in that tab — sessionStorage is per-tab by design. This is expected and consistent with the security-first choice. When the HttpOnly-cookie hardening lands (§16 item 9), the cookie will be shared across tabs and this friction goes away.

---

## 11. Scoping — deferred; how the design accommodates it

**Step 1 does not enforce any target-object scoping.** Every binding behaves as `scope: *`, meaning "the granted role applies to all objects the store manages." The `scope:` block is a designed extension point on the binding, not a step-1 feature.

### Rationale for putting *all* filters on the binding, not the rule

`resourceNames` and `namespaces` are semantically the same kind of thing — both narrow which target objects a permission applies to. Splitting them across role rules and bindings (as K8s does) would force role duplication ("prod-content-author" vs "dev-content-author") and fragment enforcement across two code paths. By putting **every** object filter under the binding's `scope:` block, roles stay fully reusable and the PDP has a single place to compose the effective filter set.

### Namespaces in the codebase today

Namespaces are already representable as ordinary tags of the form `namespace:<name>` attached to store objects (`skills`, `tools`, `snippets`, `vmcp_servers`, `vnfs_servers`). Server-side filtering infrastructure is already present and will be reused when `scope:` enforcement lands:

* [services/list_query.py](../../src/skillberry_store/services/list_query.py) `apply_filters(..., tags=[...])` accepts `namespace:xxx` in the required-tags list (AND semantics).
* [services/facets.py](../../src/skillberry_store/services/facets.py) splits `namespace:` prefixes into a dedicated `namespaces` facet.
* [fast_api/search_filters.py](../../src/skillberry_store/fast_api/search_filters.py) `apply_search_filters(..., manifest_filter="tags:namespace:prod")` also honors namespace tags.

### Design invariants the step-1 implementation must preserve

1. **Data model consistency across modes.** Objects are never associated with a *tenant*; they are associated with a *namespace* (via `namespace:<name>` tags on the object). Therefore:
   * Objects created in `disabled` mode with `tags: [namespace:prod]` remain fully accessible to any authenticated tenant later granted a binding that scopes to `prod`.
   * Migrating `disabled` → `standalone` requires no data rewrite; it only requires the right bindings.
2. **PDP signature is stable.** When scoping lands, `authorize(subject, resource, verb)` still returns a `Decision`. The change is that `Decision` grows an `effective_scope` field carrying the union of `scope:` blocks across all bindings that granted the role. Enforcement is a service-layer change (feeding `effective_scope.namespaces` into `apply_filters`), not an endpoint-layer or enforce-dep-signature change.
3. **Config-file forward compatibility.** Step 1 parses `scope:` if present and ignores it. Configs written today with `scope:` therefore keep working unchanged when scoping enforcement lands.

### One gotcha to remember when scoping enforcement lands

`_matches_tags` in `list_query.py` is AND-semantics across all required tags. If a tenant is bound to *multiple* namespaces (`prod` OR `dev`), enforcing that as `namespace:prod` AND `namespace:dev` on every item is wrong — no single item carries both. The eventual fix is a small, contained change: treat `namespace:*` tags as a disjunction (OR-within-namespaces), while keeping AND semantics for non-namespace tags. Called out here so the current filter is not mistakenly cited later as "namespace enforcement is already done."

---

## 12. `delegated` mode — reserved (design contract)

The `delegated` mode is not implemented in step 1 but is treated as a first-class design goal so that step 1 does not paint itself into a corner. Contract:

* Config schema keeps `mode: delegated` as a **reserved value**. Loading a config with this value in step 1 fails with a clear "not yet supported" error at startup.
* The bearer-resolution step in `enforce` is the seam a future `delegated` mode plugs into: read `X-Tenant-Id` (and optionally `X-Tenant-Groups`) instead of resolving a session token, and the PDP, RouteMapper, and RBAC config schema stay unchanged.
* Everything documented as `standalone` in step 1 — token layout, unauthenticated allow-list, verb taxonomy, resource mapping — will apply identically to `delegated` when it ships. The only difference is where the `Subject` comes from.
* Header names, trust anchors (mTLS peer cert CN / SPIFFE ID), and header-stripping guidance for the fronting gateway are to be finalized when the mode is implemented.

---

## 13. Estimated code change (step 1)

### 13.1 Server (Python)

**New files:**

| File | Lines | Purpose |
|---|---|---|
| `src/skillberry_store/access_control/__init__.py` | ~5 | Package marker. |
| `src/skillberry_store/access_control/config.py` | ~120 | YAML load + validation (mirrors `endpoint_auth.py`). Rejects `mode: delegated` in step 1. Parses `binding.scope` if present but does not surface it to the PDP (forward-compat). Parses `standalone.users`. |
| `src/skillberry_store/access_control/sessions.py` | ~40 | In-memory `dict[token, Session]` with `mint(tenant_id, groups, ttl) -> token`, `resolve(token) -> Subject \| None`, `revoke(token)`. Lazy expiry pruning. **Time source must be injectable** — take `now: Callable[[], float] = time.time` on the store (or a module-level `_now` that tests can monkey-patch) so `test_sessions.py` and the `expired_token_rejected` integration test can advance the clock without real `sleep()`. |
| `src/skillberry_store/access_control/pdp.py` | ~40 | Pure decision engine + `Subject`, `Decision` dataclasses. |
| `src/skillberry_store/access_control/mapper.py` | ~50 | Route → (resource, verb) — reads `x-rbac-resource` / `x-rbac-verb` from `openapi_extra`. No rule table, no tag fallback; raises `UnmarkedRouteError` on missing markers. |
| `src/skillberry_store/access_control/decorator.py` | ~50 | The `@requires(resource, verb)` decorator: sets a marker attribute on the handler, copied to `openapi_extra` at startup. (r13) |
| `src/skillberry_store/access_control/audit.py` | ~90 | `stamp_rbac_markers(app)` and `audit_rbac_coverage(app, cfg)`. Called from `SBS.__init__` after all routes register; audit failure prevents startup. (r13) |
| `src/skillberry_store/access_control/deps.py` | ~90 | Policy Enforcement Point as a FastAPI dependency. Owns the `HTTPBearer` security scheme (so OpenAPI publishes `securitySchemes.HTTPBearer` and per-route `security`), the unauth allow-list short-circuit, bearer-token resolution to a `Subject`, the PDP call, and stashing the subject on `request.state`. Skipped entirely in `disabled` mode (no dep installed → no security scheme in the schema). Replaces the ex-`middleware.py` + `idp.py` pair (r12). |
| `src/skillberry_store/fast_api/auth_api.py` | ~90 | `POST /auth/login` (username/password → session token; bcrypt-verify), `POST /auth/logout`, `GET /auth/whoami`. |
| `scripts/hash_password.py` | ~20 | Admin utility: `bcrypt.hashpw(getpass())` → prints the hash to paste into `access_control_config.yaml`. |
| `access_control_config.yaml` | ~40 | Default config; ships with `mode: disabled`. |
| `docs/config-env-vars.md` | +8 | Document `SBS_ACCESS_CONTROL_CONFIG`, `SBS_SESSION_TTL`, and `SBS_TOKEN` (CLI-side). Precedence rules per §5.3. |
| `pyproject.toml` | +1 | Add `bcrypt` dependency. |

**Modified files:**

| File | Lines changed | Change |
|---|---|---|
| `src/skillberry_store/fast_api/server.py` | ~12 | Load config; if `mode != disabled`, install `AccessControlMiddleware` after CORS. Register `auth_api`. |

**Existing endpoint modules** (`skills_api.py`, `tools_api.py`, `snippets_api.py`, `vmcp_api.py`, `vnfs_api.py`, `admin_api.py`, `plugins_api.py`): **0 lines changed** for step 1.

**Server total: ~415 new LOC, ~12 modified LOC.** One new runtime dependency: `bcrypt`.

Test coverage detailed in §14; server-side test budget rolls up to ~280 LOC.

### 13.2 UI (React / TypeScript)

**New files** (all under `src/skillberry_store/ui/src/`):

| File | Lines | Purpose |
|---|---|---|
| `contexts/AuthContext.tsx` | ~70 | Token state; `signIn(username, password)` (POSTs `/auth/login`) / `signOut()` (POSTs `/auth/logout`) / `whoami()`; reads `mode` from `import.meta.env.VITE_ACL_MODE`; `sessionStorage` persistence. |
| `pages/LoginPage.tsx` | ~90 | Username + password form, error display, redirect on success. |
| `components/AuthGate.tsx` | ~30 | Route wrapper: if `VITE_ACL_MODE === 'standalone'` and no token, redirect to `/login`. No HTTP call. |
| `components/UserBadge.tsx` | ~30 | Header widget: "Signed in as `<tenant>`" + Sign out. |

**Modified files:**

| File | Lines changed | Change |
|---|---|---|
| `src/skillberry_store/ui/src/services/api.ts` | ~30 | Wrap all `fetch` calls to inject `Authorization: Bearer <token>` and handle 401 → signOut + redirect. |
| `src/skillberry_store/ui/src/App.tsx` | ~10 | Add `/login` route; wrap existing `<Routes>` in `<AuthGate>`. |
| `src/skillberry_store/ui/src/components/AppLayout.tsx` | ~5 | Render `<UserBadge>` in the header. |
| `src/skillberry_store/ui/vite.config.ts` | ~15 | Read `access_control_config.yaml` at start-up; inject `VITE_ACL_MODE` via `define`. |
| `src/skillberry_store/ui/package.json` | ~1 | Add `js-yaml` (and its types) to `devDependencies`. |

**UI total: ~220 new LOC, ~61 modified LOC.**

### 13.3 CLI (Python, `sbs`) + SDK

The `sbs` CLI is a restish shim ([sdk_cli.py](../../client/python/skillberry_store_sdk/skillberry_store_sdk/sdk_cli.py)); it is not built on the Python SDK. Auth work is confined to `sdk_cli.py` plus a tiny helper for editing restish's config atomically.

**Modified files:**

| File | Lines changed | Change |
|---|---|---|
| `client/python/skillberry_store_sdk/skillberry_store_sdk/sdk_cli.py` | ~100 | Three new subcommands: `sbs login` (prompts for username + password via `getpass`, POSTs `/auth/login` using `urllib` from stdlib — no new deps, writes `Authorization: Bearer <token>` into the `sbs` API entry in `~/.config/restish/apis.json`, chmods the file to `0600`), `sbs logout` (POSTs `/auth/logout`, removes the header entry), `sbs whoami` (calls `/auth/whoami` and prints the result). Reads `$SBS_TOKEN` as an override (skip file, inject header for this invocation only). Also: map restish's non-zero exit from a 401 to a friendly "run `sbs login`" message. |

**CLI total: ~100 modified LOC.**

**SDK (auto-regenerated, no manual work):**

The Python SDK at [client/python/skillberry_store_sdk/](../../client/python/skillberry_store_sdk/) is produced by the OpenAPI generator. Adding `/auth/login`, `/auth/logout`, and `/auth/whoami` to FastAPI produces matching SDK methods on next regen. The SDK's existing `Configuration` class already supports `access_token` / `api_key['Bearer']` — no additional edits needed. Regen runs as part of the release, not this PR.

**SDK LOC change: 0 hand-written (regenerator output not counted).**

### 13.4 Grand total

Test LOC is broken out in **§14 Test plan**.

| | New LOC | Modified LOC |
|---|---:|---:|
| Server (Python) | ~415 | ~12 |
| UI (TS/React) | ~220 | ~61 |
| CLI (Python) | 0 | ~100 |
| Tests (see §14) | ~1,155 | 0 |
| **Total** | **~1,790** | **~173** |

Ships in a single PR. Endpoint code is untouched. New runtime dep: `bcrypt`.

The test budget is roughly 1.9× the production code — appropriate for security-sensitive scaffolding that will be trusted by every downstream feature. Cutting the E2E CLI test and one or two UI Playwright cases can drop this to ~950 test LOC if PR-size becomes an issue; recommend keeping the full suite.

---

## 14. Test plan

Tests are structured in three layers matching the three enforcement layers of the design. Every in-scope mode (`disabled`, `standalone`) is covered at every layer. **Tests for deferred features are deferred alongside the code** — the design does not budget test LOC for `delegated` mode, `scope:` enforcement, session persistence, or UI cookie hardening.

### 14.1 Unit tests (fast, no HTTP)

Location: `src/skillberry_store/tests/access_control/` (new subdirectory).

| File | Coverage | Approx. LOC |
|---|---|---:|
| `test_pdp.py` | Truth table for `authorize(subject, resource, verb)`: allow via role, deny with no matching rule, `"*"` wildcard on resources and verbs, multi-role union, empty role list. Pure function — no fixtures. | ~50 |
| `test_mapper.py` | Every mapping rule from §6.2 gets a positive case: CRUD verbs; `import ≡ create` (`/skills/import-anthropic`, `/skills/detect-anthropic-skills`, `/tools/add`, `/tools/add_code`); `export ≡ get` (`/skills/{id}/export-anthropic`); `execute` (`/tools/{id}/execute`, `/vmcp/{id}/start`, `/vnfs/{id}/start`); `admin` super-verb (`/admin/backup`, `/admin/restore`, `/admin/purge-all`); `x-rbac-resource` and `x-rbac-verb` overrides. Also: unauth allow-list matches, and unmapped routes surface as `UnmappedRouteError`. | ~80 |
| `test_config.py` | Load a valid YAML; malformed YAML in `disabled` mode → warn + empty; malformed YAML in `standalone` mode → hard fail; `mode: delegated` → hard fail with a clear "not yet supported" message; unknown resource/verb in a rule → warning + rule dropped; `binding.scope` present → parsed but not surfaced (forward-compat). | ~50 |
| `test_sessions.py` | `mint` returns a URL-safe opaque token; `resolve` returns `Subject` for a live token and `None` for expired/unknown; `revoke` is idempotent; expiry pruning happens on lookup; multiple concurrent `mint` calls yield distinct tokens. | ~40 |

**Unit total: ~220 LOC.**

### 14.2 Integration tests (in-process ASGI, no external server)

Location: `src/skillberry_store/tests/fast_api/test_access_control.py` (new). Uses `httpx.AsyncClient(transport=ASGITransport(app))` — the pattern already used in `test_server.py` — so the whole enforce-dep + PDP + auth_api stack is exercised without spawning a server.

| Case | Coverage | Approx. LOC |
|---|---|---:|
| `disabled_mode_all_endpoints_open` | With `mode: disabled`, unauthenticated requests to `/skills/`, `/tools/`, `/admin/backup` all succeed (or hit their normal handler; not 401/403). No enforce dep is installed, so no request-path overhead. | ~30 |
| `standalone_mode_missing_auth_returns_401` | With `mode: standalone`, any non-allow-list request without `Authorization` header returns 401 and `WWW-Authenticate: Bearer`. | ~20 |
| `standalone_mode_unauth_allowlist_reachable` | `GET /health`, `GET /health/ready`, `GET /admin/metrics`, `POST /auth/login`, `GET /docs`, `GET /openapi.json` reachable without a token. | ~30 |
| `login_flow_good_and_bad_creds` | `POST /auth/login` with good creds → 200 + `{token, expires_at, tenant_id}`; bad password → 401 `invalid_credentials`; unknown username → 401 with **identical** body (no user enumeration). | ~40 |
| `logout_revokes_token` | Login → call an authorized endpoint successfully → `POST /auth/logout` → the same token now returns 401. | ~30 |
| `whoami_returns_subject` | Post-login `GET /auth/whoami` returns the correct `tenant_id`, `groups`, and `roles` (roles are computed from the bindings). | ~25 |
| `expired_token_rejected` | Configure `session_ttl_seconds: 1`, log in, sleep past expiry, next request returns 401. (Or, cleaner: monkey-patch time in `sessions.py`.) | ~30 |
| `rbac_grant_and_deny` | Two-tenant fixture (`alice` = reader, `bob` = content-author). `alice`'s login can `GET /skills/` (200), cannot `POST /skills/` (403). `bob`'s login can `POST /skills/` (200). | ~50 |
| `verb_execute_gated_separately` | Reader can `GET /tools/{id}` (200) but cannot `POST /tools/{id}/execute` (403); `tool-runner` can execute (200). Same shape for `POST /vmcp/{id}/start`. | ~40 |
| `admin_verb_gated` | Non-admin `DELETE /admin/purge-all` → 403; admin → 200 (mocked to return quickly). | ~25 |
| `mode_delegated_rejected_at_startup` | Instantiating `SBS` with `mode: delegated` raises with a clear message. | ~15 |

**Integration total: ~335 LOC.**

Uses a small pytest fixture (`fresh_sbs_with_acl`) that stamps a fresh test YAML on disk and passes its path via `SBS_ACCESS_CONTROL_CONFIG`, following the pattern in `conftest.py`.

### 14.3 E2E tests (live server, HTTP)

Location: `src/skillberry_store/tests/e2e/test_access_control_e2e.py` (new). Same shape as `test_skills_api.py` — starts `uvicorn` in a subprocess against a temp data dir, uses `httpx.AsyncClient`, and hits `http://localhost:8000` for real. **Each test drives the full API path from `POST /auth/login` through downstream API calls, exercising both success and failure**, per the user's requirement.

| Scenario | Steps | Approx. LOC |
|---|---|---:|
| `disabled_mode_lifecycle` | Server started with `mode: disabled`. Create a skill, create a tool, execute the tool, delete both. No `Authorization` header. All succeed. Baseline that ACL doesn't regress existing behavior. | ~60 |
| `standalone_reader_journey` | Server started with `mode: standalone` and a `reader`-bound user `viewer`. `POST /auth/login` as `viewer` → get token. `GET /skills/` → 200. `POST /skills/` with reader token → 403. `POST /tools/{id}/execute` → 403. `POST /auth/logout`. Same token now fails with 401. | ~80 |
| `standalone_author_journey` | Login as `author` (content-author + tool-runner). `POST /skills/` → 201. `POST /skills/import-anthropic` → 200. `POST /tools/add_code` → 201. `POST /tools/{id}/execute` → 200. `DELETE /admin/purge-all` → 403 (author is not admin). Logout. | ~90 |
| `standalone_admin_journey` | Login as `admin` (admin role). `GET /admin/backup` → 200 with a ZIP body. `DELETE /admin/purge-all` → 200. Followed by `GET /skills/` → returns an empty list — proves purge ran through the admin token. | ~50 |
| `login_failure_paths` | Wrong password → 401 `invalid_credentials`. Unknown username → 401 `invalid_credentials` with identical body. Empty JSON → 422. Missing `Authorization` on a protected endpoint → 401 with `WWW-Authenticate`. Malformed `Authorization` (`Bearer` with no token) → 401. | ~50 |
| `token_expiry_forces_relogin` | Config with `session_ttl_seconds: 2`. Login. First `GET /skills/` succeeds. Sleep 3s. Second `GET /skills/` returns 401 with a message identifying expiry. Re-login → 200. | ~40 |
| `unauth_allowlist_from_the_wire` | `GET /health`, `GET /health/ready`, `GET /admin/metrics` all reachable without a token when server is in `standalone` mode. | ~20 |
| `cli_login_end_to_end` | Invoke `sbs login` in a subprocess with piped user/pass, with `XDG_CONFIG_HOME=<tmpdir>` in the env for isolation (restish reads its config from `$XDG_CONFIG_HOME/restish/apis.json`, or `~/.config/restish/apis.json` when unset). Verify the token was written to `<tmpdir>/restish/apis.json` with `0600` perms. Invoke `sbs list-skills` — succeeds. Invoke `sbs logout` — header entry removed and next `sbs list-skills` prints the actionable "run `sbs login`" message and exits non-zero. | ~70 |

**E2E total: ~460 LOC.**

E2E cases run under an explicit pytest marker (`@pytest.mark.acl_e2e`) so they can be selected/deselected in CI where server-startup time matters. Reuses `wait_until_server_ready` from `src/skillberry_store/tests/utils.py`.

### 14.4 UI tests (Playwright, existing infra)

Location: `src/skillberry_store/ui/e2e/access-control.spec.ts` (new). Playwright is already configured (`ui/playwright.config.ts`, `ui/e2e/`).

| Scenario | Coverage | Approx. LOC |
|---|---|---:|
| `disabled_mode_no_login_screen` | Vite started with a `disabled` config → visiting `/` renders the Home page directly, no `/login` redirect. | ~15 |
| `standalone_mode_redirects_to_login` | Vite started with a `standalone` config → visiting `/` redirects to `/login`. | ~15 |
| `login_success_and_navigation` | Fill username/password, submit, land on `/`. Header shows "Signed in as `<tenant>`". Sign out returns to `/login`. | ~40 |
| `login_failure_shows_error` | Wrong password → inline error, still on `/login`, no navigation. | ~20 |
| `session_expiry_redirects` | Manually clear `sessionStorage` (simulates expired token), click any link that hits the API → redirected to `/login`. | ~25 |
| `token_reuse_across_reloads` | Log in, reload the tab → still logged in (sessionStorage persists within the tab). Close and re-open tab → logged out (sessionStorage cleared). | ~25 |

**UI total: ~140 LOC.**

### 14.5 Test coverage matrix

| Layer | disabled | standalone | delegated |
|---|:-:|:-:|:-:|
| Unit (PDP / mapper / config / sessions) | n/a | ✅ | *(deferred with feature)* |
| Integration (ASGI) | ✅ | ✅ | *(deferred)* |
| E2E (live HTTP) | ✅ | ✅ | *(deferred)* |
| UI (Playwright) | ✅ | ✅ | *(deferred)* |
| CLI E2E | ✅ (implicit — existing tests already run in `disabled`) | ✅ (new `cli_login_end_to_end`) | *(deferred)* |

### 14.6 Test totals

| Layer | LOC |
|---|---:|
| Unit | ~220 |
| Integration | ~335 |
| E2E (Python) | ~460 |
| UI (Playwright) | ~140 |
| **Grand total** | **~1,155** |

Update to the estimate table in §13.4: **Tests** row → **~1,155** (was ~350). Corresponding grand total row bumps to ~1,790 new LOC.

---

## 15. Backward compatibility

* `disabled` (the shipped default) leaves all endpoints wide open — identical to today. The enforce dependency is not installed and the OpenAPI schema publishes no `securitySchemes`, so there is no request-path overhead and no observable schema change either.
* Objects created under `disabled` inherit their namespace(s) from the `namespace:*` tags the caller supplies (unchanged behavior). Later switching to `standalone` does **not** require any data rewrite: tenants bound to a namespace will simply see the objects that already carry that namespace tag.
* CLI without a token continues to work against `disabled` deployments.
* UI in `disabled` mode: no login screen (`AuthGate` sees `VITE_ACL_MODE === 'disabled'` and passes through). Existing users see no visible change.
* `standalone` mode: sessions live in memory only, so restarting the store forces all users to log in again. Fine for a demo; addressed in §16 later phases if a longer-lived deployment needs sticky sessions.

---

## 16. Later phases (for context — NOT in this iteration)

1. **`delegated` mode** — reserved slot; see §12.
2. **REST config API** (`/admin/rbac/{roles,bindings,tokens}`), backed initially by the same YAML file (read-through cache + atomic write). Enables UI.
3. **Binding `scope:` enforcement** — unified refinement covering both per-namespace and per-object (`resourceNames`) scoping. Service-layer change in [list_query.py](../../src/skillberry_store/services/list_query.py) and [search_filters.py](../../src/skillberry_store/fast_api/search_filters.py) that reads `Decision.effective_scope` and injects the filters; also the AND→OR fix for `namespace:*` tags called out in §11.
4. **Additional scope filters** (tags, `created_by`, lifecycle_state) — slot into the same `scope:` block on the binding without any role-schema change.
5. **Providers**: OIDC / JWT-with-JWKS / mTLS-CN. Adds `providers:` block to config.
6. **MCP surface polish** — SSE-handshake authentication (currently unauth-listed since the tool call itself is gated), a "signed in as X" hint in MCP client-facing metadata, and per-session tenant caching to avoid re-resolving the bearer on every tool call. Not needed for correctness — step 1 already enforces per tool call via the enforce dependency (§10.2).
7. **Session persistence & scale-out** — replace the in-memory session dict with signed JWTs (survives restart, works across workers) or a Redis-backed session store (easy revocation). Also enables sticky sessions past a restart.
8. **Long-lived API tokens** — separate mint flow (`POST /auth/api-tokens`, UI page under the user dropdown, `sbs api-token create`) with 30- / 90-day TTLs, aimed at MCP clients and CI. Same server-side validation path as session tokens; different lifetime + minting UX. Ships when the 12h-relogin friction becomes a real demo blocker rather than a paper cut.
9. **UI token hardening** — replace `sessionStorage` bearer with `HttpOnly, Secure, SameSite=Strict` cookie set by `/auth/login`, plus CSRF handling (double-submit token or `Origin` check). Removes the XSS token-exfiltration risk called out in §10.4.
10. **Password lifecycle** — password rotation endpoint, lockout after N failed logins, optional MFA.
11. **CLI credential helpers** — OS-keyring integration for `sbs login` (macOS Keychain / Linux Secret Service / Windows Credential Manager, via Python's `keyring` package), and a Docker-style credential-helper plug-in so operators can point at Vault / 1Password / etc. Also: auto-refresh via interactive prompt on 401 instead of just printing "run `sbs login`".
12. **UI RBAC-aware hiding** — use `/auth/whoami` roles to hide UI elements a tenant cannot use (buttons, tabs, admin page). Server-side enforcement remains the source of truth; this is cosmetic.
13. **Audit log**: structured `access_denied` / `access_granted` events on a dedicated logger, feeding SIEM.

---

## 17. Open questions

1. In `standalone` mode, do we accept both `Authorization: Bearer` **and** an API-key header (`X-Api-Key`)? Recommend Bearer only for step 1; simpler.
2. Should `/admin/*` be gated separately from `admin`-tagged endpoints that are actually public (`/health`, `/changes`)? The proposal is to move `/health*` and `/changes` to a dedicated `system` tag *only if* we get pushback on the allow-list approach — otherwise the allow-list is simpler and matches how K8s handles `/livez` / `/readyz` / `/metrics`.

### Resolved during the design cycle
* **MCP tenant identity** *(r9)* — per-message bearer forwarded by FastApiMCP into the ASGI stack; no separate mount-tenant or reserved-tenant model needed. See §10.2.
