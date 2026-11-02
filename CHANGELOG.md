# Changelog

Notable changes to Skillberry Store, newest first. Breaking changes are called out
explicitly: the squash-merge workflow collapses commit messages, so this file is the
only place a migration note survives where deployers will find it.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added

- **`sbs` is now a native single-file executable, downloadable from any running
  store.** No Python, no `pip`, no separate `restish` install, nothing unpacked at
  startup — one static binary per platform (~32 MB), pre-configured with the URL of
  the store it came from.

  ```bash
  curl -fsSL "https://store.example.com/cli/download?platform=linux-amd64" -o sbs
  chmod +x sbs
  ./sbs list-skills          # works immediately; no `connect`
  ```

  Five platforms are supported — `linux-amd64`, `linux-arm64`, `darwin-amd64`,
  `darwin-arm64`, `windows-amd64` — all cross-compiled from one Linux host.

  **One new endpoint**, unauthenticated in every ACL mode so the download works
  from a browser, `curl`, CI and the CLI itself without a session:

  | Method | Path | Answer |
  | --- | --- | --- |
  | `GET`, `HEAD` | `/cli/download` | The executable. `?platform=<goos>-<goarch>`, `?format=raw\|archive` |

  Which artifact you get is a query argument, so there is one route, one cache key
  shape and one thing to allow-list. The response carries the artifact's identity
  in headers — `X-SBS-SHA256` (hex, comparable straight against `sha256sum`),
  `X-SBS-CLI-Version`, `X-SBS-CLI-Platform` — so a `HEAD` reveals the digest and
  size **without** transferring ~32 MB, and a `GET` carries the digest alongside
  the bytes it describes.

  It is reachable in every mode because it is one of the built-in
  `unauthenticated_paths` defaults, alongside `/health` and the auth endpoints, and
  a config file's own list now **adds to** those defaults instead of replacing
  them. That also fixes an existing footgun: an operator with a custom list had
  silently lost `/health`, `/health/ready`, `/openapi.json` and `/docs`, so liveness
  probes and the API docs demanded a bearer token with nothing in the log to say
  why.

  **New CLI verbs:** `sbs download-cli [--platform] [--output] [--format]` and
  `sbs self-update`, both verifying the published sha256 before writing anything.
  Both work even when the store's spec is unreachable, which is when you need them.

  **New UI:** a **Download CLI** button in the masthead, a card on the home page,
  and a link on the sign-in screen — the last because a user who cannot sign in yet
  is exactly the user who wants the CLI. The expected checksum sits behind a
  "Verify this download" disclosure rather than beside the button.

  **One new setting**, `SBS_CLI_DOWNLOAD` (`on`/`off`), which unregisters the route
  entirely when off. Everything else is derived: the artifact directories are fixed
  beside the CLI source, the URL-injection mechanism follows from the platform and
  from whether a Go toolchain is present, and the concurrency cap is fixed.
  `SBS_PUBLIC_URL` is what gets baked into the artifacts. Client-side: `SBS_URL`
  and `SBS_TOKEN`.

  Preparing a per-URL artifact at server start is **idempotent and off the critical
  path**: it runs as a background task, is stamped on
  `(public_url, cli_commit, engine_version, platform, mechanism)` so an unchanged
  `SBS_PUBLIC_URL` does no work at all, and `/health/ready` deliberately does not
  gate on it. No Go toolchain is required — four of the five platforms are prepared
  by rewriting a fixed-width URL slot inside a CI-built artifact in place, which
  needs no compiler.

  restish is linked into the binaries, so its MIT licence is reproduced in this
  repository's `LICENSE` under *Third-party software notices*, and `sbs --version`
  points at it.

  The binaries are **not code-signed**, so a browser download on macOS is
  quarantined (a `curl` download is not) and Windows SmartScreen may warn. See
  `docs/cli.md`; design in `docs/design/new_cli.md`.

- **`npx skills add` support.** A skill in a running store installs into Claude
  Code, Cursor, Codex and ~70 other agents with one copy-pasted command and no
  prior setup — no `npm install`, no CLI on the PATH, no git credentials, no
  login from the terminal:

  ```bash
  npx skills add https://store.example.com/pub/pdf-forms -y -a claude-code
  ```

  This needs no npm package published and no registration with skills.sh: the
  capability is an open, documented-by-implementation HTTP discovery convention
  (`/.well-known/agent-skills/index.json`) that any web server can serve. The
  store serves it over two read-only `GET` endpoints under a single `/pub/{ref}`
  prefix, in schema v0.2.0 (archive + sha256 digest). Both are excluded from
  `/openapi.json`, so neither appears in the generated Python SDK or as an `sbs`
  command — they exist for npx and for nothing else.

  **Publishing is opt-in, per skill by default.** `npx_publish` in
  `access_control_config.yaml` takes three values, independent of the ACL `mode`:
  `true` (every visible skill), `false` (none — the routes are not registered at
  all), and `selective` (**the default**, where each skill's own `npx_publish`
  flag decides and an unset flag means not published). `true`/`false` ignore the
  per-skill flag, so either publishes or withdraws the whole store in one edit.
  The setting is declared in the access-control config rather than an environment
  variable because it *is* an access-control decision: it is the one setting that
  makes skill **content**, not just metadata, readable without a session.

  A skill's flag is an ordinary manifest field, so `PUT /skills/{id}` and its
  existing `skills:update` permission already govern it — no new endpoint, no new
  role. The UI puts a **Publish this skill with npx** switch in each skill's
  *Install with npx* card, greyed out when the store-wide value is what decides or
  when the caller lacks `skills:update`. It always shows the *effective* state:
  two computed read-only fields, `npx_publish_mode` and `npx_publish_editable`,
  give a client the context to render that, since a raw flag is not interpretable
  on a store set to `true`. The shipped `mode: disabled` config ships
  `true` (nothing is protected there anyway); the `.standalone` demo ships
  `selective`, which is as closed as `false` until an operator opts a skill in.

  **One skill per install URL.** Under `mode: standalone` the path segment is a
  read-only capability token scoped to that one skill, derived by HMAC from a
  durable seed (`SBS_PUBLISH_SEED`, confidential) rather than minted and stored — so it survives a restart, which
  it must, because the URL lives in the user's `skills-lock.json` and is replayed
  by every `npx skills update`. It is re-authorized on every request, so it stops
  working the moment its tenant loses `skills:list`. It is never resolvable as an
  `Authorization: Bearer` value. Under `mode: disabled` the segment is simply the
  skill's slug. Namespace-scoped ("pack") and store-wide URLs are available as
  opt-in capabilities.

  You never have to compose the command: `sbs get-skill <name> --npx-agent
  claude-code`, `sbs get-skill <name> --fields name,_npx_install`, `sbs
  list-skills --fields name,_npx_install`, or the **Install with npx** card on
  each skill's page in the UI, which has an agent picker, a copy button and a link
  to the Node download. Passing `--npx-agent` also *requests* the command, since
  it has no other effect. No preset returns it — `full` included — because it is a
  capability URL. `-a` is always emitted — `-y` without it installs the
  skill into every supported agent's directory, around 75 of them.

  The emitted command carries **no** `DISABLE_TELEMETRY=1` prefix. The CLI does
  report a successful install to `add-skill.vercel.sh` — hostname, skill name and
  the URL you typed, which on a secured store contains the access token; file
  contents are never sent — but a prefix is the wrong lever: it protects one
  invocation and not the `npx skills update` runs that follow, and `VAR=1 command`
  is POSIX syntax that fails outright in PowerShell and `cmd.exe`. The opt-out is
  documented as an exported `DO_NOT_TRACK=1` instead, which covers every run, and
  the UI states it next to the copy button where a reader about to paste a
  credential-bearing URL will see it.

  Set `SBS_PUBLIC_URL`. The install command is absolute, and behind an ingress
  the server cannot derive its own externally-visible URL; without it the command
  is omitted rather than guessed. See `docs/cli.md` and `docs/design/npx.md`.

  Three pre-existing defects were fixed along the way, each of which would have
  made skills silently uninstallable:

  - `SKILL.md` frontmatter was built by string interpolation, so a description
    containing a newline or a `: ` produced YAML no parser accepts, and one
    containing a quote or a `#` parsed to a silently truncated string. It is now
    serialised with `yaml.safe_dump`. **This changes the bytes of
    `GET /skills/{name}/export-anthropic` and of the vNFS tree** wherever a
    description previously needed quoting.
  - The export ZIP was not byte-deterministic (`writestr` stamps each entry with
    `time.localtime()`). There is now one deterministic zip builder, used by both
    the well-known artifact and the existing download. **`export-anthropic`
    output therefore changes too**: entries carry a fixed `1980-01-01` mtime and
    sorted order, in exchange for being reproducible.
  - A description that was absent, empty or `None` reached the file as the
    literal string `"None"`; it now falls back to `Skill: <name>`.

  Neither byte change affects stored data, and no migration is needed.

- **Baked container env vars.** Application environment variables can be given
  fixed values that ship inside the image, by adding them to `container.env` at
  the repo root:

  ```
  SBS_BASE_DIR=/app/store-data
  OBSERVABILITY=false
  ```

  `make docker-build` copies the file to `/app/.env`, where the service already
  picks it up at startup through python-dotenv — so the values are set under a
  plain `docker run <image>`, with no `--env-file` flag, no `make` in the loop,
  and no Dockerfile edit (a Dockerfile `ENV` name cannot be computed, so that
  route costs one line per variable). They are *defaults*: an already-set
  variable wins, so `docker run -e`, `--env-file` and Kubernetes
  `env:`/`envFrom:` still override them, exactly as they would a Dockerfile
  `ENV`. The values are baked into the image, so it must hold **no secrets** —
  pass those at run time. Build against a different file with `make docker-build
  CONTAINER_ENV_FILE=prod.env`; if the file is absent the build skips it. Any
  `EXTRA_COPY_FILES` pair passed on the command line is kept alongside it.
  Readable under the arbitrary UID OpenShift assigns, and — because the loading
  happens inside the application rather than in an entrypoint script — it
  survives a Kubernetes `command:` override. See `docs/config-env-vars.md`.

- **Login information message.** An operator can show a short informational
  message at login — the `/etc/issue.net` tradition — by setting
  `standalone.login_info` in `access_control_config.yaml`:

  ```yaml
  standalone:
    login_info:
      enabled: true
      message: |
        This is a shared evaluation deployment — do not store secrets here.
        Access requests: ops@example.com
  ```

  The same text appears on the UI sign-in screen, before the `sbs login`
  prompt, and on `GET /auth/whoami`'s 401 body. `enabled` and `message` are
  independent controls, so a message can be committed ahead of being switched
  on; the default is off, and with it off behavior is unchanged. The message is
  served **pre-authentication**, so it must contain no secrets. It is read at
  config load, so changing it needs the same restart that adding a user does,
  and it is not baked into the UI bundle — no `make ui-build` needed after an
  edit. `standalone` mode only: neither `disabled` nor `delegated` has an
  in-store login. See `docs/design/login-info.md`.

- **Rich login banner.** The same message can be presented as a banner nobody
  can miss, by adding `format: rich` and an optional `style:` block:

  ```yaml
  standalone:
    login_info:
      enabled: true
      format: rich
      style:
        gradient: ["#1b1141", "#4c1d72", "#0d1b3e"]
        border_color: "#ffd166"
        glow: "#ffd166"
        icon: rocket
        align: center
        animate: [pulse-border, shimmer]
      message: |
        # Store [LIVE DEMO]{bg=#ffd166 color=navy pill bold caps}
        ## [**Visit us** and *drop us a star!*]{color=#ffe9a8}
        [github.com/x/y](https://github.com/x/y){bold color=#8ee6ff}
  ```

  The markup is Markdown-flavoured — `**bold**`, `*italic*`, `` `code` ``,
  `~~strike~~`, `==mark==`, headings, bullets, quotes, rules, `[text](url)`
  links, `![alt](src)` images, `:rocket:` icons, bare-URL autolinking — plus a
  `[text]{color=… size=xl bold pill}` attribute span for per-span colour, size
  and badges, and `style:` for the banner's ground, frame, glow, icon, image and
  opt-in motion (all of which stops under `prefers-reduced-motion`).

  **`format` defaults to `plain`, so no existing config changes behavior.**

  **`sbs login` and `GET /auth/whoami` are unchanged and still plain.** A rich
  message degrades back to text with the markup resolved away, at the same
  1024-character cap as before, so a terminal never sees markup and never sees
  an escape sequence — and no SDK regeneration is needed. The rich message
  itself is capped at 8192 characters / 40 lines.

  Every colour, size, URL scheme, attribute and animation name is matched
  against an allow-list at config load and again in the browser; anything else
  is warned about and dropped with the surrounding text kept, and nothing in the
  block can fail a server boot. The message is parsed server-side into a
  validated tree and rendered as React elements, so no operator text reaches an
  HTML parser: `javascript:`, `data:text/html` and `image/svg+xml` are rejected,
  and markup in the message stays visible text.

  A **UI rebuild is required once** to ship the renderer (`make ui-build`);
  editing the config afterwards still needs only a restart. See
  `docs/design/login-banner.md`.

### Breaking

- **The sbs console script is gone from the Python SDK.**
  `pip install skillberry-store-sdk` no longer installs `sbs`. It is now a native
  single-file executable, and there is exactly one implementation of it. The Python
  shim that `make generate-sdk` used to inject into the generated SDK
  (`skillberry_store_sdk/sdk_cli.py`) has been **deleted**.

  If you install the SDK for the CLI, switch to one of:

  ```bash
  pip install skillberry-store-cli            # platform wheel carrying the binary
  pip install 'skillberry-store-sdk[cli]'     # the SDK plus that wheel
  curl -fsSL "https://store.example.com/cli/download?platform=linux-amd64" -o sbs   # from a store
  ```

  Nothing is withdrawn: the last SDK release carrying the shim stays installable,
  so a pinned CI job keeps working and the fix is one line.

  **Why.** The shim delegated with `os.execvp("restish", ...)`, which replaced the
  process — so it never saw restish's output and could not brand any of it. Users
  read `restish sbs list-skills` in help, error messages and hints, and those
  strings are not commands that work when typed. It also required a **separate
  manual `restish` install** on `PATH`, which users hit before reaching the tool
  at all. The native CLI embeds restish as a Go *library*, so the command name,
  root description, config paths and auth handler are configuration rather than
  text to rewrite, and generated operations sit at the root (`sbs list-skills`,
  not `sbs sbs list-skills`).

  **What you gain:** one static binary with no Python and no `pip`; no separate
  REST client to install; a binary downloaded from a store already points at that
  store; and `sbs login` / `sbs list-skills` work on a fresh install with no
  `connect` step. Config moves from `~/.config/restish/restish.json` to
  `~/.config/sbs/sbs.json` — your existing `apis.sbs` entry is copied over once,
  automatically, and the old file is left untouched.

  The generated **SDK itself is unchanged and remains a pure Python library** that
  installs anywhere; it simply stops declaring a console script. Details in
  `docs/cli.md` and `docs/design/new_cli.md`.

  For other assets in the shared `skillberry-common` subtree: shim generation is
  now gated behind `SDK_PY_CLI`, which **defaults to `1`**, so nothing changes for
  them. This asset sets `SDK_PY_CLI := 0` in `.mk/local.mk`.

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

- **`ENABLE_UI` has been removed.** It had already stopped doing anything: the UI is
  served in-process by FastAPI at `/ui`, and `main()` only ever consulted
  `ENABLE_UI_SUBPROCESS`, so setting `ENABLE_UI=false` silently still served the UI.
  There is no supported API-only mode. Remove the variable from your deployment
  configuration; nothing needs to replace it. `ENABLE_UI_SUBPROCESS` is a different,
  still-live switch and is unaffected.

### Changed

- **`GET /health` now reports the boot stage, and `GET /health/ready` answers 503
  instead of 500 while initialising.** The probes were unusable as a deployment
  health check. `/health` returned a constant `{"status": "healthy"}` that said
  nothing about startup progress, and `/health/ready` — the only stage-aware
  answer — signalled "still initialising" with **HTTP 500**, which a platform
  reads as a crash. Pointed at it, Render tore the instance down mid-boot, the
  replacement entered the same window, and the service restart-looped until a
  boot happened to win the race.

  The two answers are now split across the status code and the body rather than
  being squeezed into one status code:

  | Endpoint | Answers | While booting | Point it at |
  | --- | --- | --- | --- |
  | `GET /health` | "is this alive?" | **200** | Render health check path, Kubernetes `livenessProbe`, target groups, `docker HEALTHCHECK` |
  | `GET /health/ready` | "can it serve content yet?" | **503** + `Retry-After` | `readinessProbe`, load-balancer membership, test harnesses |

  `/health` answers 200 for as long as the process can serve HTTP — including
  before the object handlers exist — and carries progress in the payload:

  ```json
  {
    "status": "healthy",
    "stage": "initializing",
    "checks": {"skill": true, "encoder_warmup": false},
    "uptime_seconds": 4.182
  }
  ```

  `stage` is `initializing` or `operational`; `checks` names the individual gate
  that is still open (usually `encoder_warmup`, the ONNX sentence-encoder load),
  so a slow boot can be diagnosed rather than just observed. A client that needs
  semantic search waits for `stage == "operational"` instead of keying off a
  status code that cannot express it.

  Both probes answer in **every** ACL mode (`disabled` and `standalone`) with no
  credentials, and stay reachable even if an operator writes an
  `unauthenticated_paths` list that omits them — the built-in allow-list is a
  floor that config adds to, now asserted over both modes and over every shipped
  YAML including `access_control_config.yaml.demo`.

  **Deployers: set Render's Health Check Path to `/health`, not
  `/health/ready`.** Render restarts an instance after 60 s of consecutive
  health-check failures, which a cold encoder warmup on a shared-CPU free
  instance can exceed — and the restart re-enters the same window. See
  [docs/health-probes.md](docs/health-probes.md) for the Render, Kubernetes and
  Docker settings, and for three non-probe causes of the same restart symptom:
  the service does not read Render's `$PORT` (`SBS_PORT` defaults to 8000), peak
  RSS measures ~414 MB against the free plan's 512 MB cap, and uvicorn binds only
  2.7 s after process start. That last one is why binding early and serving a
  cut-down route table was considered and rejected — the doc records the
  reasoning, including that deferring route registration would move
  `audit_rbac_coverage` behind a server already accepting traffic.

  Payload changes are additive: `/health` still carries `"status": "healthy"` and
  a ready `/health/ready` still carries `"status": "ready"` plus `checks`, so the
  demo script, the CLI-artifacts workflow and the generated SDK are unaffected.
  The only behavioural change is the readiness status code while initialising,
  500 -> 503 — anything asserting specifically on 500 rather than on "not 200"
  needs updating.

- **Anthropic skill import no longer turns every path segment into a tag.**
  Importing a skill tagged each generated tool and snippet with `file:<path>`
  *and* with one bare tag per segment of that same path — so
  `scripts/check_bounding_boxes.py` produced `scripts` and
  `check_bounding_boxes.py` alongside it. Nothing consumed the bare tags (the
  exporter reads the `file:` tag to rebuild the skill layout), but they
  dominated the UI's tag picker: on a 580-snippet store, 239 of 638 distinct
  tags were file names. The file extension (`md`, `py`) is still tagged; the
  path is now recorded only in `file:<path>`.

  Items imported before this change keep their old tags — the store is not
  migrated. Re-import a skill to drop them, or strip any tag that exactly
  matches a segment of the item's own `file:` tag.
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

- **A remote MCP tool that reports an error is now an error.** Executing an `mcp`
  tool used to return `content[0].text` and ignore the result's `isError` flag, so
  a failing remote tool looked successful (`{"return value": "<error text>"}`).
  Now an `isError: true` result is returned as `{"error": "<text>"}`, which
  `POST /tools/{id}/execute` reports as HTTP 500 like any other failed execution.
  Every text content item is joined with newlines instead of keeping only the
  first, and `structuredContent` is returned as `"structured"` when the server
  sends it. **Behavior change:** a client that parsed error text out of a
  successful response must now read the error response instead.

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
