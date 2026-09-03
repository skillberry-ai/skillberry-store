# Login Information Message — Design

Status: **Implemented**
Owner: skillberry-store
Scope: `skillberry-store` — an operator-configurable informational message shown to users at login time in `standalone` access-control mode, across the UI, the CLI, and the REST surface.

Related: [access-control.md](access-control.md) (§5.1 schema, §5.2 validation, §7.2 `standalone` auth, §10.1 CLI, §10.4 UI).

---

## 1. Goals & Non-Goals

### Goals

* Let an operator show a short informational message to users **at the point of login** — a pre-auth banner in the `/etc/issue.net` tradition ("shared eval box, do not store secrets", "access requests → ops@example.com").
* Configure it where the rest of the login behavior is already configured: `access_control_config.yaml`.
* Make **setting** the message and **enabling** its display two independent controls.
* Present the same message, from the same source, at the same point in the flow, on every surface that has a login: the UI login screen and `sbs login`.
* Cost nothing when the feature is off — byte-identical behavior to today.

### Non-Goals

* Not a per-tenant, per-user, or localized message. One string, one deployment.
* Not a post-login banner, MOTD, or in-app notification surface.
* Not rich content. Plain text with line breaks; no HTML, Markdown, or links-as-links.
* Not live-reloadable. The value is read at config load, so changing it needs the same server restart that changing `mode` or adding a user already needs (access-control.md §5.4).
* Not shown after a failed sign-in. The message is a pre-attempt banner on every surface (§2).
* Nothing in `disabled` or `delegated` mode — neither has an in-store login (§4.1, §9).

---

## 2. Behavior

| Surface | What the user sees |
|---|---|
| UI login screen (`/ui/login`) | An inline info alert above the username field, rendered before any sign-in attempt (§6). |
| `sbs login` | The message on stderr, printed before the username prompt (§7). |
| REST — `GET /auth/whoami` 401 | A `login_info` field alongside `detail` (§8). |

Two properties hold across all three:

* **Pre-attempt, never post-failure.** The message appears before any credential is submitted. `POST /auth/login`'s 401 body and every 422 in the service stay byte-identical (§8).
* **One resolved value, one gate, one sanitization pass, three encodings at the edges** (§5). The surfaces cannot disagree, because there is nothing for them to disagree about.

---

## 3. The value is read at runtime, not compiled into the UI bundle

`access_control_config.yaml` is already a UI build input — [`.mk/dev.mk`](../../.mk/dev.mk#L41) declares it as a prerequisite of the `ui-build` stamp (`ACL_CONFIG`) because [`vite.config.ts`](../../src/skillberry_store/ui/vite.config.ts#L13-L33) bakes `mode` from it. The message must nonetheless **not** be baked the same way. Three reasons, the first decisive:

**A container cannot rebuild the bundle.** The runtime image sets [`DEPLOY_ONLY=TRUE`](../../Dockerfile#L142), which [drops `ui-build` from `make run`](../../.mk/process.mk#L6-L8). A baked message would be fixed for the life of the image, taken from whatever config sat in the build context — the repo's default, which ships `mode: disabled` and no message — unless the operator supplies theirs via `EXTRA_COPY_FILES` at `make docker-build` time. But the standalone config carries bcrypt password hashes and is edited in place by `scripts/setup_user.py`, so it is realistically mounted or edited at **runtime**. The server would then read the message while the bundle did not have it: the UI blank, `sbs login` showing the banner. For containerized standalone deployments that is the *default* outcome, not a corner case.

**The same failure mode is already documented in this repo.** [Dockerfile:59-63](../../Dockerfile#L59-L63): `make ui-build` bakes the ACL mode from the YAML, and staging the operator's config only in the runtime stage shipped "a bundle built against the repo's config while the image ran with the operator's — a UI stuck in the wrong auth mode." A stale banner is less harmful than a stale auth mode, but `mode` is a far more static property than a message.

**It would cost a dependency.** `readAclMode()` deliberately regex-scrapes the top-level `mode:` line — "A minimal top-level scan is enough … We don't want a new runtime dep for this." A nested `login_info.message` block scalar cannot be scraped that way; baking would require `js-yaml`.

Serve-time injection (§6) costs ~45 LOC in `server.py` and is correct in every deployment shape, including a config mounted at runtime and one image serving two deployments with different messages.

---

## 4. Configuration

### 4.1 Schema

Two keys under the existing mode-specific `standalone:` block, alongside `session_ttl_seconds` and `users`:

```yaml
mode: standalone

standalone:
  session_ttl_seconds: 43200

  login_info:
    enabled: true
    message: |
      This is a shared evaluation deployment — do not store secrets here.
      Access requests: ops@example.com

  users:
    - username: skillberry
      ...
```

| Key | Type | Default | Effect |
|---|---|---|---|
| `standalone.login_info.enabled` | bool | `false` | Master gate. When false the feature is entirely inert and every surface behaves exactly as today. |
| `standalone.login_info.message` | string | unset | The message text. UTF-8; line breaks natural via a `\|` block scalar (§4.3). |

`login_info` belongs under `standalone:` because it is a property of the **in-store login flow, which exists in exactly one mode** — the same reason `session_ttl_seconds` and `users` live there. This holds across all three modes by construction:

* **`disabled`** — no credentials are ever collected; there is no login to annotate.
* **`standalone`** — the only mode with an in-store login screen and an in-store credential prompt. This block's home.
* **`delegated`** — authentication happens in the fronting gateway, never in the store. access-control.md §10.4 states it outright: the UI "is expected to run behind the same trusted gateway that authenticates other traffic … **No login screen in-store**", and §10.1 says the CLI likewise receives the tenant via the trusted-header pattern and "never invents it". A store-rendered banner has nowhere to appear, and a message shown *at login* would have to come from whatever system owns that login — the gateway.

No mode therefore wants this key at the top level.

**The gate defaults false.** The two controls are independent: the file is version-controlled and shared across deployments, so the presence of text must not imply display. A message committed ahead of being switched on is inert.

### 4.2 Validation — warn and drop, never fail closed

`load_config()` **hard-fails** on a broken config in `standalone` mode (access-control.md §5.2, fail-closed). A banner must never be able to stop the server from booting, so `login_info` follows the other convention in that same section — the one used for unknown resource/verb tokens: log and drop the value.

| Condition | Behavior |
|---|---|
| `login_info` absent | `None`. Silent — the normal state. |
| `login_info` is not a mapping | Warning, treated as absent. |
| `enabled: true`, `message` absent / empty / whitespace-only / empty after sanitization | `None` + **warning**: an operator who explicitly opted in and gets nothing needs to be told. |
| `enabled` absent or false, `message` present | `None`, **debug** only. The steady state for a staged message; it must not be noisy. |
| `message` is not a string (list, mapping, number) | Warning, treated as absent. YAML will happily parse `message: [a, b]`. |
| `enabled` is not a bool (e.g. the string `"true"`) | Coerced with the truthy set this repo already uses for config booleans (`true`/`1`/`yes`, case-insensitive); anything else is false, with a warning naming the key. YAML parses bare `true`/`false` as bools, so this only catches quoted values. |

### 4.3 Line breaks

Native, via a YAML block scalar:

```yaml
    message: |
      First line.
      Second line.
```

`|` preserves newlines, `>` folds them, and a backslash carries no special meaning inside a block scalar — so there is no escape syntax for an operator to get wrong and no character that cannot be expressed.

`\r\n` normalization is still required: a file edited on Windows can carry CRLF (§5 step 3).

### 4.4 When the value is read

At config load, in `load_config()` — the same moment `mode`, `session_ttl_seconds`, and `users` are read. There is no live reload in step 1 (access-control.md §5.4: `SIGHUP` is a nice-to-have, `POST /admin/rbac/reload` is future work), so changing the message needs a server restart, exactly like adding a user. This is what lets §6 render the injected HTML once at startup and cache it rather than rebuilding it per request.

---

## 5. Resolution and sanitization — the single point of truth

All three surfaces read one already-sanitized value. Nothing downstream re-parses, re-decodes, or re-gates.

**Home:** `AccessControlConfig` grows one field:

```python
@dataclass
class AccessControlConfig:
    ...
    login_info: Optional[str] = None   # canonical, sanitized; None == show nothing
```

`None` is the only "off" state. The gate, an absent or malformed message, and any mode other than `standalone` (§9) all collapse into it, so no surface needs to know *why* there is nothing to show. This is the invariant that makes the surfaces consistent by construction: **a per-surface gate check is a bug.**

**Resolver:** a new `_parse_login_info(raw: Any, cfg_path: str, mode: str) -> Optional[str]` in [`access_control/config.py`](../../src/skillberry_store/access_control/config.py), called from `load_config()` alongside `_parse_users`, taking `standalone.get("login_info")`. Steps, in this order:

1. If `mode != "standalone"` → `None` (§9).
2. Apply the §4.2 validation table; on any drop condition → `None` with the stated log level.
3. **Normalize** line endings: `\r\n` → `\n`, bare `\r` → `\n`.
4. **Strip control characters**, allow-listing only `\n`: remove C0 (`U+0000`–`U+001F`) and C1 (`U+007F`–`U+009F`) apart from it. Tabs are stripped like any other control character — they do nothing in HTML (collapsed under `pre-line`) and nothing a space cannot do in a terminal, so allowing them would widen the allow-list for no gain.
5. **Cap**: 1024 characters and 10 lines. On truncation, log a warning naming which limit was hit.
6. Strip leading/trailing whitespace. If the result is empty → `None` + the §4.2 warning.

Step 4 is load-bearing. The CLI prints this string straight to a TTY, so a message containing `ESC[` sequences could reposition the cursor or recolor the terminal — config text echoed to a terminal is the classic case for this. Supporting line breaks means the sanitizer must *allow-list* which control characters survive rather than passing through whatever was configured. Step 5 bounds the other practical risk: a block scalar makes a 40-line message easy to write, and an unbounded message would push the login form out of the viewport.

**Encoding happens at the edges, never at the source.** The operator writes plain text; nobody writes escapes:

| Surface | Encoding applied |
|---|---|
| UI (`<meta content>`) | `html.escape(value, quote=True)` at HTML render time (§6) |
| REST (`whoami` 401 body) | JSON string escaping, by `json.dumps` (§8) |
| CLI (stderr) | none — the canonical value is already terminal-safe after step 4 (§7) |

---

## 6. UI

### 6.1 Serve-time injection into `index.html`

The server already serves the SPA entry point itself, with a no-cache directive, in [`_ui_spa_fallback`](../../src/skillberry_store/fast_api/server.py#L413-L442). When `cfg.login_info` is set, it injects one tag before `</head>`:

```html
<meta name="sbs-login-info" content="Shared eval box: don&#x27;t store secrets. Access &amp; support: ops@example.com">
```

Mechanics:

* **Rendered once, at startup**, inside `SBS.__init__` where `acl_cfg` is already in scope (it is loaded at [the top of the constructor](../../src/skillberry_store/fast_api/server.py#L148) and the `/ui` routes are registered in the same function). The injected bytes are held in a closure variable. The value cannot change without a restart (§4.4), so there is no per-request work.
* **Both paths that serve HTML must serve the injected copy.** `_ui_spa_fallback` returns `index.html` from two branches — the on-disk hit for a literal `GET /ui/index.html`, and the SPA fallback for `/ui/login`. Injecting in only one would show the banner on `/ui/login` and not on `/ui/index.html`. The `asset.suffix == ".html"` test that already selects the cache directive is the right hook for both.
* **`<meta content>`, never an inline `<script>`.** An attribute value is inert; escaped operator text cannot execute. A `window.__SBS_LOGIN_INFO__ = "..."` script tag would put operator text in a JavaScript parsing context, which is a strictly worse position to defend.
* **Injection point** is `</head>`, matched case-insensitively on the first occurrence. The bundle's [`index.html`](../../src/skillberry_store/ui/dist/index.html) is Vite-generated and always has one. If it is somehow absent, log a warning and serve the file unmodified — the banner is not worth failing a page load over.
* **When `login_info` is `None`, the route is untouched** — the same `FileResponse` as today, with its ETag, `Last-Modified`, and Range support intact. The feature is strictly additive (§11).

### 6.2 HEAD, caching, and Range — the three costs of not using `FileResponse`

Serving generated bytes instead of a file has three consequences, all verified against the installed Starlette:

* **HEAD must be handled explicitly.** `FileResponse` suppresses the body for HEAD via `send_header_only` ([`starlette/responses.py:343-344`](../../.venv/lib/python3.11/site-packages/starlette/responses.py#L343-L344)); a plain `Response` does not — it always sends the body. Since the `/ui/{path:path}` route serves GET *and* HEAD, a naive switch would return a body for HEAD. The fix relies on `init_headers` skipping its own `content-length` when the caller supplies one (`populate_content_length = b"content-length" not in keys`): for HEAD, return an empty body with an explicit `Content-Length` equal to the GET body's length, so HEAD reports the truth without sending it. [`test_index_html_by_name_is_served_for_head_too`](../../src/skillberry_store/tests/fast_api/test_ui_serving.py#L80) already covers this route and must keep passing with the feature on.
* **No ETag / `Last-Modified` on the entry point** when injection is active. `index.html` is already served `no-cache, must-revalidate`, so this costs a conditional-request 304 and nothing else. (Starlette's `FileResponse` does not implement `If-None-Match` either, so this is smaller than it sounds.)
* **No Range support on `index.html`.** No client byte-ranges an HTML entry point, and [the existing Range test](../../src/skillberry_store/tests/fast_api/test_ui_serving.py#L154) covers a hashed asset, which still goes through `FileResponse` untouched.

`Cache-Control` stays exactly `no-cache, must-revalidate` — unchanged, and load-bearing: the point of that directive is that a rebuild, or a restart with a new message, reaches the user.

### 6.3 `LoginPage`

[`LoginPage.tsx`](../../src/skillberry_store/ui/src/pages/LoginPage.tsx) reads the tag once, in a `useState` initializer (the DOM value is fixed for the page's lifetime):

```tsx
const [loginInfo] = useState<string | null>(() =>
  document.querySelector('meta[name="sbs-login-info"]')?.getAttribute('content') || null
);
```

Rendered as the first `StackItem` in the existing form stack, above the error alert:

```tsx
{loginInfo && (
  <StackItem>
    <Alert
      variant="info"
      isInline
      title={
        <span style={{ whiteSpace: 'pre-line', fontWeight: 'normal' }}>{loginInfo}</span>
      }
    />
  </StackItem>
)}
```

Three details that matter:

* **The message is rendered verbatim — no heading, no label, no splitting.** Nothing is added that the operator did not write; a message that wants to open with "Notice:" says so in the message. PatternFly's `Alert` requires a `title`, so the whole message goes there as a node rather than as children, and `fontWeight: 'normal'` undoes the heading weight `title` would otherwise apply. There is no separate body.
* **`white-space: pre-line`** is what makes §4.3's line breaks render. Without it HTML collapses them and the CLI would show three lines where the UI showed one run-on paragraph.
* **The `Alert` contributes styling only** — the inline band and the info icon. It adds no text. If even that is unwanted, the same span in a plain `<div>` is a drop-in replacement; the escaping and `pre-line` rules are unchanged either way.

React escapes text content, so the value renders as text under all circumstances; the `html.escape` in §5 protects the *attribute*, and the browser un-escapes it on parse, so both surfaces show the same characters.

### 6.4 Limitation: `make ui-dev` does not show the banner

In dev, Vite serves [its own `index.html`](../../src/skillberry_store/ui/index.html) and only proxies non-`/ui` paths, so the serve-time injection never runs.

This is accepted rather than closed. A `transformIndexHtml` hook in `vite.config.ts` could inject the tag, but with the message in a nested block scalar it cannot regex-scrape the value the way `readAclMode()` does — it would need `js-yaml` in `devDependencies`, plus a second implementation of a security-relevant sanitizer, to render a banner in a hot-reload session.

Documented behavior: `make ui-dev` never shows the login message; verifying its rendering means `make ui-build && make run`. The UI unit tests (§12.4) cover the rendering directly, so this is not a coverage gap.

---

## 7. CLI

[`_do_login`](../../skillberry-common/scripts/sdk_cli.py#L232-L246) already issues exactly one preflight request before prompting, to decide whether prompting is pointless:

```python
effective_url = _registered_base(api_name) or api_url
if _auth_disabled(effective_url):        # GET /auth/whoami
    print(f"Authentication is disabled on {effective_url}; no login required.", ...)
    return 2
```

[`_auth_disabled`](../../skillberry-common/scripts/sdk_cli.py#L205-L230) reads the body on the 503 branch and **returns early on 401 without reading it**. That discarded body is where the message lives (§8), so the change is to read it:

```python
def _preflight(api_url: str) -> tuple[bool, Optional[str]]:
    """Return (auth_disabled, login_info) from a single GET /auth/whoami.

    Never raises: any network failure yields (False, None) so the caller
    proceeds and surfaces the real error itself.
    """
```

`_do_login` then becomes:

```python
auth_disabled, login_info = _preflight(effective_url)
if auth_disabled:
    ...unchanged...
if login_info:
    print(login_info, file=sys.stderr)
username = input("Username: ").strip()
```

Properties:

* **No new request.** The probe already happens on every `sbs login`; it returns two facts instead of one. Request count is unchanged.
* **Printed once, before the prompt.** Nothing is printed after a failed attempt — that is what makes the CLI match the UI: both show the message before any attempt, neither after one.
* **stderr, not stdout.** Consistent with every other advisory message in this file, and it keeps `sbs login`'s stdout clean for the `Signed in as ...` line.
* **Fail-quiet.** A server that is down, a server without message support, a malformed body — all yield `None`, and `sbs login` behaves exactly as it does today.
* **Correct across `sbs connect`.** The message comes from whichever backend is actually registered, because the probe uses `effective_url`.

`sbs login` takes no arguments — credentials come from `input()` / `getpass()` prompts — so "run without arguments" is the ordinary invocation, and the banner precedes the prompt on every one of them. Empty input still short-circuits locally with `Username and password are required` (`return 2`), by which point the banner has already been printed.

---

## 8. REST surface

**The login contract does not change.** `POST /auth/login` still answers `401 {"detail": "invalid_credentials"}`, byte for byte, and every 422 in the service is untouched. `detail` must stay a plain string: [the UI renders it directly as an alert title](../../src/skillberry_store/ui/src/pages/LoginPage.tsx#L61) and [the CLI string-matches it](../../skillberry-common/scripts/sdk_cli.py#L265-L270), so widening it to an object would break both. Attaching a sibling key to the 422 would additionally mean a `RequestValidationError` handler — a global one — scoped by path.

The message rides **`GET /auth/whoami`'s 401** instead: the request the CLI already makes, and the natural "you are not authenticated, here is context" moment. No new route is added, so no `unauthenticated_paths` entry is needed and no operator with a customized allow-list has to change anything.

```json
{ "detail": "missing_authorization", "login_info": "Shared eval box …" }
```

Applied to both of `whoami`'s 401 branches — `missing_authorization` (no header, the CLI's preflight) and `invalid_or_expired_token` (an expired session, which is exactly when a client wants re-auth context).

**Mechanism: local, not global.** No new exception class and no `app.exception_handler`. The route returns the response directly:

```python
@app.get("/auth/whoami", ...)
async def whoami(request: Request):
    try:
        result = service.whoami(request.headers.get("authorization"))
    except HTTPException as e:
        if e.status_code == 401 and cfg.login_info:
            return JSONResponse(
                {"detail": e.detail, "login_info": cfg.login_info}, status_code=401
            )
        raise
    return WhoAmIResponse(**result)
```

`detail` keeps its type and value; `login_info` is additive and present only when configured. The blast radius is one function. `AuthService.whoami` is unchanged — it still raises, and stays FastAPI-agnostic apart from `HTTPException`, per its existing convention.

An API client learns the message the same way the CLI does: a documented field on a documented response, with the login contract unmoved.

---

## 9. Mode interaction

| Mode | Behavior |
|---|---|
| `disabled` | `login_info` resolves to `None` unconditionally (§5 step 1) — no login screen, no credential prompt, nothing to attach a message to. `GET /auth/whoami` still returns `503 auth_disabled`, and the CLI still prints `Authentication is disabled …` and exits 2. A `login_info` block present in a `disabled` config is debug-logged, not warned: the same file is routinely shared across deployments that differ only in `mode`. |
| `standalone` | The feature is live, per §§6–8. |
| `delegated` | Reserved and rejected at config load (access-control.md §12). No behavior to define, and none will be needed: authentication moves to the fronting gateway and the store renders no login screen (access-control.md §10.4), so there is no in-store moment for the message to attach to. A deployment wanting a pre-auth banner there configures it on the gateway. |

Resolving to `None` outside `standalone` is what lets the UI, CLI, and REST paths carry no mode checks of their own.

---

## 10. Security considerations

* **The message is public by construction.** It is served pre-authentication to anyone who can reach `/ui/` or `GET /auth/whoami`. That is the point of a login banner, and it means **the message must contain no secrets** — stated as a comment beside the key in the shipped config files, not only here. It matters that the message lives in the same file as the bcrypt password hashes: adjacency to secrets must not be mistaken for confidentiality.
* **XSS.** Escaped with `html.escape(quote=True)` into an inert attribute, then rendered as a React text child. Two independent barriers, neither relying on the operator writing safe input.
* **Terminal escape injection.** Neutralized by §5 step 4 before the value reaches `print()`.
* **No header, so no response splitting.** The message never travels in an HTTP header, which is what makes §4.3's line breaks safe; in a header they would be response-splitting territory and constrained to latin-1.
* **Layout / payload bounds.** The §5 step 5 caps keep the login card and the injected HTML small; an operator cannot accidentally ship a megabyte of `<meta>`.
* **Fingerprinting.** An unauthenticated caller can already distinguish `disabled` from `standalone` (503 vs 401 on `whoami`), so exposing the banner on that same response reveals no new deployment fact.

---

## 11. Backward compatibility

* **Off by default.** The shipped configs gain a commented-out `login_info` block, so `login_info` resolves to `None`, `index.html` is served by the same `FileResponse` as today, `whoami` raises as today, and `_preflight` returns `(x, None)`. Behavior is byte-identical; the existing [`test_ui_serving.py`](../../src/skillberry_store/tests/fast_api/test_ui_serving.py) and [`test_access_control.py`](../../src/skillberry_store/tests/fast_api/test_access_control.py) suites are unaffected.
* **Unknown-key tolerance already exists in both directions.** `load_config` reads named keys and ignores the rest, so an older server given a config with `login_info` boots and ignores it — no migration ordering constraint between config and binary.
* **No new route**, so `unauthenticated_paths` is untouched.
* **No OpenAPI change.** No new operation, no changed response model (`whoami`'s 401 is not in the schema), so **no SDK regeneration is required** and no new `restish` subcommand appears.
* **No new environment variable**, so [`docs/config-env-vars.md`](../config-env-vars.md) needs no change. The schema addition goes in access-control.md §5.1, next to the block it extends.
* **No UI rebuild required.** The message is not a build input, so `.stamps/ui-build` does not change and a config edit does not force a bundle rebuild.
* **Old CLI against a new server:** ignores the extra JSON field; prints no banner. **New CLI against an old server:** `login_info` is absent, `_preflight` yields `None`, no banner. Both directions degrade to today's behavior with no error.
* **`CHANGELOG.md`** gets an `Unreleased` entry — a new operator-facing configuration surface is what deployers search that file for, and [`test_changelog.py`](../../src/skillberry_store/tests/test_changelog.py) guards the structure.

---

## 12. Test plan

Layered like access-control.md §14, and mapped onto the suites that already exist.

### 12.1 Unit — `src/skillberry_store/tests/access_control/test_login_info.py` (new)

Parsing, validation, and sanitization against temp YAML files, no HTTP. `tests/access_control/test_config.py` already establishes the write-a-temp-config-and-load-it fixture pattern.

* Gate false / true × message present / absent / whitespace-only → expected `login_info`, and the §4.2 log level in each case (warning on `enabled + empty`, debug on `message without enable`).
* `mode: disabled` with a fully populated `login_info` → `None`.
* Malformed shapes, each a **warning and a boot**, never an exception: `login_info` as a string or list; `message` as a list, mapping, or number; `enabled` as `"yes"` (coerced true) and `"nope"` (false + warning).
* A malformed `login_info` in `standalone` mode does **not** raise `AccessControlConfigError` — the regression test for §4.2's "a banner must never stop the server booting".
* Block scalars: `|` preserves newlines, `>` folds them, and a backslash-`n` in a block scalar stays two literal characters.
* `\r\n` and bare `\r` normalization.
* Control-character stripping: ANSI CSI (`\x1b[31m`), `\x00`, `\x07`, `\t`, a C1 codepoint — all removed; `\n` preserved.
* Caps: a 2000-character message truncates to 1024 with a warning; a 20-line message truncates to 10 with a warning naming the line limit.
* Idempotence: sanitizing an already-sanitized value is a no-op.

### 12.2 Integration — `tests/fast_api/test_ui_serving.py` (extend)

* Feature on: `GET /ui/` **and** `GET /ui/index.html` both carry `<meta name="sbs-login-info">` with the expected content — the two-branch trap from §6.1.
* Feature off: no such tag, and the response is still a `FileResponse` (assert `etag`/`accept-ranges` present, proving the untouched path).
* `Cache-Control` is `no-cache, must-revalidate` in both states.
* Escaping: a message containing `" < > & '` appears escaped in the raw bytes and un-escapes to the original via an HTML parse.
* Line breaks survive into the attribute.
* `HEAD /ui/index.html` with the feature on → 200, **empty body**, `Content-Length` equal to the GET body length.
* A hashed asset still byte-ranges (the existing Range test, re-run with the feature on).
* Missing `</head>`: injection is skipped, a warning is logged, the page still serves 200.

### 12.3 Integration — `tests/fast_api/test_access_control.py` (extend)

* `standalone` + feature on: `GET /auth/whoami` with no header → 401, `detail == "missing_authorization"`, `login_info` present. Same for an expired/unknown token → `invalid_or_expired_token` + `login_info`.
* Feature off: the 401 body has **no** `login_info` key.
* `POST /auth/login` with bad credentials → body is exactly `{"detail": "invalid_credentials"}` with the feature **on**. The regression test for §8's promise.
* `POST /auth/login` with an empty body → the 422 body is unchanged with the feature on; and a second endpoint's 422 is unchanged too, proving no global handler was installed.
* `disabled` mode + a populated `login_info` → `whoami` still 503 `auth_disabled`, no `login_info`.

### 12.4 UI — vitest, alongside the existing component tests

* `LoginPage` renders the info alert when the meta tag is present, with the text intact.
* The rendered alert contains **only** the message — no added heading or label text, so a change that reintroduces one fails here.
* No alert when the tag is absent or its content is empty.
* A message containing `<script>alert(1)</script>` renders as visible text — no element is created.
* Multi-line content: the rendering element carries `white-space: pre-line`.

### 12.5 CLI — `tests/cli/test_sdk_cli_login_info.py` (new infrastructure)

There are no unit tests for [`sdk_cli.py`](../../skillberry-common/scripts/sdk_cli.py) today — it is a generation template with `{{API_NAME}}` / `{{API_URL}}` placeholders, so the fixture substitutes them into a temp file and imports it as a module. Against a stub HTTP server:

* 401 + `login_info` → `_preflight` returns `(False, "<message>")`; the message is printed to **stderr** before the first prompt, and `stdout` is untouched.
* 401 without `login_info` → `(False, None)`, nothing printed.
* 503 `auth_disabled` → `(True, None)`, the existing "no login required" path with exit code 2 is unchanged.
* Connection refused / timeout / non-JSON body → `(False, None)`, no traceback.
* The message is printed exactly once across a full failed-login run.

### 12.6 Config and docs

* All three shipped configs — [`access_control_config.yaml`](../../access_control_config.yaml), [`.disabled`](../../access_control_config.yaml.disabled), [`.standalone`](../../access_control_config.yaml.standalone) — gain a **commented-out** `login_info` block with the "no secrets" note from §10. Commented, not enabled, so §11's byte-identical default holds. The `.standalone` demo config is the natural place for a realistic example.
* access-control.md §5.1 schema gains the two keys; §5.2 gains the warn-and-drop row.
* `CHANGELOG.md` `Unreleased` entry (§11).

---

## 13. Estimated change size

| Area | Files | ~LOC |
|---|---|---|
| YAML parse + validate + sanitize + config field | `access_control/config.py` | ~65 |
| `index.html` injection (render-once, both branches, HEAD) | `fast_api/server.py` | ~45 |
| `whoami` 401 body | `fast_api/auth_api.py` | ~10 |
| UI alert | `ui/src/pages/LoginPage.tsx` | ~15 |
| CLI `_auth_disabled` → `_preflight` | `skillberry-common/scripts/sdk_cli.py` (+ generated copy) | ~30 |
| Tests | 5 files (2 new) | ~320 |
| Config examples + docs | 3 YAMLs, `access-control.md`, `CHANGELOG.md`, this file | ~45 |
| **Total** | | **~530** |

No new dependencies. No new REST route. No OpenAPI or SDK change. No new environment variable.

The weight is in the serve-time injection (§6.1–6.2) and the tests, not in reading the configuration — the resolver is ~10 LOC of shape validation on top of a value `load_config` is already parsing.

