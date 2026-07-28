# Access Control — Summary

skillberry-store ships with **Kubernetes-style RBAC** (roles + role bindings) applied by a FastAPI middleware. See [access-control.md](access-control.md) for the full design.

## Modes

Set via `mode:` in [access_control_config.yaml](../../access_control_config.yaml) (overridable with `SBS_ACCESS_CONTROL_CONFIG`).

| Mode | Behavior |
|---|---|
| `disabled` *(default)* | No middleware installed. All endpoints reachable — backward compatible. |
| `standalone` | Bundled username/password IdP mints opaque session tokens; every request is authenticated and authorized. |
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

- **Resource** comes from the endpoint's OpenAPI tag (`skills`, `tools`, `snippets`, `vmcp_servers`, `vnfs_servers`, `admin`, `plugins`) — overridable with `openapi_extra={"x-rbac-resource": "..."}`.
- **Verb** derives from method + path: `list`/`get`/`search`/`create`/`update`/`delete`/`execute`/`admin`. Import ≡ `create`, export ≡ `get`. Overridable with `x-rbac-verb`.

## Config shape

```yaml
mode: standalone
standalone:
  session_ttl_seconds: 43200        # 12h; env override: SBS_SESSION_TTL
  users:
    - username: alice
      password_hash: "$2b$12$..."   # produced by scripts/hash_password.py
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

Always-open regardless of mode: `/health`, `/health/ready`, `/admin/metrics`, `/docs`, `/openapi.json`, `/control_sse*`, plus the three `/auth/*` endpoints.

## Clients

- **CLI** — `sbs login` prompts for credentials, writes the bearer into `~/.config/restish/apis.json` (`chmod 0600`); restish auto-injects it thereafter. `sbs logout`, `sbs whoami`. `SBS_TOKEN` env var overrides for CI.
- **UI** — In `standalone` mode a `/login` page gates the app. `vite.config.ts` inlines the mode at start-up; `AuthContext` persists the token in `sessionStorage` and installs a `window.fetch` interceptor that adds `Authorization: Bearer` and redirects to `/login` on any 401.
- **Control MCP** — Works transparently: FastApiMCP re-dispatches tool calls through the ASGI stack, forwarding the client's `Authorization` header. Same PEP applies.

## Operator quickstart

```bash
python scripts/hash_password.py alice        # prints a bcrypt hash
# paste hash into access_control_config.yaml under standalone.users
# set mode: standalone, add a binding
# restart the store
sbs login                                    # or use the UI /login page
```

## Deferred (see §16 of the full design)

Binding `scope:` (per-namespace / per-object filters — parsed but not enforced), long-lived API tokens, HttpOnly cookies, OIDC/JWT/mTLS providers, session persistence across restarts, UI RBAC-aware hiding.
