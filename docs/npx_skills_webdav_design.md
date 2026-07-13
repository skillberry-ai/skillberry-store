# Design: Make skillberry-store vNFS/WebDAV URLs installable with `npx skills`

**Status:** Draft for review
**Author:** Design notes (2026-07-07)
**Related:** [conversation_export_npx_skills.md](conversation_export_npx_skills.md), [vnfs_server.py](../src/skillberry_store/modules/vnfs_server.py), [exporter.py](../src/skillberry_store/tools/anthropic/exporter.py)

## 1. Goal

Enable the URL exposed by a Skillberry-store WebDAV vNFS server to be consumed directly by the `skills` CLI:

```bash
npx skills add http://<host>:<port>
```

Today this does not work. `npx skills` supports Git remotes, local paths, direct `SKILL.md` URLs, and the **well-known HTTP provider**; it does **not** crawl a bare WebDAV directory listing. The path with the least friction is to make our HTTP surface look like a **well-known agent-skills endpoint** while remaining a functional WebDAV mount.

## 2. Current state

- [VirtualNfsServer](../src/skillberry_store/modules/vnfs_server.py#L176) creates one server per skill, each on its own port, with two backends: `nfs` (ShenanigaNFS) and `webdav` (wsgidav + cheroot).
- The WebDAV backend uses `FilesystemProvider(export_path, readonly=True)` mounted at `/` and `simple_dc: {"*": True}` (anonymous), on plain HTTP.
- The exported directory tree, produced by [export_skill_to_directory](../src/skillberry_store/tools/anthropic/exporter.py#L335), is:

  ```
  <export_path>/
  └── <skill_name>/
      ├── SKILL.md
      ├── scripts/…
      ├── references/…
      └── …
  ```

- `<skill_name>/SKILL.md` already has the YAML frontmatter (`name`, `description`) the `skills` CLI requires.

The content is already almost right; only the discovery surface is missing.

## 3. Proposal — opt-in well-known HTTP layout on the same port

Add a **well-known agent-skills manifest** and file layout to the WebDAV export so the same HTTP endpoint can serve both:

1. A standard WebDAV mount (unchanged behavior for `davfs2`/`rclone`/etc.).
2. `/.well-known/agent-skills/index.json` plus per-skill files under `/.well-known/agent-skills/<slug>/…` for `npx skills add http://host:port`.

The feature is **opt-in per vNFS**. It is available **only when the vNFS protocol is `webdav`** (see §6.11); creating an NFS vNFS with the flag set is a validation error. The opt-in also gates a **skill-name validation step** because the well-known layout and the `skills` CLI require the skill's slug to match its `SKILL.md` frontmatter `name`. NFS users who need `npx skills` install can still mount the NFS export and point `npx skills add <local-path>` at it — no server-side change is required for that case.

### 3.1 New field: `npx_compat`

Add a boolean field to `VnfsSchema` — for example `npx_compat: bool = False` (name TBD; `install_via_npx` or `well_known_endpoint` are alternatives). Persisted with the vNFS object. Behavior:

- `npx_compat=false` (default): today's behavior — plain WebDAV, no `.well-known/`.
- `npx_compat=true` **and** `protocol="webdav"`: enable the export layout and provider mappings in §3.3.
- `npx_compat=true` **and** `protocol="nfs"`: rejected at create/update time with a clear validation error.
- Toggling the flag on an existing vNFS requires the server to re-export and restart the backend so the tree and mounts match the new setting.

### 3.2 Skill-name validation (shared with Anthropic export)

Skillberry skill names are not guaranteed to be slug-safe. Both `npx skills` and the Anthropic-skill folder convention require the `name` in `SKILL.md` frontmatter to match the enclosing directory name, and to be `[a-z0-9-]+`. Rather than silently rewriting the name (which risks divergence between the store's canonical name and what the consumer sees), the system should **validate** and **refuse** to enable the feature when the name is not slug-safe.

Verified: the current [exporter.py](../src/skillberry_store/tools/anthropic/exporter.py#L62-L64) emits `name: {skill['name']}` verbatim into the frontmatter, so today an Anthropic export of a skill named e.g. `My Skill` produces `name: My Skill`, which is technically invalid per Anthropic conventions and would misbehave in `npx skills` too. This is a latent bug shared with the new feature.

Design:

- Add a shared utility `validate_skill_slug(name) -> bool` (or `raise ValueError`) in `tools/anthropic/exporter.py` (or a nearby common module) that accepts the same character set consumed by `npx skills` / Anthropic conventions: `^[a-z0-9]+(-[a-z0-9]+)*$`, length ≤ 64.
- Apply it at three points:
  1. `VnfsService.create`/`update` when `npx_compat=True` — reject with 400.
  2. Anthropic export endpoints (ZIP and directory export) — reject with 400 by default; optionally accept `?allow_invalid_name=1` for callers who want the current permissive behavior. That preserves the ability to unblock Anthropic ZIP exports that happen to be tolerated by permissive consumers, while making the strict path the default going forward.
  3. UI form validation, mirroring the server rule so users get instant feedback (see §4).
- Do **not** auto-slugify. If the name is invalid, present the user with a preview of the suggested slug (`"my-skill"` for `"My Skill"`) and require them to explicitly rename the skill (or accept the suggestion) before enabling npx-compat / doing the Anthropic export.

### 3.3 Export layout (with `npx_compat=True`)

The on-disk tree becomes:

```
<export_path>/
├── .well-known/
│   ├── agent-skills/
│   │   ├── index.json
│   │   └── <skill-slug>/
│   │       ├── SKILL.md
│   │       ├── scripts/…
│   │       └── …
│   └── skills/                # legacy alias — see below
│       ├── index.json
│       └── <skill-slug>/…
└── <skill-slug>/               # top-level copy for WebDAV mount compatibility
    ├── SKILL.md
    └── …
```

Per user decision on §6.4: **the file bytes are written twice** (or three times if we include the legacy alias) — once at each location — rather than using symlinks or wsgidav multi-mount. This is simpler, avoids the symlink-follow question, and keeps every path a first-class file on disk that both WebDAV and plain-HTTP GET see identically. Duplication cost is bounded (skills are small — kilobytes to low megabytes) and each vNFS is short-lived.

Concretely the exporter builds one file-tree dict and materializes it three times under prefixes:

- `""` (top level, existing WebDAV path)
- `.well-known/agent-skills/`
- `.well-known/skills/` (legacy)

Plus two `index.json` files at `.well-known/agent-skills/index.json` and `.well-known/skills/index.json` (byte-identical).

### 3.4 `index.json` shape

```json
{
  "version": 1,
  "skills": [
    {
      "name": "<skill-slug>",
      "description": "<description from SKILL.md frontmatter>",
      "files": [
        "SKILL.md",
        "scripts/validate.py",
        "references/guide.md",
        "assets/template.md"
      ]
    }
  ]
}
```

The `files` array is built by the same code path that materializes the tree, so what's on disk and what's advertised in `index.json` cannot drift (resolves §6.6). Rules for the builder:

- Enumerate exactly the paths the exporter is about to write under `<skill-slug>/`; do not walk the filesystem after the fact.
- Sort deterministically (stable across restarts) so the manifest is byte-stable when inputs are unchanged.
- Include hidden files (`.foo`) if any exist.
- `description` is read from the SKILL.md frontmatter that this same call is generating (single source of truth — resolves §6.7), matching the pattern already used by the Anthropic exporter.
- Reject the build if the skill's `SKILL.md` frontmatter `name` differs from `<skill-slug>` — belt-and-braces on top of §3.2.

### 3.5 Server changes

`WebDavBackend.start` keeps its single provider mount at `/` (readonly filesystem). No additional wsgidav provider mappings are needed because the well-known files are physically present under `<export_path>/.well-known/…`. This is the direct consequence of the "duplicate on disk" decision in §3.3 and keeps wsgidav configuration untouched.

The only server-side change in `WebDavBackend` is that it now depends on the exporter having written the `.well-known/` tree — i.e., no code change to the backend, but a new precondition. `VirtualNfsServer.start` reads the vNFS's `npx_compat` flag and passes it to `export_skill_to_directory(..., npx_compat=...)` so the exporter chooses which layout to emit.

### 3.6 URL published to the user

`VnfsService.get`/`list_all` gains a new `install_url` field, populated only when `protocol == "webdav"` and `npx_compat == True`:

```
install_url = f"http://{public_host}:{server.port}"
```

Users install with either:

```bash
npx skills add http://<host>:<port>
npx skills add http://<host>:<port>/.well-known/agent-skills/<skill-slug>   # specific skill path
```

No aggregator (per user decision on §6.8) — each vNFS is independent and has its own URL.

## 4. Backwards compatibility

- WebDAV mount behavior at `/` is unchanged for vNFS with `npx_compat=false`; the top-level `<skill-slug>/` copy in §3.3 preserves the same layout when `npx_compat=true`, so existing WebDAV clients keep working.
- NFS backend is entirely unaffected (well-known is HTTP-only, and the flag is rejected for NFS at the schema level — §6.11).
- `VnfsSchema` gains one new optional field (`npx_compat`, default `false`). Persisted objects without the field are read as `false` — no migration required.
- `install_url` is a runtime-derived response field only; it is absent unless `protocol=="webdav"` and `npx_compat==True`.
- The strict skill-name validation is a **behavior change** for Anthropic exports. Guard behind default-strict, with an explicit `allow_invalid_name` escape hatch for one release (§3.2) so users with invalid names are informed rather than silently broken.

## 5. Implementation checklist

### 5.1 Service (Python)

1. **Shared validation** — add `validate_skill_slug(name)` to [exporter.py](../src/skillberry_store/tools/anthropic/exporter.py) (or a new `tools/anthropic/naming.py` if we want a cleaner home). Regex: `^[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 64 chars. Return a `(ok, suggested_slug, reason)` triple so callers can render actionable errors.
2. **Anthropic export change** ([exporter.py](../src/skillberry_store/tools/anthropic/exporter.py)):
   - Call `validate_skill_slug(skill["name"])` at the top of `export_skill_to_anthropic_format` and `export_skill_to_directory`. Raise `ValueError` on failure unless an `allow_invalid_name=True` kwarg is passed.
   - Expose the same knob on the Anthropic export FastAPI route (query param or request body flag).
3. **Well-known layout in exporter** ([exporter.py](../src/skillberry_store/tools/anthropic/exporter.py)):
   - Extend `_build_file_structure(...)` (or add a `_build_file_structure_with_wellknown`) so it accepts `npx_compat: bool`. When true, materialize the tree three times (`""`, `.well-known/agent-skills/`, `.well-known/skills/`) plus two identical `index.json` files.
   - Add `build_wellknown_index(files, skill, slug) -> bytes` that returns the `index.json` payload. The description is read from the SKILL.md frontmatter this same call is generating.
   - Update `export_skill_to_directory(..., npx_compat=False)` to forward the flag.
4. **Schema** ([vnfs_schema.py](../src/skillberry_store/schemas/vnfs_schema.py)):
   - Add `npx_compat: bool = False` with a docstring.
   - Add a Pydantic model validator that raises `ValueError` if `npx_compat and protocol != "webdav"`.
5. **VNFS server** ([vnfs_server.py](../src/skillberry_store/modules/vnfs_server.py)):
   - Thread `npx_compat` through `VirtualNfsServer.__init__` and into `start`/`refresh` so it is forwarded to `export_skill_to_directory`.
   - Store `npx_compat` as an attribute; include it in `to_dict()`.
6. **VNFS manager** ([vnfs_server_manager.py](../src/skillberry_store/modules/vnfs_server_manager.py)):
   - Pass `npx_compat` through both `add_server` and `load_servers` (read from persisted dict, default `False`).
7. **Service** ([vnfs_service.py](../src/skillberry_store/services/vnfs_service.py)):
   - Update `_to_ns` to pass `npx_compat`.
   - In `create`/`update`, if `npx_compat` is set, run `validate_skill_slug` on the referenced skill's name and 400 on failure. Also 400 if `protocol != "webdav"` (defense in depth — schema already blocks this).
   - In `get`/`list_all`, populate `install_url` when both preconditions hold; the host portion is taken from a new config value (see §5.2) with a fallback to the request's `Host` header.
8. **Config** — add a `VNFS_PUBLIC_HOST` env var (documented in [config-env-vars.md](config-env-vars.md)) that overrides autodetection when the store runs behind a reverse proxy or in a container.

### 5.2 UI (React)

1. **vNFS create/edit form** ([VNFSServersPage.tsx](../src/skillberry_store/ui/src/pages/VNFSServersPage.tsx) and its form component):
   - Add a **protocol** radio group (`webdav` / `nfs`) that already exists in the API; wire the form's `protocol` field to it.
   - Add an **"Install with `npx skills`"** checkbox next to the protocol selection. Show/enable it **only** when `protocol=="webdav"` (per §6.11). When protocol switches to `nfs`, force the checkbox off and hide it.
   - When the checkbox is checked, run client-side slug validation on the linked skill's name. If invalid, disable the submit button and render an inline error with the suggested slug (mirroring server rule from §3.2).
2. **vNFS detail page** ([VNFSServerDetailPage.tsx](../src/skillberry_store/ui/src/pages/VNFSServerDetailPage.tsx)):
   - Show a new **"Install command"** section, only when the API response includes `install_url` (i.e., WebDAV + `npx_compat`). Render:

     ```
     npx skills add <install_url>
     ```

     with a copy-to-clipboard button. Include a short helper line explaining what `npx skills add` does and linking to the well-known endpoint (`<install_url>/.well-known/agent-skills/index.json`).
   - Add a small "Well-known" badge on the card if `npx_compat` is enabled, so it's visible in the list view.
3. **Anthropic export dialog** (wherever the store exposes the "Export as Anthropic skill" button):
   - Before firing the export, run the same client-side slug validation on the skill's name. On failure, block export with a modal that offers a "Rename skill to `<suggested-slug>`" quick action (which routes through the existing skill-rename flow) or an "Export anyway" secondary button that sends `allow_invalid_name=true`.
4. **Copy affordances** — reuse the existing copy-button component used for other endpoint URLs in the store; do not introduce a new one.

### 5.3 Tests

1. Extend [test_vnfs_api.py](../src/skillberry_store/tests/e2e/test_vnfs_api.py) with a fixture that starts a WebDAV vNFS with `npx_compat=True`, then:
   - `GET /.well-known/agent-skills/index.json` returns valid JSON matching the schema.
   - Every path in `files` is fetchable at `/.well-known/agent-skills/<slug>/<file>` AND at the top-level `/<slug>/<file>` (duplicate-on-disk decision).
   - `.well-known/skills/index.json` is byte-identical to the primary manifest.
   - Creating a vNFS with `npx_compat=True, protocol="nfs"` returns 400.
   - Creating a vNFS with `npx_compat=True` referencing a skill whose name is `"My Skill"` returns 400 with the suggested slug in the error body.
2. Add a unit test in the exporter suite that:
   - `validate_skill_slug` accepts/rejects the expected cases.
   - The Anthropic export path rejects invalid names by default and accepts them with `allow_invalid_name=True`.
3. Optional e2e: run `npx skills add http://127.0.0.1:<port>` from a scratch dir and assert `SKILL.md` lands under `.claude/skills/<slug>/`. Skip on CI if the runner has no network egress for `npm`.

### 5.4 Docs

- Update [cli.md](cli.md) and the vNFS section of the README with `npx skills add` usage and the `npx_compat` flag.
- Add a note under Anthropic-export docs about the new name-validation behavior and the `allow_invalid_name` escape hatch.

## 6. Issues raised and decisions

Each item lists the original concern and the resolution agreed with the user (2026-07-07).

### 6.1 HTTPS expectations
**Concern:** `.well-known/` URIs are typically HTTPS; our WebDAV backend is plain HTTP.
**Decision:** `npx skills` accepts `http://`. **Not a blocker.** No TLS termination required for this feature. Deployments that want HTTPS can front the store with a reverse proxy independently.

### 6.2 Non-standard ports in well-known URLs
**Concern:** Well-known URIs usually run on 443; each vNFS is on a per-skill port.
**Decision:** `npx skills` accepts custom ports. **Not a blocker.**

### 6.3 wsgidav responses to bare `GET`
**Concern:** Directory-index HTML on `GET /`; `DAV:` headers on `OPTIONS`.
**Decision:** **Ignore for now.** The user will test end-to-end; if the CLI misbehaves, we will design a workaround (candidates: a tiny plain-static backend variant, a shim that intercepts specific paths, or an HTML landing page). No code change gated on this.

### 6.4 Symlinks vs hard links vs multi-mount
**Concern:** Deduplicating the top-level and well-known copies of the skill files.
**Decision:** **Duplicate the files on disk** — write each file twice (three times counting the legacy alias). Skills are small and vNFS instances are short-lived; the simplicity is worth the extra kilobytes and it sidesteps the wsgidav/symlink questions in §6.3. Design updated in §3.3.

### 6.5 Skill name normalization
**Concern:** Skillberry names aren't guaranteed to be slug-safe; `npx skills` and Anthropic conventions require `[a-z0-9-]+`.
**Decision:** **Make npx compatibility an explicit choice** (both API and UI) — new `npx_compat` flag on the vNFS (§3.1). When set, validate the skill's name against the slug regex and refuse creation on failure. **Verified** that the current Anthropic exporter emits the name verbatim (see [exporter.py](../src/skillberry_store/tools/anthropic/exporter.py#L62-L64)), so the same validation must apply to Anthropic export too — implemented via the shared `validate_skill_slug` in §3.2 and §5.1.

### 6.6 File enumeration must match reality
**Concern:** The `files` array in `index.json` must exactly match what's fetchable.
**Decision:** Resolved in the exporter design. The same code path both materializes the tree and builds the manifest, so the two cannot drift (§3.4).

### 6.7 Description field source
**Concern:** Which description ends up in `index.json` — Skillberry's free-text or the SKILL.md frontmatter?
**Decision:** Same rule the Anthropic exporter already follows — read from the generated SKILL.md frontmatter, which is itself sourced from the skill dict's `description`. Single source of truth; nothing to change beyond wiring it into `build_wellknown_index`.

### 6.8 Aggregator on the main FastAPI app
**Concern:** Users installing several skills need one URL per skill.
**Decision:** **No aggregator for now.** Each skill has its own independent URL. Revisit if usage patterns show real friction.

### 6.9 Authentication
**Concern:** Anonymous exposure via `simple_dc: {"*": True}`.
**Decision:** **No authentication for now.** Same posture as the existing WebDAV backend. Revisit when we support private skills.

### 6.10 CLI version drift
**Concern:** Upstream `WellKnownProvider` schema may evolve (`installName`, checksums, etc.).
**Decision:** **Not needed now.** Track upstream only when we hit a breaking change.

### 6.11 NFS/WebDAV protocol switch
**Concern:** `npx_compat` is HTTP-only; NFS servers can't participate.
**Decision:** **Restrict the flag to WebDAV.** The UI shows the "Install with `npx skills`" checkbox only when the user has selected WebDAV; the API rejects `npx_compat=True` with `protocol="nfs"` at the schema layer (§3.1, §5.1, §5.2). Users on NFS who want npx install can mount the NFS export and use the local-path form (`npx skills add /mnt/…`) — no server-side work needed.

### 6.12 Reverse-proxy path prefixes
**Concern:** A proxy mounted at `/store/` would break `/.well-known/`.
**Decision:** **Not handled for now.** Deployments that need this can proxy the vNFS ports directly at a host root or run the store on its own hostname. Document if the situation actually arises.
