# Plugin Identity under Access Control — Design

Scope: establish which tenant identity a plugin operates under, and make plugins
work correctly when `access_control_config.yaml` is in `standalone` mode.
Companion to [access-control.md](access-control.md). **Reference convention:**
`§N` is a section of *this* document; `AC §N` is a section of access-control.md.
The two numberings collide (both have a §1, §3, §11), so the prefix matters.

Three distinct defects motivate this work. From the outside they look like one
bug; they share no cause:

| | Symptom | Cause |
|---|---|---|
| **A** | Every plugin action endpoint returns **500** under `standalone` | Plugin routes carry no `@requires` marker, and the startup audit cannot see them to complain |
| **B** | A plugin has no tenant identity for anything it does | `StoreAPI` calls the service layer in-process; no identity is carried, requested, or checkable |
| **C** | A Claude Code agent handed the store's MCP URL cannot use it | It is an out-of-process caller with no token, and under `standalone` the URL it is given is not mounted |

---

## 1. Principles

Normative. P1–P7 are as stated by the project owner. The subsection below
resolves the one case they leave unnamed, which is also the most common case in
this codebase.

| | Principle |
|---|---|
| **P1** | A plugin's **autonomous** operations execute as its **owner tenant** — the tenant that created it, or one assigned by configuration. Outward calls it makes (store API, other plugins) carry that identity. |
| **P2** | A plugin's **own API** is authenticated when ACL is enabled, exactly like any other store endpoint. |
| **P3** | When an external user calls a plugin's API, every store/plugin call made during that invocation carries the **calling user's** tenant, not the configured one. |
| **P4** | Implementation may follow a **thread-context** model: a plugin carries its default tenant as ambient context, which is **replaced by the calling tenant** for the duration of one of its own API calls. |
| **P5** | An outward invocation attempted with **no tenant assigned** must **fail**, not proceed anonymously. |
| **P6** | These principles concern **which identity is required**, independently of whether outward calls need authentication or secrets. |
| **P7** | The startup route audit must cover **plugin routes too**. Each plugin endpoint declares a specific resource/verb label like any store endpoint, and the audit checks those labels. |

**P6 has since been settled in the affirmative.** It scopes these principles to
identity, leaving open whether a plugin's calls are merely *labelled* with a
tenant or also *authorized*. They are authorized: §2 puts the PDP on both paths,
always. Identity remains the prerequisite, so P1–P5 stand unchanged.

**P4 is not a relaxation — it is the implementation.** Python `contextvars` are
the async-native equivalent of thread-local storage, and asyncio's
context-copy-per-task semantics give P3's "until the API call completes" scoping
for free, with no unwind code. Adopting P4 as the mechanism satisfies P1, P3 and
P5 as written, so **no relaxation of P1–P3 is needed**. §4 verifies this
empirically.

### P1 governs triggers — the boundary is the plugin's own API call

P1 and P3 leave one case unnamed, and it is the most common one here: **seven**
plugins (`evaluator`, `security`, `dedupe`, `doc_generator`, `sast`,
`provenance`, `kagenti-approver`) register `content_added` handlers and act when
content arrives through a **core store** endpoint — `POST /skills/`, an import —
not through a plugin endpoint. (`dependency_tracker` deliberately registers none.)

**Decision: trigger-driven work runs as the owner tenant (P1).** The boundary is
therefore narrow and precise:

> The calling tenant (P3) applies **only** while a plugin is executing one of its
> own API calls. Everything else a plugin does — event handlers, timers,
> background sweeps, startup work — runs as the owner tenant (P1), regardless of
> whether an inbound request caused it.

### Why this is right, and one thing it is not

The event **contract** is genuinely actor-free, and the code confirms it:

```python
def emit_content_added(content_type: str, uuid: str):
    emit_event(f"content_added:{content_type}", uuid=uuid)     # payload: a uuid. No actor.
```

A handler subscribes to "a skill was added", not to "tenant X added a skill".
Nothing in the notification names a tenant.

**But a triggering tenant is nonetheless *available*, and that is the one claim to
be careful about.** Every emit path today runs inside either an HTTP request or a
plugin operation, and `emit_event` dispatches via `loop.create_task`, which copies
the caller's context — so the trigger's tenant is ambiently present at handling
time. The choice of owner tenant is therefore a **policy decision, not a forced
consequence of tenant-free events**. Four reasons it is the right policy:

1. **Depending on an actor the contract never promised is fragile coupling.** The
   trigger's tenant is reachable only as an accident of where the emit sits in the
   call stack. Any emitter that is not request-bound — a filesystem sync, a webhook
   poll, a scheduled reconciler, or `restore_all` if it ever moves from
   `handler.write_dict` to the service layer — supplies none. `emit_event` already
   contemplates such callers: it detects "no running event loop" and skips
   handlers rather than assuming a request. Handlers written against the owner
   tenant keep working under every emitter; handlers written against the trigger
   break or silently misattribute.

2. **Coverage stops depending on who uploaded.** Under trigger-inheritance, an
   auto-scan annotates or fails according to whether that particular tenant holds
   `update` — so a security scanner's coverage becomes a function of the uploader's
   role. That is a bad property for a scanner, and it is what made the
   create-without-update case a problem; owner tenant removes it.

3. **Attribution honesty.** A SAST finding or an approval label is the plugin's
   judgement about content, not an action the uploader took.

4. **Plugin-triggered cascades stay coherent.** `StoreAPI.create_skill` calls
   `skills_service.create`, which emits — so a plugin creating content fires other
   plugins' handlers. Under trigger-inheritance, plugin B's handler would run under
   whatever identity plugin A happened to be carrying, which is incoherent: B
   subscribed to a data change, not to A's identity. Owner tenant gives each
   handler a stable identity of its own no matter who or what caused the write.

**The cost, and a trap worth naming.** Because the trigger's tenant *is* ambiently
present, the event path must **actively override** it (§4.3) rather than getting
the right answer by default. If that override is ever missed or removed, the
system silently reverts to trigger-inheritance — and it will look correct in
testing, because annotations still appear. Only the identity behind them is wrong.
That is why §4.3's regression test (a handler triggered by tenant Y must observe
the owner, not Y) is load-bearing rather than routine.

Two further consequences: §5's owner tenant becomes a **prerequisite** rather than
an optional convenience, and §8's privilege-boundary note becomes load-bearing.

---

## 2. Architecture — one PEP, one PDP, two enforcement points

The requested split is: **one PEP** guarding API entry for core and plugins
alike, authenticating external requests only, with plugin-issued requests
arriving post-PEP; and **PDP admission control always engaged**, for external and
plugin-issued requests both.

**This makes sense and needs no restructuring** — the interception point and the
PDP both already exist; what is missing is a second call site and the plumbing to
attribute it (§2.4). One terminology note first, because it changes where the work
lands: in the NIST/XACML model a PEP is the component that *intercepts and
enforces*, and it necessarily consults a PDP for the decision — a PEP that only
authenticates is an authentication filter, not a PEP. Read that way, the goal is:
**one interception point for external traffic, one PDP, and every authorization
decision made by that PDP no matter which path reached it.** That is what the
rest of this section builds.

### 2.1 Already true today — no work

| Requirement | Status |
|---|---|
| **One PEP for core *and* plugin routes** | **Done.** `SBS.__init__` installs `Depends(make_enforce_dependency(...))` via `FastAPI(dependencies=[...])`, which lands on `router.dependencies` and therefore fires on **every** route registered afterwards, plugin sub-routers included. Proof: defect A's 500 originates *inside* `enforce`, on a plugin route. |
| **Authentication of external requests happens once, centrally** | **Done.** Steps 1–2 of `enforce`: allow-list short-circuit, then token → `Session` → `Subject(tenant_id, groups)`. |
| **Plugin-issued requests are post-PEP** | **Done, for free** — for the one path that exists. `StoreAPI` calls the service layer in-process: no HTTP request, no router, no dependency, so no re-authentication is even possible. It holds because `StoreAPI` is the *only* way a plugin reaches the store; a plugin that issued a real API call would be pre-PEP and re-authenticated like any caller (§4.4). |
| **A single global PDP, callable from anywhere** | **Done.** `pdp.authorize(subject, resource, verb, cfg) -> Decision` is a pure function with no request or FastAPI coupling. |

**One global PDP is the right choice, not one per plugin.** Per-plugin PDPs would
each load the same config and return the same answer for the same inputs.
Per-plugin *policy* — different roles gating different plugins — is a resource
**naming** question (§11), not a reason to instantiate more decision points.

### 2.2 The gap — the plugin path never reaches the PDP

Today `authorize()` is called from exactly one place, inside `enforce`. Core HTTP
requests are therefore admitted by the PDP; plugin-issued store calls are not
admitted at all, because they never touch a route. Two additions close it:

```
external request ──▶ PEP (authenticate, set ambient subject) ──▶ PDP ──▶ route ──▶ service
                                                                │
plugin (in-process) ──▶ StoreAPI ──▶ PDP ──▶ service ───────────┘
                                     ▲
                          same authorize(), same config,
                          subject read from ambient context
```

**Enforcement point 2 is `StoreAPI`**, and that placement is what keeps the
change minimal: `StoreAPI` is constructed once in `SBS.__init__` and handed
**only** to `PluginLoader`. Core routes call the
services directly and never pass through it. So a core HTTP request is decided
once, at the PEP. A plugin's *event-path* work is decided once, at `StoreAPI`,
because it has no route. A plugin *API* call is decided at both — at the door for
what it declared (§6.2) and at `StoreAPI` per object it actually touches — which is
deliberate rather than redundant: the door catches the caller early with a clean
403, and `_admit` covers fan-out the single door marker cannot express. Nothing is
unchecked on any path.

### 2.3 Why not move the decision to the service layer

The tempting alternative is one decision point at the service layer, covering
both callers. Rejected as larger and riskier for no gain:

- It touches ~30 service methods instead of ~30 `StoreAPI` methods, with the same
  arithmetic but a blast radius that includes every core endpoint.
- Route markers would still be required: `mcp_plan.operations_for_user` computes
  each tenant's MCP surface from them for core endpoints, and endpoints with no
  service behind them (`/auth/*`, `/admin/*`, `/health*`) have nowhere else to
  declare intent.
- Leaving the PEP's decision in place as well would double-decide every core
  request; removing it would leave the service-less endpoints unguarded.

### 2.4 The delta, concretely

```python
# 1. access_control/context.py — new, ~5 lines
CURRENT_SUBJECT: ContextVar[Optional[Subject]] = ContextVar("current_subject", default=None)

# 2. access_control/deps.py — one line added to enforce(), after the Subject is built
CURRENT_SUBJECT.set(subject)

# 3. plugins/store_api.py — StoreAPI.__init__ takes `services` only today, so it gains
#    the collaborators it needs. `cfg` is REQUIRED, not defaulted: see the fail-open
#    note below. SBS.__init__ already holds both.
def __init__(self, services, cfg, sessions=None): ...

# 4. plugins/store_api.py — a per-plugin view, so calls are attributable (see below)
def for_plugin(self, slug: str) -> "PluginStoreAPI": ...

# 5. plugins/store_api.py — one helper, then one call per method
def _admit(self, resource: str, verb: str, uuid: str | None = None) -> None:
    """Enforcement point 2: same PDP, subject from ambient context."""
    if self._cfg.mode == "disabled":
        return                                    # no tenants exist; nothing to decide
    subject = CURRENT_SUBJECT.get()
    if subject is None or not subject.tenant_id:
        record_outcome(self._slug, uuid, "error", "no tenant in context")
        raise PluginIdentityError(                # P5
            "no tenant in context; assign an owner tenant for autonomous work")
    decision = authorize(subject, resource, verb, self._cfg)
    if not decision.allowed:
        record_outcome(self._slug, uuid, "error", decision.reason)
        raise PluginAuthorizationError(decision.reason)

def update_skill_tags(self, uuid: str, tags: List[str]) -> bool:
    self._admit("skills", "update", uuid)         # ← the only new line per method
    ...
```

**The pairs `_admit` must cover.** Twenty-six named content and vMCP methods, mapped
the obvious way (`get_*`/`list_*` → `get`, `create_*` → `create`, `update_*` →
`update`, `delete_*` → `delete`). Three are worth naming explicitly, and one of them
is a different *kind* of operation from the rest:

| Method | Pair |
|---|---|
| `get_tool_module` | `tools:get` |
| `update_tool_module` | `tools:update` |
| `execute_tool` | **`tools:execute`** |

`execute_tool` is the only *execution* path `StoreAPI` exposes. It calls
`tools_service.execute` — the same path behind `POST /tools/{uuid}/execute` — so an
owner tenant that needs it holds arbitrary code execution over every tool in the
store. §5.3 grants it, and §8 says what that costs. `get_tool_module` and
`update_tool_module` are the plugin-side equivalents of `GET` / `PUT
/tools/{uuid_or_name}/module`, which declare `("tools", "get")` and
`("tools", "update")`, so the door and `_admit` agree by construction.

Plus §6's walker fix and route markers, which are what let the PEP consult the PDP
for a plugin route at all. `authorize()`, the PEP's existing structure, the config
schema, and every core endpoint stay as they are. `disabled` mode is unaffected by
everything in this section — but **not** by §6; see §2.5.

**`cfg` must be required, not optional.** A `cfg=None` default that skips
enforcement is precisely the fail-open shape §3 faults the old mapper for: a
construction site that forgets to pass it would silently disable enforcement point
2 while every test still passes. `SBS.__init__` already holds `acl_cfg`, so there
is no reason to make it optional.

**`StoreAPI` is a single shared instance today** — the loader does
`plugin.set_store_api(self.store_api)` with the same object for all 16 plugins.
That is why `for_plugin(slug)` is on the list: without it `_admit` cannot tell
which plugin is calling, and three things become impossible rather than merely
awkward:

- `record_outcome` cannot attribute an outcome to a plugin (§9.1);
- an **autonomous** operation — a timer, not an event — has no way to resolve
  *whose* owner tenant applies, since `_run_handler`'s per-handler lookup (§4.3)
  covers only the event path;
- per-plugin authorization granularity (§11) has nothing to key on.

A thin per-slug facade holding `_slug` and delegating to the shared instance is
enough, created once in the loader where `set_store_api` is already called.

**Instrumenting the named methods is sufficient for in-tree plugins, and not
sufficient on its own.** Every bundled plugin reaches the store exclusively through
named `StoreAPI` methods — `get_tool_module`, `update_tool_module`, `execute_tool`,
`update_tool` / `update_skill` / `update_snippet` and the `get_*` / `list_*` /
`create_*` / `delete_*` family — so `_admit` on those methods covers all 16 plugins by
inventory, and no proxy layer is needed to reach them.

The gap is the escape hatch beside them. `StoreAPI` also exposes `tools`, `skills` and
`snippets` as **properties returning the raw service handler**:

```python
@property
def tools(self):
    return self.tools_service.handler       # no method to hang _admit on
```

They carry a `DeprecationWarning` and nothing else, so an out-of-tree plugin reaches
`write_dict`, `write_file` and the locks without passing `_admit` — enforcement point
2 would report full coverage while a third-party plugin bypassed it entirely, the same
false-confidence shape as the audit blind spot in §3. Their setters are also how tests
inject fakes.

Since no in-tree caller depends on them, the cheap closure is to make each property
**raise when `cfg.mode != "disabled"`**: the test setters keep working in `disabled`
mode, and the hole closes without a proxy class. Returning a **guarded proxy** over the
handler is the alternative if an out-of-tree plugin must keep working under ACL —
resource fixed by which property was used, verb derived from the handler method
(`read_file` → `get`, `write_dict`/`write_file` → `update`).

**One property of the write paths is load-bearing and undeclared: annotation writes
do not re-trigger event handlers.** `update_tool` / `update_skill` / `update_snippet`
write through `handler.write_dict`, bypassing the service layer where
`emit_content_updated` lives, and `update_tool_module` reaches
`tools_service.set_module`, which writes via `handler.write_file` and emits nothing
either. So a plugin annotating an object does not re-enter its own handler. §9.1's
`record_outcome` depends on exactly this — a service-layer write would emit
`content_updated` and re-enter the very handlers that just failed. Assert it in a
test: it is incidental to how those service methods are written, not something either
one declares.

`_admit` deliberately raises rather than returning a bool. Translation to HTTP
belongs on the **app**, not in plugin code — one pair of handlers registered in
`SBS.__init__` covers every plugin route without touching any of the 16 plugins:

```python
self.add_exception_handler(PluginAuthorizationError, _403)   # caller lacks the verb
self.add_exception_handler(PluginIdentityError, _500)        # deployment misconfigured
```

A denied plugin action is an authorization failure the caller should see as such; a
missing ambient identity is an operator error, not something the caller did wrong.
**Neither handler fires on the event path** — see §8, which is why `_admit` records
the outcome itself rather than relying on the raise reaching a handler.

### 2.5 Behavior when access control is disabled

`disabled` mode installs no PEP at all (`acl_dependencies` stays empty, so
`router.dependencies` is bare), and there is no tenant concept. Every mechanism in
this design is inert there **except one**:

| Mechanism | In `disabled` mode |
|---|---|
| PEP sets `CURRENT_SUBJECT` | never runs — the dependency is not installed, so the var stays `None` |
| `StoreAPI._admit` | returns on the first line (`cfg.mode == "disabled"`); no PDP call, no P5 failure |
| `PluginAuthorizationError` / `PluginIdentityError` handlers | registered but unreachable, since `_admit` never raises |
| `_run_handler` owner override (§4.3) | runs, sets whatever the resolver returns (likely `None`), and nothing reads it |
| `record_outcome` (§9.1) | still fires for `skip` and `error` from ACL-independent causes — a crash, a missing engine, nothing scannable. This is desirable, not a regression |
| Owner-tenant recording on `PATCH /plugins/{name}` | no subject on the request; must no-op rather than assume `request.state.subject` exists |
| `internal_token()` (§4.5) | returns `None`. A `SessionStore` *is* constructed in `disabled` mode, so minting would succeed — but there is no PEP to validate it and `/control_sse` is already unauthenticated, so minting is pointless. Do not inject an empty `Authorization` header |
| **§6 route markers + audit** | **not inert — see below** |

**The exception: §6 changes startup in `disabled` mode.** `SBS.__init__` calls
`audit_rbac_coverage` unconditionally, and deliberately so — its docstring states
coverage is "a code-correctness property" and that skipping it in `disabled` mode
"would defeat its purpose". Today the audit is blind to plugin routes, so it passes
in every mode. Once §6.1's walker descends `_IncludedRouter`, it sees them in every
mode too. Measured on this checkout with `mode: disabled` and no PEP installed:

```
routes seen by walker NOW   : 63
routes seen by FIXED walker : 94
audit as shipped     : PASSES (plugin routes invisible)
audit, fixed walker  : FAILS — 31 endpoint(s) missing @requires marker(s)
```

For the bundled plugins this is a non-issue: §6.3 annotates all 31 in the same
change. The consequence lands on **third-party plugins**, whose routes are unmarked
and outside this repository — so a deployment that never enables access control
will nonetheless refuse to boot after upgrading. That is the strongest argument in
the design for a warn-then-fail transition, which §6.3 otherwise recommends
against; at minimum it belongs in the release note, phrased as affecting all modes
rather than only `standalone`.

---

## 3. Confirming the cause of defect A

The initial hypothesis was that the call is aborted for lack of tenant context.
**It is not.** The tenant is present, valid, and already admitted by the PDP when
the failure occurs — which is itself why §2's plugin-path work is *new*
capability rather than a fix.

`enforce` runs in a fixed order: (1) allow-list short-circuit, (2) token →
`Session` → `Subject`, (3) `try_map_request`, (4) PDP. The exception fires at
**step 3**, after step 2 produced a valid subject. A missing tenant fails at
step 2 with a 401 — exactly what an unauthenticated call to the same endpoint
returns.

Controlled experiment; same config, token and body, only route markers varied:

```
RUN A (as shipped):      whoami={'tenant_id':'demo','roles':['base-user']}
                         POST /plugins/provenance/check -> UnmarkedRouteError
RUN B (markers stamped): whoami={'tenant_id':'demo','roles':['base-user']}
                         POST /plugins/provenance/check -> 404 "Plugin 'provenance' is disabled"
```

In run B the request clears the PEP as tenant `demo` and reaches the plugin's own
router guard.

**Root cause.** `PluginLoader.mount_routers` attaches plugin routers with
`include_router`, and **FastAPI 0.137 no longer flattens included routes into
`app.routes`** — it nests them under a private `_IncludedRouter` whose
`original_router.routes` holds the real `APIRoute` objects, each still carrying
its unprefixed path (`/check`, not `/plugins/provenance/check`). One change,
three consequences — two active, one latent:

- `stamp_rbac_markers` iterates `_api_routes(app)` → never stamps plugin routes,
  so even a plugin that *does* declare `@requires` would not get its marker
  copied onto the route.
- `audit_rbac_coverage` shares that walker → 31 plugin routes are never examined,
  and the fail-safe boot check passes with a hole exactly where third-party code
  mounts. **This is what P7 closes.**
- `mcp_plan._mcp_marked_routes` keeps its own `app.routes` walk, so it is blind in
  the same way. This one is latent rather than active: no plugin route sets
  `openapi_extra={"x-mcp-tool": True}`, and `SBS.__init__` intersects
  `operations_for_user` with the `x-mcp-tool` set — 0 of 40 marked operations belong
  to a plugin — so plugin operations are absent from every per-user MCP surface
  because they never opted in, not because of this walk. Fixing it matters the day
  a plugin does opt in, not today.

The request path *does* see those routes, because Starlette stamps the matched
`APIRoute` onto `request.scope["route"]`. The mapper finds it, finds no marker,
raises `UnmarkedRouteError` — and `try_map_request` catches only
`UnmappedRouteError`, so it escapes as a 500. The mapper is **fail-crash** where
it was designed to be fail-safe.

---

## 4. Mechanism — ambient tenant via `contextvars`

### 4.1 Shape

- **Set by the PEP** (§2.4 item 2), immediately after the `Subject` is built.
  Covers P3 for every authenticated request, plugin or core, with no per-plugin
  work.
- **Set from the owner tenant** (P1) for everything outside a plugin's own API
  call: by `_run_handler` on the event path (§4.3) and at autonomous entry points,
  resolved lazily in both cases (§5.2).
- **Read by `StoreAPI._admit`** and by the token accessor in §4.5.
- **Never read by plugin code.** Plugins stay unaware; that is the point of
  ambient context over threading a `tenant_id` through ~30 `StoreAPI` methods
  and every plugin call site.

### 4.2 Propagation, verified

Five paths matter, because plugin code runs behind all of them. Measured against a
FastAPI app with the var set in a dependency:

| Path | Where it occurs | Result |
|---|---|---|
| `async def` endpoint | most plugin routes | **propagates** |
| `def` endpoint (threadpool) | several core routes, e.g. `start_vnfs_server` | **propagates** |
| `loop.create_task(...)` | exactly `plugins/events.py::emit_event` | **propagates** |
| `asyncio.to_thread(...)` | `dast` offloads its whole scan (`plugin.py:578`) | **propagates** — `to_thread` runs the callable inside a copied context, and an `asyncio.run` nested inside *that* inherits it too |
| raw `threading.Thread(...)` | `dast._run_bounded` (`plugin.py:443`); `VirtualMcpServer`'s uvicorn thread (`vmcp_server.py:796`) | **does NOT propagate** — a fresh thread starts with an empty context |

The third row is the one that needs **neutralizing** rather than exploiting.
`emit_content_added` is called from inside the service layer
(`skills_service.py:233`, `tools_service.py:334`, `snippets_service.py:146`), so
a handler task inherits the triggering request's context — which under §1's
decision is the wrong tenant. §4.3 overrides it.

Cross-request leakage was tested separately and does **not** occur: a request
that never calls `.set()` — an allow-listed path, or `disabled` mode — observes
`None`, not a previous request's tenant, for both async and sync endpoints. This
matters for P5, since a leaked value would let an autonomous operation silently
inherit some earlier user's identity instead of failing.

There is no existing `contextvars` usage in `src/` or `plugins/`, so this
introduces no interaction with prior art.

### 4.2a The raw-thread rule, and the one plugin it binds

The fifth row is not hypothetical: **one bundled plugin makes store calls from a raw
thread.** `dast._run_bounded` uses a raw daemon `threading.Thread` deliberately —
that is what lets a hung tool be abandoned without keeping a non-daemon executor
thread alive — and the MCP-scope path runs `twin.drive_tool(...)` inside it. The
twin's `StoreApiToolSource` executes through `StoreAPI.execute_tool`, so that thread
does reach `_admit`, with an empty context. Measured:

```
inside asyncio.to_thread                  : tenant-Y
asyncio.run nested in to_thread           : tenant-Y
raw threading.Thread (dast._run_bounded)  : None       ← _admit raises P5
raw thread + copy_context().run           : tenant-Y
```

Left alone, every twin-mediated tool call fails with `PluginIdentityError`, and — per
§8 — `_run_handler` swallows it into a log line on the event path. It is gated behind
DAST live mode (`self._live`, an env var), so it is not the default path, but it is
the *documented* faithful-twin path, and the MCP scope is always part of the
cumulative scope once live is on. The sibling call `_run_executor_bounded` →
`FileExecutor.execute_file_sync` is unaffected: it touches no store.

**The rule this establishes, which belongs in the plugin contract:** work offloaded
to a thread the asyncio machinery did not create for it must carry the context
explicitly.

```python
ctx = contextvars.copy_context()
threading.Thread(target=ctx.run, args=(work,), daemon=True).start()
```

The dividing line is narrower than it looks, and worth stating exactly, because two
of the four ways to reach a thread do not propagate. Measured:

| Offload | Propagates? |
|---|---|
| `asyncio.to_thread(fn)` | **yes** — copies the context explicitly |
| Starlette's `run_in_threadpool` (the `def`-endpoint path, via anyio) | **yes** |
| `loop.run_in_executor(None, fn)` | **no** |
| `ThreadPoolExecutor.submit(fn)` / `threading.Thread(target=fn)` | **no** |

The same shape occurs a second time in `VirtualMcpServer`'s `serve=True` transport,
which runs handlers on a raw daemon thread with its own event loop — so a plugin that
serves a twin over a port hits it without any bounded-execution wrapper of its own.
Auditing for this is cheap: `dast` is the only plugin whose raw thread performs store
work (the threads in `skill-optimizer` and `anthropic-skill-generator` only stream
Docker logs).

### 4.3 Overriding the ambient subject on the event path

§1 requires trigger-driven work to run as the owner tenant, so the inherited
context must be replaced before a handler runs. The machinery for this already
exists: `PluginLoader.discover_plugins` calls
`plugin_events.register_handler_owner(func, slug)` for every handler a plugin
registers, so `_handler_owners` already maps handler callable → owning plugin.
That map is what the enable-resolver uses; the same lookup gives the owner tenant.

Set it inside `_run_handler`, not at task creation:

```python
async def _run_handler(handler, **kwargs):
    # P1: trigger-driven work runs as the owning plugin's owner tenant, never as
    # the tenant whose request happened to emit the event.
    token = CURRENT_SUBJECT.set(_owner_subject_for(handler))   # None if unassigned
    try:
        await handler(**kwargs)
    except Exception as e:
        logger.error(...)
    finally:
        CURRENT_SUBJECT.reset(token)
```

Each handler task already owns a copied context, so a `set` here is private to
that task and cannot leak back to the request or across to a sibling handler.
Doing it here rather than passing `context=` to `loop.create_task` keeps it to one
function and avoids depending on that parameter's availability.

**Where `_owner_subject_for` comes from.** `plugins/events.py` is a standalone
module with no access to the ACL config or the plugin config store, so the owner
lookup has to be injected — and there is already a precedent to copy exactly:
`PluginLoader.__init__` does `plugin_events.set_enabled_resolver(self.config.is_enabled)`
to give the module its enable check. Add `set_owner_resolver(...)` alongside it,
resolving slug → `Subject`. This keeps the lazy resolution §5.2 requires (the
resolver is called per dispatch, not captured at startup) and keeps `events.py`
free of imports it should not have.

Note what happens when no owner is assigned: the subject becomes `None`, and P5
then fails every outward call the handler attempts. That is the intended
behavior — but it means **all seven auto-triggering plugins stop working under
ACL until an owner tenant is configured**, and `_run_handler` swallows the
resulting exception into a log line. §8 treats this as the design's sharpest
operational edge.

### 4.4 Plugin-to-plugin calls — deferred

P1 and P3 both mention "other plugins", meaning a plugin issuing an API call against
another plugin's API exactly as it would against the core store API. **The identity
question has the same answer in both cases**, by the same principles: the call carries
the ambient subject — the calling user under P3, the owner tenant under P1.

**What makes the two cases unequal is the mechanism, not the identity.** A plugin
reaches the core store through `StoreAPI`: a privileged in-process interface onto the
service layer, with no HTTP, no router and no PEP, so the ambient subject is simply
read at `_admit` (§2.2). **No equivalent facility exists for plugin APIs.** The only
way to reach another plugin is its route, and every plugin route sits behind the PEP,
which requires a bearer token and derives the `Subject` from the resolved session
rather than from ambient context. A plugin-to-plugin call therefore needs a token
minted for the ambient subject — §4.5's mechanism — even though it never leaves the
process. **The boundary that matters is the PEP, not the process.**

**Decision: deferred.** Nothing needs it. Cross-plugin awareness is limited to reading
another plugin's results out of `extra` (as `provenance` does with SAST findings), and
no plugin issues an API call to another. Two things to pick up whenever it is taken on:

- **§4.5's token minting stops being an out-of-process concern.** It becomes the
  general answer to "a plugin makes an API call", loopback included, and §2.1's
  "plugin-issued requests are post-PEP" narrows to "`StoreAPI`-issued requests are".
- **§5.3's role gains the callee's verbs.** The target route's `@requires` marker is
  evaluated against the *caller's* identity, so under P1 the owner tenant must hold
  whatever the target declares — `("plugins", "get")` for a sibling's `/status`,
  `("skills", "update")` for another scanner's `/scan`. `plugin-agent` as written
  anticipates none of this.

**The likelier resolution is architectural rather than incremental.** Running plugins
as processes outside the store turns this from a special case into the ordinary one:
an out-of-process plugin has no privileged in-process interface to preserve, so every
call it makes — core API or sibling plugin — is an authenticated API call through the
one PEP, with §4.5's minted token as the single identity mechanism. §2.2's two
enforcement points would collapse back into one, and this section would disappear
rather than grow. That change reaches well beyond identity and is out of scope here,
but it is the direction this asymmetry points at.

### 4.5 Out-of-process — materializing the ambient tenant

Context variables stop at the process boundary, which is defect C. The
runspace-backed plugins (`ask-runspace`, `skill-optimizer`,
`anthropic-skill-generator`) hand a Claude Code agent the store's own MCP URL so
the agent can persist its work. That config carries a URL and nothing else, and
two independent things are broken, so fixing one leaves it broken:

**No credential.** Per AC §10.2 the SSE handshake is allow-listed but every
re-dispatched tool call goes through `enforce`. The agent connects, then 401s on
every store operation.

**The URL is not mounted.** `_store_mcp_url()` returns `.../control_sse`, but
`SBS.__init__` mounts the bare `/control_sse` **only in `disabled` mode**; under
`standalone` it mounts one per user in `cfg.users`:

```
control_sse mounts: ['/control_sse/demo', '/control_sse/demo/messages/',
                     '/control_sse/skillberry', …, '/control_sse/skillberry-admin', …]
ask-runspace targets: /control_sse        ← not mounted
```

**Resolution, needing no stored secret.** `SessionStore.mint(tenant_id, groups,
ttl)` takes no credential; `AuthService.login` performs the bcrypt check and
*then* calls it as a separate step. A plugin shares the process with that session
store, so the store can mint a session for the **ambient subject** and inject it:

```python
{STORE_SERVER_NAME: {"type": "sse",
                     "url": _store_mcp_url(),                  # per-subject mount
                     "headers": {"Authorization": f"Bearer {token}"}}}
```

Under P3 the token is minted for the **calling tenant Y**, so the agent's calls
re-enter through the PEP as Y and are admitted by the same PDP against Y's role —
attribution and authorization both follow the user, and nothing is escalated.
Under P1 it is minted for the owner tenant. Either way: no password, no bcrypt
hash, no environment variable, nothing on disk. The credential is derived from
identity the store already holds and dies with the process.

Consequence for the mount: the per-subject loop is driven by `cfg.users`, so a
tenant with no `standalone.users` entry gets no MCP mount.
`operations_for_user` computes its surface from `(tenant_id, groups)` against the
bindings and works on any subject unchanged — only the iteration source widens.

---

## 5. Owner tenant (P1)

### 5.1 There is nowhere to record it today

P1 offers two sources. Only one is currently expressible:

- **"assigned by configuration"** — straightforward; a new mapping in the ACL
  config or the plugin config file.
- **"the tenant that created it"** — **no such record exists.** Plugins are
  discovered from `importlib.metadata` entry points at startup and instantiated
  before any tenant exists. `PluginConfigStore` persists exactly one thing, a
  `disabled` list; there is no owner field and no plugin-creation event to hang
  one on.

The closest real record is **the tenant that enabled it**:
`PATCH /plugins/{plugin_name}` already exists and already requires
`plugins:update`. Recording the acting tenant there gives P1's first source a
meaning:

```json
{ "disabled": ["dedupe"], "owners": { "sast": "team-blue", "provenance": "team-blue" } }
```

Precedence: per-plugin owner → deployment-wide default from the ACL config →
**none, and P5 applies**.

The earlier recommendation here — keep the deployment-wide default opt-in, so P5
stays observable — **does not survive §1's decision**. With triggers running as
the owner tenant, no default means a fresh `standalone` deployment has seven
plugins whose auto-triggers all fail on the first import. Ship a default, and make
P5 observable the other way: surface "no owner tenant" in each plugin's status
message and on the affected object (§8), rather than relying on total failure to
make the gap noticeable.

### 5.2 Resolve lazily, never at construction

Plugins are constructed at startup and register their event handlers inside
`__init__` — before any tenant, session, or config reload. The owner must be
resolved **at call time**, which also keeps a config reload effective without a
restart, matching AC §5.4.

### 5.3 The role for a configured owner

When an operator assigns an owner tenant that exists only to run plugins, it
needs a role: content authorship, tool execution, and virtual-server publication —
nothing more. It never mentions the `admin` resource, and `/admin/backup`,
`/admin/restore` and `/admin/purge-all` all declare `@requires("admin", "admin")`, so
they are out of reach by construction rather than by omission:

```yaml
- name: plugin-agent
  rules:
    - resources: [skills, tools, snippets]
      verbs: [list, get, search, create, update, delete]
                                                     # delete: simulate's teardown
                                                     # removes the sim skill/tools
                                                     # it created (§6.2)
    - resources: [tools]
      verbs: [execute]                               # StoreAPI.execute_tool —
                                                     # dast's twin runs the skill's
                                                     # tools through the store's own
                                                     # execution path (§2.4, §8)
    - resources: [vmcp_servers, vnfs_servers]
      verbs: [list, get, create, update, delete, execute]
                                                     # execute == start; this is
                                                     # what "export over vNFS /
                                                     # WebDAV / vMCP" requires.
                                                     # delete: simulate again
    - resources: [facets, plugins]
      verbs: [list, get, search]

bindings:
  - name: plugin-agent-binding
    subjects:
      - kind: tenant
        name: plugin-user      # virtual: no standalone.users entry, no password
    roles: [plugin-agent]
```

`plugin-user` is deliberately a **virtual subject**: present in `roles` and
`bindings` so its grants are reviewable in the same YAML as every other grant,
but with **no `standalone.users` entry**, therefore no password hash and no way
to log in from the network — `POST /auth/login` as `plugin-user` returns
`invalid_credentials` like any unknown user. The identity is unforgeable from
outside because no credential for it exists anywhere. Because it is not in
`cfg.users`, §4.5's mount loop must iterate "subjects needing an MCP surface"
rather than `cfg.users` alone.

**`delete` and `tools:execute` are the two grants worth defending, because both look
omittable and neither is.** `simulate` deletes the sim skill, tools and vMCP it
created on teardown, so without `delete` every simulation leaks four objects and a
container. `dast`'s twin executes the skill's tools through `StoreAPI.execute_tool`,
so without `tools:execute` a live scan is denied on every call. Withholding either
does not make the deployment safer; it makes a bundled plugin fail.

The cost is that the token minted in §4.5 carries both. `execute_tool`,
`update_tool_module` and the `delete_*` operations are all on the `x-mcp-tool`
surface, so an agent handed an owner-tenant token can run and rewrite arbitrary tool
code — a sharper edge than "content authorship", and §8's trade-off in its strongest
form.

One asymmetry to keep in mind: `StoreAPI` exposes no vNFS methods (it holds a
`vnfs_service` and never uses it), so the `vnfs_servers` grants above are reachable
only over §4.5's MCP path, not in-process. They are not dead — `create_vnfs_server`
and `start_vnfs_server` are both on the MCP surface — but no bundled plugin exercises
them.

---

## 6. Marked and audited plugin routes (P2, P7)

### 6.1 One walker repairs three things

`stamp_rbac_markers` and `audit_rbac_coverage` both iterate
`audit.py::_api_routes(app)`. Teaching that single generator to descend
`getattr(route, "original_router", None)` recursively fixes **marker stamping and
the coverage audit at once**:

```python
def _api_routes(app_or_router) -> Iterable[APIRoute]:
    for route in getattr(app_or_router, "routes", []):
        if isinstance(route, APIRoute):
            yield route
            continue
        # FastAPI >= 0.137 nests include_router() routes under _IncludedRouter.
        included = getattr(route, "original_router", None)
        if included is not None:
            yield from _api_routes(included)
```

The `getattr` guard keeps it correct on FastAPI versions that still flatten.
`mcp_plan._mcp_marked_routes` should switch to the shared generator for
consistency, though nothing changes observably until a plugin opts into
`x-mcp-tool` (§3). Run B in §3 confirms these are the right
route objects: stamping `original_router.routes` is what made the request pass
the PEP.

### 6.1a What the fixed walker covers, and what still escapes it

Measured on this checkout. With the recursive generator above:

| Shape | Audited? | Runtime behavior if unmarked |
|---|---|---|
| Plain `APIRoute` in a plugin router | **yes** — all 31 bundled routes | 500 today; correct allow/deny after §6.2 |
| Routes of an **admin-disabled** plugin | **yes** | router is mounted regardless (guarded by a 404), so 13 of the 16 plugins here are disabled and still audited |
| Nested `include_router` inside a plugin router | **yes** — the generator recurses | as above |
| `APIWebSocketRoute` | **no** — not an `APIRoute` | enforce dep runs and the handshake fails; **fails closed** (broken, not bypassed) |
| Sub-app `Mount` | **no** | **`200` with no token at all** — see below |
| Routes added after startup | **no** — the audit has already run | `mapper.py` names this as the reason `UnmarkedRouteError` exists as a backstop |

So the answer to "does the audit cover configured plugins" is **yes once §6.1 lands,
for every plugin route that is an `APIRoute`** — which is all 31 bundled ones,
enabled or disabled. The gaps are shapes no bundled plugin currently uses, but
nothing stops one from using them.

**The `Mount` case is a real hole, not a theoretical one.** A Starlette `Mount` is
outside the FastAPI dependency chain entirely — the same property `deps.py` already
documents for the `/control_sse` mounts — so a plugin doing
`router.mount("/subapp", Starlette(...))` exposes a surface that is unauthenticated,
unauthorized, and invisible to the boot check. Verified against the real enforce
dependency in `standalone` mode:

```
APIRoute   POST /plugins/demo/scan          -> 500   (the known defect)
WebSocket  WS   /plugins/demo/ws            -> handshake refused (fails closed)
Mount      GET  /plugins/demo/subapp/inner  -> 200 'reached the sub-app'   (no token)
```

**Recommendation: the audit should reject non-`APIRoute` route objects found inside
a plugin router**, rather than skipping them the way it skips `Mount` objects on the
core app (where `/control_sse` is a deliberate, allow-listed exception). A plugin
declaring an unguardable surface is exactly the class of problem a boot-time
coverage check exists to catch, and refusing it costs one `isinstance` branch in the
same generator. Silently ignoring it means P7 reads as "all plugin endpoints are
checked" while a plugin can opt out by choosing a different route type.

### 6.2 What a plugin route declares

P7 asks for a specific label per endpoint, **like a core store endpoint** — not a
loader-applied default. That is also consistent with `decorator.py`'s stated
rationale: the ACL design deliberately removed method/path inference because it
"had a fail-open failure mode", and a default verb chosen by the loader would
quietly reintroduce it.

"Like a core store endpoint" is the operative phrase, and it settles what the
label should say. A core endpoint that updates a skill declares
`@requires("skills", "update")` — it names the resource it acts on, not the
subsystem it belongs to. A plugin endpoint follows the same rule:

```python
from skillberry_store.plugins.base import PluginBase, requires

@requires("tools", "update")          # what the scan actually does to the store
@router.post("/scan")
async def scan(...): ...

@requires("plugins", "get")           # a genuine plugin-management endpoint
@router.get("/status")
async def status(...): ...
```

`requires` is re-exported from `skillberry_store.plugins.base` so authors do not
reach into `access_control` internals.

**Declaring the honest resource is materially better than a blanket
`("plugins", "execute")`**, and it resolves three things at once:

- **The denial moves to the door.** A `base-user` invoking a scan is refused with a
  clean 403 before any work starts, instead of failing partway through at
  `_admit`.
- **Granularity comes for free.** `plugins:execute` as a universal front-door verb
  would be all-or-nothing across all 16 plugins, with nothing to discriminate on
  now that object scope is out (§7). Content resources discriminate naturally.
- **Affordance needs no new plugin contract.** The marker *is* the declaration.
  After §6.1's stamping, every plugin route carries `x-rbac-resource` /
  `x-rbac-verb` in `openapi_extra` — and the generated schema does reach them:
  `app.openapi()` already lists 33 `/plugins/...` paths, so the nesting that hides
  routes from the audit does not hide them from OpenAPI. `get_plugin_info` already
  calls `plugin.get_router()`, so surfacing the pair per action there lets the UI
  evaluate it against the requesting subject via `authorize()` and grey out the
  button with a reason. No `ui_config` schema addition, no second declaration to
  keep in sync.

**The marker describes the action's effect on store resources, not its internal
mechanics.** Some plugins own substantial machinery of their own: `dast` constructs a
private `FileExecutor` to run the skill under test and a private `VirtualMcpServer` as
a benign observation twin, both from `skillberry_store.standalone` — the sanctioned
surface for components a plugin may construct and own — while `simulate` spawns a
Docker container through its own harness manager, importing nothing from the store
beyond the plugin contract.

**Owning such an instance is code sharing, not an access-control bypass.** `dast`'s
twin is the plugin's own: `serve=False`, no port, no transport, outside the shared vMCP
port range, and not a store-managed `vmcp_servers` object. The test for a bypass is
whether it permits something ACL would otherwise deny; a privately constructed sandbox
permits nothing ACL governs, and if `dast` reimplemented container execution itself
instead of importing it, nothing about access control would change.

**Two things that machinery does reach, which the marker rule has to account for.**

*`dast` invokes the store, through the twin.* The twin's `StoreApiToolSource` resolves
manifests via `StoreAPI.get_tool` and executes via `StoreAPI.execute_tool` —
deliberately, so the twin is *faithful*: the skill's tools run exactly as they would in
production, dependency closure and all. A `dast` scan therefore fans out to
`tools:get`, **`tools:execute`**, and `skills|tools|snippets:update` (its writer
dispatches on object type). All of it is covered by `_admit`, and `dast` is the
design's clearest example of the one-pair friction below.

*`simulate` creates real store objects.* Its orchestrator calls `create_tool`,
`create_skill` and `create_vmcp` for the simulation, then `delete_vmcp` /
`delete_tool` / `delete_skill` on teardown. Only the Docker container is private, so
`simulate` too is fully covered by `_admit` — and it is why §5.3 grants `delete`.

**The one exception to "imports are not an authorization boundary".**
`standalone.VirtualMcpServer` falls back to `_HandlerToolSource` when no `tool_source`
is injected: the `ObjectHandler` singletons plus the service registry, reading
manifests and module files, walking dependencies and executing — entirely outside
`StoreAPI` and therefore outside `_admit`. The module docstring offers that fallback
as supported, so a plugin can obtain unguarded read and execute over every tool in the
store with one import and no `tool_source`. Close it: either require `tool_source` when
ACL is enabled, or route the default source through `StoreAPI`. (`FileExecutor` needs
no such treatment — it takes the source as an input, which the caller obtained through
`StoreAPI` in the first place.)

The practical rule that follows: declare the marker from what the action does to the
**store**, ignoring how it computes the answer. `dast` writes `dast:` tags and
`extra["dast"]`, so its scan route declares `("skills", "update")` — the object it
annotates — and leaves the `tools:get` / `tools:execute` fan-out to `_admit`.

(Separately checked and clear: the four plugins importing
`skillberry_store.tools.anthropic` — `anthropic-skill-generator`, `skill-optimizer`,
`skillssh-importer`, `provenance` — are not a write bypass either. Those functions
parse and return `(skill_name, description, tools, snippets, ignored)` in memory;
persistence still happens through `StoreAPI` afterwards.)

**The one friction: `@requires` holds exactly one pair.** `get_marker` returns a
2-tuple and the mapper reads a single resource/verb, so an action that fans out
cannot express its full requirement at the door. Two bundled plugins fan out, in
different directions: SAST scanning a skill touches its tools *and* its snippets
(fan-out across **resources**), while DAST needs `tools:get` and `tools:execute` on
the way to a `skills:update` (fan-out across **verbs**). Declare the coarsest honest
requirement at the door and let `_admit` catch the remainder per object. Widening the
marker to a list would ripple through `decorator.py`, `mapper.py`, `audit.py` and
`mcp_plan.py`, which is still not worth it for two cases; but it is why `_admit`
stays necessary rather than becoming redundant.

Two layers therefore remain, now often checking the same pair at the door and the
first object, and genuinely divergent only on fan-out and on the event path (which
has no route at all) — this is §2.2's diagram expressed per-route:

| Layer | Question | Decided by |
|---|---|---|
| Plugin endpoint (`@requires`) | may this caller invoke this action at all? | PDP, via the PEP |
| `StoreAPI._admit` | may that identity perform each resulting store operation? | PDP, via ambient subject |

### 6.3 Migration

The audit becoming effective is a **breaking change by design**: 31 routes across
the 16 bundled plugins are unmarked, and startup will refuse until each is
annotated. That is mechanical and belongs in the same change as §6.1 — landing
the walker fix alone trades a runtime 500 for a boot failure.

Third-party plugins outside this repository will fail to boot on upgrade — and per
§2.5 that includes deployments running `mode: disabled`, which have no access
control and no reason to expect an ACL-related boot failure. This needs a release
note and a documented contract, phrased as affecting **all modes**.

A warn-then-fail transition weakens P7, which is why the recommendation elsewhere
is to fail immediately; the `disabled`-mode reach is the one argument on the other
side, and it is a real one. A narrower compromise preserves P7 where it matters:
fail immediately in `standalone` (an unmarked route there is a live authorization
hole), and warn for one release in `disabled` (where no decision is being skipped
because no PEP exists). That keeps the audit fail-safe exactly where fail-safe
means something.

---

## 7. Non-goal: object-level scope

Admission control decides on **role and verb alone**. No object identity is
consulted anywhere in this design — not by the PEP, not by `_admit`.

This is a deliberate decision, not an omission, and it matches what the codebase
can express: `authorize()` has no object parameter, `scope:` on bindings is
accepted by the schema and ignored by the PDP (AC §11 defers it), and there is no
ownership fact to test against — `tenant` appears nowhere in `services/`, the
handlers, or storage.

The consequence to keep in view: an operator should not read "plugin operations
run as tenant Y and are admitted by the PDP" as "tenant Y can only touch tenant
Y's objects". Any tenant granted a verb holds it over **every** object of that
resource type. Per-object restriction requires AC §11's scope work and is out of
scope here.

Because scope is out, `(resource, verb)` is the *only* axis of discrimination
available — which makes §11's first open question a decision that has to be made
now rather than deferred.

## 8. Accepted trade-offs and limits

**A minted token is a real bearer token.** Anything it is handed to inherits the
subject's rights until it expires. Keep the TTL short and refresh on demand
rather than minting long-lived tokens at startup, and never log one.

**Handing one to an agent is a deliberate delegation.** Giving Claude Code a
token for tenant Y is the *point* of §4.5, but the agent can then do anything Y
can. Under P3 that is bounded by Y's own role rather than escalating; it remains
a reason `ask-runspace` should not be exposed on a public deployment.

**Sessions are per-process (AC §7.2).** A minted token is valid only on the replica
that minted it. Fine while plugin and store share a process; a multi-replica
deployment where the agent's call is load-balanced elsewhere will 401. A shared
session store is a prerequisite, out of scope here, and must not be discovered in
production.

**P5 is only as good as the absence of a silent default.** If a deployment-wide
owner tenant is configured, no autonomous operation ever reaches the P5 failure.
A legitimate operator choice, but it should be an explicit one.

**The owner tenant is a deliberate privilege-boundary crossing.** Under §1's
decision, a low-privilege tenant who imports a skill causes writes performed as
the *owner* tenant, which typically holds more privilege than they do. That is
the intent — the annotation is the plugin's judgement, not the user's — and it is
how CI-style system annotation normally works. The bound that makes it safe is
that the **plugin** decides what gets written — and, since §5.3 now grants
`tools:execute`, what gets **executed**. Note that bound softens for plugins whose
write content is derived from the uploaded material by
a model (`doc_generator`, `creator`, SAST's *Fix*): there, uploaded text
influences what gets written at owner privilege. Not an argument against the
decision, but a reason those plugins deserve more scrutiny than the deterministic
ones.

**Execution at owner privilege is the sharpest instance of that.** `dast` runs the
uploaded skill's tools through `StoreAPI.execute_tool` as the owner tenant, on a
trigger the uploader caused. The uploaded code is what runs — so a `base-user`
import, refused `tools:execute` at every door, nonetheless causes that tenant's own
code to execute.

The execution itself is not an added capability: `execute_tool` is the same
`tools_service.execute` path behind `POST /tools/{uuid}/execute`, with the same
isolation (a container for code-packaged Python unless `execute_python_locally` is
set). What the owner tenant changes is the **trigger** — from an authenticated caller
holding `tools:execute` to whoever uploaded the content. The usual bound, "the plugin
decides", holds here only in the weak sense that the plugin decides *whether* to run
the code, not *what* the code does. This is the one place where owner privilege and
attacker-supplied input meet directly. Mitigating it is out of scope; what bounds it
in practice is that `dast`'s live mode is off unless an operator enables it, so the
trade-off arrives with that switch rather than at rollout.

**On-demand and triggered runs of the same action differ — by design.** SAST
scanning on import runs as the owner tenant and succeeds; the identical scan
invoked from the UI runs as the caller (P3) and, for a `base-user` tenant, is
refused at the door, because §6.2 has the scan route declare `("tools", "update")`
and `base-user`'s verbs are `list, get, search, execute`.
An `admin` (`resources: ["*"], verbs: ["*"]`) passes both checks and can drive
every plugin manually.

**This is the intended semantics, and it is the opposite of setuid.** The owner
tenant's privilege is used only for the plugin's own autonomous judgement; it is
never lent to a user who asks for it. A caller gets exactly their own rights, so
"the plugin can do it" never becomes "therefore I can ask the plugin to do it for
me". Seeing a plugin in the catalogue is not entitlement to drive it.

What remains is a **discoverability** defect, not an authorization one: the UI
renders an action the user cannot invoke, and they learn it only from a 403 after
clicking. P7's markers already carry the answer, so no new declaration is needed —
see §6.2. Because each route declares the resource and verb it actually needs, the
plugin-info endpoint can evaluate that pair against the **requesting** subject via
`authorize()` and report it per action, letting the UI disable the button with a
reason. This is the same shape SAST already uses to gate its *Fix* button on
`ui_config.capabilities.fix`; the difference is that the input is a marker the
plugin was required to write anyway rather than a second thing to keep in sync.

**Denials on the event path are invisible by construction, and now routine.**
`events._run_handler` wraps every handler in `except Exception: logger.error(...)`
and never re-raises, and background tasks sit outside any request, so the
app-level exception handlers in §2.4 cannot fire. Combined with §4.3, an
unassigned owner tenant means all seven auto-triggering plugins fail silently: the
user's import succeeds, no annotation appears, and the UI cannot distinguish
"scanned and clean" from "not permitted to scan" from "no owner configured". This
was a corner case when triggers inherited the trigger's tenant; with P1 governing
triggers it is the **default state of a fresh ACL deployment**. A counter metric
is the minimum; a marker written to the object (`sast:denied`, mirroring the
existing `not_installed` reporting) is better, and the plugin status message
should say plainly when a plugin has no owner tenant.

---

## 9. Observability of plugin outcomes

### 9.1 Outcome labelling — three states

Plugins label **successes only** today. Everything else — nothing scannable, a
missing engine, an exception, and (once §2 lands) an authorization denial —
leaves no trace on the object but a `logger.error` line, and is therefore
indistinguishable from "never ran".

Three terminal states, one per run, mutually exclusive:

| State | Meaning | Detail |
|---|---|---|
| **result** | the plugin reached a judgement | plugin-defined; for SAST this is the existing `sast:clean` / `sast:high:2` |
| **skip** | the content did not warrant analysis | reason in `extra` |
| **error** | the analysis could not be performed | reason in `extra` — no tenant, unauthorized, engine missing, crash |

**`result` is not a new tag** — it is whatever the plugin already writes, so no
`sast:result` marker gets layered on top of `sast:clean`. Only `skip` and `error`
are additions.

**Keeping the vocabulary closed matters more than it looks.**
`services/facets.py` enumerates every unique tag in the store to populate the
UI's tag picker, so a tag family that grows one entry per failure mode
(`sast:denied`, `sast:no-owner`, …) degrades the filter UI as it grows. Three
fixed states keep the picker stable while `extra` absorbs unbounded diagnostic
detail — which is also how the plugin already reports `not_installed` and
`language_unsupported` per engine inside its result block. Cause belongs in the
block; category belongs in the tag.

The discriminator to give plugin authors, since `skip` and `error` are otherwise
easy to confuse: **skip means the content didn't warrant analysis; error means the
analysis couldn't be performed.** So a non-Python file is `skip`, while Bandit not
being installed is `error`.

`skip` and `error` must live in the same tag family the plugin already strips on
re-scan (`_strip_sast_tags` and its equivalents), so a later successful run
replaces them rather than accumulating alongside a stale failure.

**One circularity to resolve, which applies specifically to `error`.** Writing an
outcome tag *is* an update to the object — so a plugin denied `update` by `_admit`
cannot record its own denial, and a plugin with no tenant at all (P5) cannot write
anything either. The two states most worth recording are exactly the two that
cannot record themselves.

The resolution is that **the framework records the outcome, not the plugin**: the
`_admit` raise site and the `_run_handler` wrapper both sit above plugin code, so a
single `record_outcome(slug, object_ref, state, reason)` there covers every plugin
at once with a store-level write the plugin's identity does not gate.

**Concretely, `record_outcome` must reach the service handler directly, not through
the `StoreAPI` method that looks like the natural choice.** `update_skill(uuid, obj)`
is exactly the write it wants — and once §2.4 lands, it is also a method whose first
line is `self._admit("skills", "update", uuid)`, precisely the call that just failed.
Going through it would re-enter the denial it is trying to record. Writing at the
handler level avoids both that and the re-emission problem (§2.4).

Two prerequisites, both in §2.4 rather than here: `_admit` has to receive the
object uuid (it takes only `resource, verb` as first drafted, which would leave
`record_outcome` with nothing to label), and the calling plugin has to be
identifiable — which the single shared `StoreAPI` instance does not permit today,
hence the per-slug facade. That also gives
§9.2 its emit point for free — one call writes the tag and appends the message —
and it means the state vocabulary belongs in `plugins/base.py`, defined once
rather than per plugin.

### 9.2 A system-messages feed — worth doing, and not as cheap as it looks

The OpenShift analogy is apt, and the closer one is the Kubernetes Events API: a
bounded ring of recent `(reason, message, involvedObject, count, timestamp)`
records that the console surfaces in a drawer.

**What can be reused is less than the route names suggest.** `/changes` sounds
like an event feed but is not:

```python
"""Global mutation counter — incremented on every write or delete."""
_count = 0
def bump() -> None: ...
def get() -> int: ...
```

It is a single integer the UI polls to decide when to refresh. So there is no
message store, no retention, and no delivery mechanism to extend. What *is*
reusable is the **idiom**: bump-a-counter, poll cheaply, fetch on change. A
messages feed can follow the same shape — a ring buffer plus a counter, one
`GET /system-messages` endpoint marked `@requires("system", "list")`, and UI
plumbing that already exists in the form the `/changes` poller established.

**Rough cost.** The plumbing is small; the decisions are what cost:

| Piece | Effort | Notes |
|---|---|---|
| In-memory ring buffer + counter | small | mirrors `SessionStore`: module-level, `threading.Lock`, bounded, lost on restart |
| `GET /system-messages` + `@requires` | small | one endpoint, marked and audited like any other |
| Emit at the failure sites | small | free — §9.1's `record_outcome` is already the single choke point |
| UI drawer | medium | new component; polling already solved |
| **Who may see which message** | **the real cost** | see below |
| Persistence / retention | deferrable | in-memory matches sessions and `/changes`; say so rather than implying durability |

**The audience question is the expensive part, and it is a direct consequence of
§1's decision.** A denied or failed annotation has two distinct audiences with
different needs: the **uploader**, who should know their content was not scanned,
and the **operator**, who should know the policy is misconfigured. But the work
ran as the *owner* tenant, not the uploader's — so a naive "show me messages for
my tenant" filter shows the uploader nothing, since none of those messages are
theirs. Resolving that means either recording both the owner tenant and the
triggering tenant on each message (the triggering tenant is available at emit
time even though the work does not run as it), or scoping the feed to admins only
and accepting that uploaders learn from the object label in §9.1.

**Recommendation: sequence them.** §9.1 alone closes the silent-failure hole,
costs almost nothing, and puts the outcome on the object where it is most
useful. Ship it with step 5. Then build §9.2 as a follow-up, with the audience
decision made deliberately rather than implied by whatever filter is easiest —
starting admin-only is a defensible first cut, since an operator misconfiguration
is the failure this design most plausibly produces.

---

## 10. Rollout

Each step is independently shippable and testable.

1. **Walker fix (§6.1) + `@requires` on all 31 bundled plugin routes (§6.2).**
   Satisfies P2 and P7; turns the 500 into correct allow/deny, which is to say it
   makes the *existing* single PEP work for plugin routes. No identity, no new
   config. **Changes boot behavior in `disabled` mode too** (§2.5) — this is the
   one step that does. Land together.
2. **Fail-safe mapper.** An `UnmarkedRouteError` at request time becomes a **403
   with an audit line**, never a 500. Step 1 makes it unreachable; this makes the
   design fail-safe by construction rather than by inventory.
3. **Ambient subject (§2.4 items 1–2, §4.1–4.2).** `CURRENT_SUBJECT` plus the PEP
   setting it. Identity only — no PDP call on the plugin path yet, so no behavior
   change for working deployments. Satisfies P3.
4. **Owner tenant (§5) + event-path override (§4.3).** `owners` map recorded by
   `PATCH /plugins/{name}`, lazy resolution, `plugin-agent` role and `plugin-user`
   virtual subject, and `_run_handler` setting the owning plugin's subject.
   Satisfies P1. **Moved ahead of `_admit`:** once triggers run as the owner
   tenant, an unassigned owner makes every auto-trigger fail, so the owner
   mechanism has to exist before enforcement turns on.
5. **`StoreAPI._admit` (§2.4 item 4)** plus `record_outcome` (§9.1).
   Enforcement point 2: P5's failure, the PDP call, and the outcome write. The
   only step that changes behavior for deployments working today (§8), so it wants
   the `base-user` policy call made before it lands. **Two prerequisites in the
   plugins rather than the framework:** `dast._run_bounded` must carry the context
   into its worker thread (§4.2a) or every live twin call fails P5, and the
   deprecated handler properties must be closed off (§2.4) or the enforcement point
   is bypassable from out-of-tree code. The thread fix is worth landing on its own
   ahead of this step — it is correct either way and costs two lines.
6. **Out-of-process delegation (§4.5).** Widen the MCP mount loop, then wire the
   three runspace plugins to the right URL with an injected token. Repairs the
   agent integration under ACL.

Tests per step:

1–2. A `standalone` plugin call returns 200 or 403 and never 500; startup fails
   when a plugin route carries no marker.
3. A plugin's own API call observes the calling tenant as the ambient subject; an
   allow-listed request observes `None`.
4. A handler triggered by tenant Y's import observes the **owner tenant**, not Y —
   the regression test for §4.3, since ambient inheritance would give Y. Sibling
   handlers owned by different plugins observe their own owners. `POST /auth/login`
   as `plugin-user` returns 401, while a token minted for it authorizes `create`
   on skills and is denied on `/admin/backup`.
5. A triggered handler whose plugin has no owner raises `PluginIdentityError`, and
   the failure is visible on the object rather than only in the log. A `base-user`
   tenant is refused at the door of a route declaring `("tools", "update")`. And —
   the case only `_admit` catches — a tenant holding the door's declared pair but
   not one reached by fan-out is admitted, then denied on the object that exceeds
   its grant, with `record_outcome` marking that object `error`. Plus the §4.2a
   regression: a store call made from a plugin's own worker thread observes the
   ambient subject, not `None` — the `dast` live path is the case that fails without
   `copy_context()`. And `record_outcome`'s own write does not re-enter the handler
   it is recording for (§9.1).
6. The per-subject MCP mount exists and its operation set matches the role.

---

## 11. Open questions

- **Audience of the system-messages feed (§9.2).** Admin-only, or filtered
  per-tenant with both owner and triggering tenant recorded on each message?

- **Granularity for plugin-*management* endpoints only.** §6.2 removed most of
  this: content-touching actions declare content resources, so they discriminate
  naturally. What remains is the genuine plugin-management surface (a plugin's
  `/status`, its config endpoints) which honestly declares `("plugins", <verb>)` —
  so granting `plugins:get` grants it across all 16. Whether anyone needs
  per-plugin management grants is unclear; nothing has asked for it yet.

  If it is ever wanted, one trap is worth knowing before someone tries it in a
  config file: `KNOWN_RESOURCES` is a **closed set**, and `_parse_roles` filters a
  rule's resources against it and then **skips the rule entirely** when nothing
  survives (`if not resources or not verbs: continue`). A role written as
  `resources: [plugins/sast]` is dropped with a warning and grants nothing — it
  fails closed, but silently, and an operator reading the YAML would believe the
  grant exists. Per-plugin resources therefore need plugin slugs registered into
  the known set at load time, not just a naming convention.

- **Token TTL.** Reuse `session_ttl_seconds` (12h in the demo config), or a
  shorter plugin-specific value with refresh-on-demand? The latter is safer and
  costs one accessor.
- **One owner per plugin, or per plugin per tenant?** Sharper now that every
  trigger depends on the owner. If two tenants both enable a plugin, the `owners`
  map as sketched holds one, so the second tenant's imports get annotated under
  the first tenant's identity. Whether triggered work should run once per owner,
  or once as the plugin's single owner, is undetermined and visible to users the
  moment two tenants share a store.
- **`delegated` mode (AC §3, future).** P3 applies unchanged — the ambient subject is
  whatever the PEP resolved. Worth re-reading this design when `delegated` lands,
  since it is the first mode where the tenant is asserted rather than
  authenticated.
