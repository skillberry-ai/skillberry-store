# Changelog

Notable changes to Skillberry Store, newest first. Breaking changes are called out
explicitly: the squash-merge workflow collapses commit messages, so this file is the
only place a migration note survives where deployers will find it.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Breaking

- **Every plugin API route must now declare `@requires(resource, verb)`.** The startup
  RBAC coverage audit could not see plugin routes at all: FastAPI >= 0.137 nests
  `include_router()` routes under a private `_IncludedRouter` instead of flattening them
  into `app.routes`, so the audit's walker missed all of them — and so did the marker
  stamper, which is why every plugin action endpoint returned **500** under
  `mode: standalone`. The walker now descends that nesting, all 31 bundled plugin routes
  carry markers, and a plugin call is decided (200/403/404) instead of aborting.

  This reaches **third-party plugins in every mode, including `mode: disabled`**. An
  unmarked plugin route now:

  - **fails startup** under `mode: standalone` — an unmarked route there is a live
    authorization hole;
  - **logs a warning** under `mode: disabled`, where no PEP is installed and therefore no
    decision is being skipped, so the deployment still boots.

  Unmarked *core* routes keep failing startup in every mode, as before. A route object
  inside a plugin router that is not an `APIRoute` (a websocket, a Starlette `Mount`) is
  reported on the same terms: a `Mount` sits outside the FastAPI dependency chain
  entirely and would answer with no token at all.

  To migrate a plugin, import the decorator from the plugin contract and put it *above*
  the route decorator:

  ```python
  from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType, requires

  @requires("skills", "update")     # what the action does to the store
  @router.post("/scan")
  async def scan(...): ...
  ```

  Declare the resource the action actually touches, not the plugin subsystem — see
  `docs/design/plugin-identity.md` §6.2.

- **Plugin store calls are now authorized, and a plugin with no identity fails.**
  `StoreAPI` was a privileged in-process interface onto the service layer: a plugin's
  calls reached no router, so no authorization decision was ever made on them. Every
  named `StoreAPI` method now consults the same PDP against the ambient tenant. Under
  `mode: standalone` this changes behavior for deployments working today:

  - **Assign an owner tenant** or the seven auto-triggering plugins (`evaluator`,
    `security`, `dedupe`, `doc_generator`, `sast`, `provenance`, `kagenti-approver`)
    stop annotating. Trigger-driven work runs as the *owner* tenant, not as whoever
    uploaded. The shipped configs set `plugins.owner_tenant: plugin-user` with a
    `plugin-agent` role; a per-plugin owner is recorded when a tenant enables a plugin
    through `PATCH /plugins/{name}`. With neither, outward calls fail (P5) rather than
    proceeding anonymously — the plugin's status message says so, and the framework
    labels the affected object `<slug>:error`.
  - **`StoreAPI.tools` / `.skills` / `.snippets` now raise** while access control is
    enabled. They returned the raw `ObjectHandler`, reaching `write_dict`, `write_file`
    and the locks without passing admission control. Use the named accessors
    (`get_tool_module()` / `update_tool_module()`, `update_tool()` / `update_skill()` /
    `update_snippet()`); each is authorized. They still work in `mode: disabled`, which
    is how tests inject fakes.
  - **`skillberry_store.standalone.VirtualMcpServer` now requires `tool_source`** while
    access control is enabled. Its default source reaches the `ObjectHandler`
    singletons and the service registry directly — unguarded read and execute over
    every tool in the store, obtained with one import. Pass a source you got through
    `StoreAPI`. The core class keeps its fallback for the store's own managed servers.
  - **`StoreAPI(services)` now requires a config**: `StoreAPI(services, acl_cfg,
    sessions=...)`. Deliberately not defaulted — a construction site that forgot it
    would silently disable enforcement while every test still passed.

  Object-level scope is explicitly **not** part of this: any tenant granted a verb
  holds it over every object of that resource type (§7).

- **`~/.skillberry/plugins.json` gained an `owners` key.** Files written by earlier
  versions load unchanged; the key is added on the next write.

### Fixed

- **A Claude Code agent handed the store's MCP URL can now use it under access
  control.** Two independent things were broken, so fixing either alone left it
  broken: the agent had no credential (the SSE handshake is allow-listed, but every
  re-dispatched tool call goes through the PEP and 401s), and the URL it was given —
  the bare `/control_sse` — is not mounted at all under `standalone`. The Control MCP
  mount loop now covers every subject that needs a surface rather than only
  `standalone.users` entries, so a virtual plugin owner tenant gets one too, and
  `ask-runspace` resolves the mount for whoever is calling and attaches a short-lived
  token minted for that identity. No password, no stored secret: the token is derived
  from identity the store already holds and dies with the process. The UI prefill
  carries the URL only — a bearer token has no business round-tripping through a form.

- **`ENABLE_UI` has been removed.** It had already stopped doing anything: the UI is
  served in-process by FastAPI at `/ui`, and `main()` only ever consulted
  `ENABLE_UI_SUBPROCESS`, so setting `ENABLE_UI=false` silently still served the UI.
  There is no supported API-only mode. Remove the variable from your deployment
  configuration; nothing needs to replace it. `ENABLE_UI_SUBPROCESS` is a different,
  still-live switch and is unaffected.

### Changed

- UI sourcemaps are no longer emitted by default. The bundle is served on the same
  unauthenticated port as the API, so shipping maps published the frontend source to
  anyone who could reach the service. Build with `VITE_SOURCEMAP=true make ui-build`
  when you need them for debugging a deployed build.
- The embedding model's truncation limit is now pinned explicitly to **256 tokens**
  (`SBS_ENCODER_MAX_LENGTH`), matching `SentenceTransformer('all-MiniLM-L6-v2')`.
  fastembed's own default for these weights is 128, so descriptions longer than 128
  tokens had been embedding differently from the vectors already in a faiss index.
  Override only to match an index already built at a different limit.
- The encoder's ONNX weights are cached at a stable path (`SBS_ENCODER_CACHE_DIR`,
  defaulting to `$APP_HOME/.cache/fastembed` in the container) and are pre-seeded into
  the image at build time. `/health/ready` no longer waits on an ~80 MB HuggingFace
  download, and the image starts with no network access at all.
- `fastembed` is now bounded (`>=0.8.0,<0.9`). The model name and the tokenizer path
  the truncation pin uses are not public API, so a minor bump should be a deliberate,
  tested step.
- `ci-push` now also builds and pushes the all-plugins image (see the `:latest-full`
  note below), and `make test` / `make test-e2e` build the UI bundle first so the
  `/ui` routes are actually exercised.

### Fixed

- Plugin-declared endpoint URLs keeping the legacy `/api` prefix are normalised at
  every UI fetch site. Without this, `ask-runspace` dropdowns, the whole `dedupe`
  notification/keep/delete flow and the `skillssh-importer` catalog import returned
  404 once the Vite rewrite proxy was removed.
- `GET /ui/index.html` no longer answers `max-age=31536000, immutable`. Requesting the
  un-hashed entry point by its real name — from a bookmark, a doc link, or an ingress
  rewriting `/ui/` to `/ui/index.html` — permanently pinned a stale SPA bundle that no
  reload could recover.
- `make update-sdk` installs the `[build]` extra it needs, instead of failing with
  `openapi-generator-cli: command not found`.
- The `.stamps/ssh-agent.env` build step no longer fails when no SSH key is present,
  which had aborted every `ci-push` run before `docker-build`.

## 2026-08-25 — Memory Scale Down ([#308](https://github.com/skillberry-ai/skillberry-store/pull/308))

### Breaking

- **The default image no longer bundles any plugins.** `Dockerfile` sets
  `ARG PLUGIN_EXTRAS=` (empty), so `:latest` and `:<version>` are core-only. Every
  bundled plugin's router, CLI and dependencies were previously installed and imported
  in every deployment.

  Deployments that rely on bundled plugins must switch to the all-plugins variant,
  tagged `:latest-full` / `:<version>-full` and built by `make docker-build-full`.
  Note this tag did not actually exist in the registry until the `ci-push` fix listed
  under Unreleased above — if you pinned `:latest-full` earlier and got a pull failure,
  that is why.

  For a subset instead of everything:
  `make docker-build --build-arg PLUGIN_EXTRAS=plugin-creator,plugin-dedupe`. See
  [docs/plugins-installation.md](docs/plugins-installation.md).

### Changed

- Embeddings are produced by `fastembed`/onnxruntime instead of
  `sentence-transformers`/torch, dropping torch, transformers, tokenizers,
  safetensors, huggingface-hub, sympy and mpmath from the runtime dependencies. Both
  paths run the same 384-dim `all-MiniLM-L6-v2` weights and agree to ~1e-7 for short
  text, so existing indices remain valid — but see the truncation-limit note under
  Unreleased for inputs longer than 128 tokens.
- The UI is served in-process by FastAPI at `/ui` instead of by an `npx vite preview`
  subprocess on a port of its own, saving ~50–100 MiB of RSS. Health probes and
  ingress rules pointing at the old UI port must move to `/ui` on the API port
  (`8000` by default).
- Measured effect of the release as a whole: ~70% RSS reduction, 812 MB → 232–239 MB.
