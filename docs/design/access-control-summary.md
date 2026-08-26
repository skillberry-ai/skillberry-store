# Access Control — Summary

skillberry-store ships with **Kubernetes-style RBAC** (roles + role bindings) applied by a single FastAPI dependency installed on the app's `router.dependencies`. Bearer extraction rides FastAPI's `HTTPBearer` security scheme, so the generated OpenAPI advertises the scheme and per-route `security` — Swagger UI shows an "Authorize" button and lock icons for free. See [access-control.md](access-control.md) for the full design.

## Modes

Set via `mode:` in [access_control_config.yaml](../../access_control_config.yaml) (overridable with `SBS_ACCESS_CONTROL_CONFIG`).

| Mode | Behavior |
|---|---|
| `disabled` *(default)* | No enforce dep installed. All endpoints reachable — backward compatible. OpenAPI publishes no `securitySchemes`. |
| `standalone` | Bundled username/password login mints opaque session tokens; every request is authenticated (`HTTPBearer`) and authorized (RBAC). |
| `delegated` *(reserved)* | Header-based trust from an upstream gateway. Rejected at startup in step 1. |

## Request flow (`standalone`)

```
Request → Allow-list check → Bearer → SessionStore → Subject
                                                       │
                                             Route → (resource, verb)
                                                       │
                             PDP: any role bound to Subject that grants it?
                              ├─ yes → handler runs (subject on request.state)
                              └─ no  → 403 (401 if identity missing)
```

- **Every endpoint declares `(resource, verb)` explicitly** with `@requires("resource", "verb")` above `@app.<method>`. There is no rule table, no tag fallback — a route without markers fails startup via the RBAC coverage audit (`audit_rbac_coverage`), so forgetting the decorator is a *loud* deploy-time error rather than a silent fall-through.
- **Resources in use**: `skills`, `tools`, `snippets`, `vmcp_servers`, `vnfs_servers`, `admin`, `plugins`.
- **Verbs in use**: `list`, `get`, `search`, `create`, `update`, `delete`, plus `execute` (running code) and `admin` (whole-store destructive ops).

## Config shape

```yaml
mode: standalone
standalone:
  session_ttl_seconds: 43200        # 12h; env override: SBS_SESSION_TTL
  users:
    - username: alice
      password_hash: "$2b$12$..."   # produced by scripts/setup_user.py
      groups: [team-blue]
roles:
  - name: reader
    rules: [{resources: [skills, tools, snippets, ...], verbs: [list, get, search]}]
bindings:
  - name: alice-reads
    subjects: [{kind: tenant, name: alice}]
    roles: [reader]
```

Built-in roles: `reader`, `content-author`, `tool-runner`, `server-operator`, `admin` (see [access_control_config.yaml](../../access_control_config.yaml)).

## Endpoints

- `POST /auth/login` — `{username, password}` → `{token, expires_at, tenant_id}`. Unauth-listed.
- `POST /auth/logout` — revokes the bearer token. Idempotent.
- `GET /auth/whoami` — returns `{tenant_id, groups, roles}` for the current token.

Always-open regardless of mode: `/health`, `/health/ready`, `/admin/metrics`, `/docs`, `/openapi.json`, `/control_sse*`, plus the three `/auth/*` endpoints. In `standalone` mode these routes still run through the enforce dep, which short-circuits on the unauth allow-list; `custom_openapi` also strips the auto-derived `security` requirement from them so `/docs` doesn't paint misleading lock icons.

## Clients

- **CLI** — `sbs login` prompts for credentials, writes the bearer into `~/.config/restish/apis.json` (`chmod 0600`); restish auto-injects it thereafter. `sbs logout`, `sbs whoami`. `SBS_TOKEN` env var overrides for CI.
- **UI** — In `standalone` mode a `/login` page gates the app. `vite.config.ts` inlines the mode at start-up; `AuthContext` persists the token in `sessionStorage` and installs a `window.fetch` interceptor that adds `Authorization: Bearer` and redirects to `/login` on any 401.
- **Control MCP** — Works transparently: FastApiMCP re-dispatches tool calls through the ASGI stack, forwarding the client's `Authorization` header. Each re-dispatched call hits the enforce dep on the target REST route, so authorization applies per tool call.

## Operator quickstart

```bash
./scripts/setup_user.py alice -b base-user   # prompts for a password, writes the
                                             # user + role binding into the config
# set mode: standalone
# restart the store
sbs login                                    # or use the UI /login page
```

`setup_user.py` runs on its own (re-execing into the project venv when needed).
`-f <file>` targets another config, `-t <tenant>` maps the user onto a different
tenant, `-b <binding>:<role>` names the binding (and shares it between tenants
when it already exists), and `-f -` just prints a bcrypt hash without touching
any file. `-l` lists users as a `USER / TENANT / BINDING / ROLE` table (no
username needed), `-d` deletes one.

## Deferred (see §16 of the full design)

Binding `scope:` (per-namespace / per-object filters — parsed but not enforced), long-lived API tokens, HttpOnly cookies, OIDC/JWT/mTLS providers, session persistence across restarts, UI RBAC-aware hiding.
