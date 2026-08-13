"""CLI module for sbs SDK using restish.

Thin shim over the `restish` CLI (https://rest.sh). This file is the
generation template; ``make generate-sdk`` substitutes ``sbs``
(lowercase acronym, e.g. ``sbs``) and ``http://0.0.0.0:8000`` (compiled-in base
URL) before it lands in the generated SDK. See
docs/design/access-control.md §10.1 for the CLI/auth story.
"""
import getpass
import json
import os
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn, Optional


API_NAME = "sbs"
API_URL = "http://0.0.0.0:8000"

# Env override for CI / scripting. Named uppercase to match the design
# doc (`SBS_TOKEN`, `GH_TOKEN`-style). When set, restish reads it via a
# durable ``env-token`` profile so the token never appears on argv.
API_TOKEN_ENV = f"{API_NAME.upper()}_TOKEN"
ENV_PROFILE = "env-token"


def check_restish_installed() -> bool:
    """Check if restish is installed and available on PATH."""
    try:
        subprocess.run(
            ["restish", "--version"],
            capture_output=True,
            check=True,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def abort_with_install_instructions() -> NoReturn:
    """Print installation instructions and exit."""
    print("Error: 'restish' CLI is not installed or not available on PATH.", file=sys.stderr)
    print("\nTo install restish, you have two options:", file=sys.stderr)
    print("\n1. Using Go (if you have Go installed):", file=sys.stderr)
    print("   go install github.com/rest-sh/restish@latest", file=sys.stderr)
    print("\n2. Download pre-built binaries from GitHub:", file=sys.stderr)
    print("   https://github.com/rest-sh/restish/releases", file=sys.stderr)
    print("\nAfter installation, ensure restish is in your PATH.", file=sys.stderr)
    sys.exit(1)


# Strip JSONC comments outside of strings. Restish writes `//` line
# comments (migration header) into ``restish.json`` which trip json.load.
_JSONC_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|/\*.*?\*/|//[^\n]*', re.DOTALL)


def _strip_jsonc(text: str) -> str:
    return _JSONC_TOKEN.sub(lambda m: m.group(0) if m.group(0).startswith('"') else "", text)


def _config_path() -> Path:
    """Path to the restish v2 config file (``restish config path``)."""
    try:
        proc = subprocess.run(
            ["restish", "config", "path"],
            capture_output=True,
            text=True,
            check=True,
        )
        candidate = proc.stdout.strip()
        if candidate:
            return Path(candidate)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return Path.home() / ".config" / "restish" / "restish.json"


def _load_config() -> tuple[dict, Path]:
    """Return (config, path). Missing/unreadable file => empty dict."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return {}, path
    try:
        with open(path, "r") as fh:
            return json.loads(_strip_jsonc(fh.read())) or {}, path
    except (json.JSONDecodeError, OSError):
        return {}, path


def _write_config(config: dict, path: Path) -> None:
    with open(path, "w") as fh:
        json.dump(config, fh, indent=2)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass


def _registered_base(api_name: str) -> Optional[str]:
    """Return the base_url currently registered for ``api_name``, or None.

    Uses ``restish api list -o json`` so we consume restish's own
    parser rather than reimplementing JSONC handling here.
    """
    try:
        proc = subprocess.run(
            ["restish", "api", "list", "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        entries = json.loads(proc.stdout) or []
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None
    for entry in entries:
        if entry.get("name") == api_name:
            return entry.get("base_url")
    return None


def _restish_connect(api_name: str, api_url: str, replace: bool = False) -> None:
    """Register/refresh the API with restish. Errors surface to stderr and exit."""
    cmd = [
        "restish", "api", "connect", api_name, api_url,
        "--spec", f"{api_url.rstrip('/')}/openapi.json",
        "--yes",
    ]
    if replace:
        cmd.append("--replace")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip() or "unknown error"
        print(f"Failed to connect to {api_url}: {msg}", file=sys.stderr)
        sys.exit(1)


def _ensure_env_profile(api_name: str) -> None:
    """Idempotently create the env-token profile.

    Only literal text ``env:<VAR>`` is passed on argv here — no secrets.
    Restish resolves ``env:<VAR>`` at request time.
    """
    subprocess.run(
        [
            "restish", "api", "set", api_name,
            f"profiles.{ENV_PROFILE}.auth: "
            f"{{type: bearer, params: {{token: env:{API_TOKEN_ENV}}}}}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _ensure_connected(api_name: str, default_url: str) -> str:
    """Ensure the API is registered. Preserve any user-set base_url override.

    Returns the effective base_url in use.
    """
    existing = _registered_base(api_name)
    if existing:
        target_url = existing
    else:
        target_url = default_url
        _restish_connect(api_name, target_url, replace=False)
    _ensure_env_profile(api_name)
    return target_url


def _store_bearer(api_name: str, token: str) -> None:
    """Persist a bearer token in restish's v2 config, off argv.

    Writes ``apis.<name>.profiles.default.auth = {type: bearer, params: {token: <t>}}``
    directly — restish's own ``api set`` would echo the token on argv.
    """
    config, path = _load_config()
    apis = config.setdefault("apis", {})
    entry = apis.setdefault(api_name, {})
    profiles = entry.setdefault("profiles", {})
    default = profiles.setdefault("default", {})
    default["auth"] = {"type": "bearer", "params": {"token": token}}
    _write_config(config, path)


def _auth_disabled(api_url: str) -> bool:
    """Return True only when the server explicitly reports auth is disabled.

    Preflight probe against ``GET /auth/whoami``: in ``disabled`` mode the
    server returns 503 with ``{"detail": "auth_disabled"}`` (see
    docs/design/access-control.md §7 and the ``auth_api.py`` handler).
    Any other status — 401 when standalone-auth is on but the client
    isn't signed in, 200 when a valid bearer is already present, network
    errors — returns False so the caller can proceed and surface the
    real error itself.
    """
    url = f"{api_url.rstrip('/')}/auth/whoami"
    try:
        urllib.request.urlopen(url, timeout=5).read()
    except urllib.error.HTTPError as e:
        if e.code != 503:
            return False
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail")
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            return False
        return detail == "auth_disabled"
    except (urllib.error.URLError, OSError):
        return False
    return False


def _do_login(api_name: str, api_url: str) -> int:
    """`<API> login` — prompt for creds, POST /auth/login via restish, persist bearer."""
    # Fail-fast when the server has auth disabled: don't prompt for
    # credentials the server would ignore anyway. Uses whatever URL is
    # currently registered (respects `sbs connect <alt>`), falling back
    # to the compiled-in default.
    effective_url = _registered_base(api_name) or api_url
    if _auth_disabled(effective_url):
        print(
            f"Authentication is disabled on {effective_url}; no login required.",
            file=sys.stderr,
        )
        return 2

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    if not username or not password:
        print("Username and password are required", file=sys.stderr)
        return 2

    _ensure_connected(api_name, api_url)

    # Body via stdin — nothing sensitive on argv. `-o json` forces
    # machine-parseable output regardless of the terminal state.
    body = json.dumps({"username": username, "password": password})
    result = subprocess.run(
        ["restish", api_name, "login", "-o", "json"],
        input=body,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or "login_failed"
        # restish exits non-zero on 401; the server's `invalid_credentials`
        # detail is in the response body which restish surfaces to stderr.
        if "401" in detail or "invalid_credentials" in detail:
            print("Login failed: invalid_credentials", file=sys.stderr)
        else:
            print(f"Login failed: {detail}", file=sys.stderr)
        return 1

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Server did not return valid JSON", file=sys.stderr)
        return 1

    token = response.get("token")
    if not token:
        print("Server did not return a token", file=sys.stderr)
        return 1

    _store_bearer(api_name, token)
    print(f"Signed in as {response.get('tenant_id', username)}")
    return 0


def _do_logout(api_name: str) -> int:
    """`<API> logout` — best-effort server revoke, then clear the stored bearer.

    Uses restish's own ``api set … auth: null`` patcher (no secrets on
    argv) rather than editing the config file inline.
    """
    subprocess.run(
        ["restish", api_name, "logout"],
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        ["restish", "api", "set", api_name, "profiles.default.auth: null"],
        capture_output=True,
        text=True,
        check=False,
    )
    print("Signed out")
    return 0


def _do_connect(api_name: str, url: str) -> int:
    """`<API> connect <URL>` — repoint the CLI at a different backend.

    Preserves credentials (no ``--replace``) so a URL switch does not
    force a re-login when the same tenant lives at both hosts.
    """
    _restish_connect(api_name, url, replace=False)
    _ensure_env_profile(api_name)
    print(f"Connected to {url}")
    return 0


def cli() -> None:
    """Main CLI entry point."""
    # All paths need restish on PATH.
    if not check_restish_installed():
        abort_with_install_instructions()

    # Intercept subcommands that need local-side work (config writes,
    # interactive prompts) before falling through to plain delegation.
    if len(sys.argv) >= 2:
        first = sys.argv[1]
        if first == "login":
            sys.exit(_do_login(API_NAME, API_URL))
        if first == "logout":
            sys.exit(_do_logout(API_NAME))
        if first == "connect":
            if len(sys.argv) != 3 or not sys.argv[2]:
                print("Error: usage: connect <URL>", file=sys.stderr)
                sys.exit(1)
            sys.exit(_do_connect(API_NAME, sys.argv[2]))

    # Everything else — including `whoami` — is a plain generated
    # OpenAPI operation. Register the API on first use, then hand off
    # to restish so it owns the TTY: color, streaming, interactive
    # auth flows, and per-command help all work as documented.
    _ensure_connected(API_NAME, API_URL)

    cmd = ["restish"]
    # If API_TOKEN_ENV is set, run under the env-token profile so the
    # token stays in the process environment and never lands on argv.
    if os.environ.get(API_TOKEN_ENV):
        cmd += ["-p", ENV_PROFILE]
    cmd += [API_NAME] + sys.argv[1:]

    try:
        os.execvp(cmd[0], cmd)
    except FileNotFoundError:
        abort_with_install_instructions()


if __name__ == "__main__":
    cli()
