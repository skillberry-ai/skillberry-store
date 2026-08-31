# Changelog

Notable changes to Skillberry Store, newest first. Breaking changes are called out
explicitly: the squash-merge workflow collapses commit messages, so this file is the
only place a migration note survives where deployers will find it.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Breaking

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
