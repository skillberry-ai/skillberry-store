"""CLI module for {{API_NAME}} SDK using restish."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn


API_NAME = "{{API_NAME}}"
API_URL = "{{API_URL}}"


def check_restish_installed() -> bool:
    """Check if restish is installed and available on PATH."""
    try:
        subprocess.run(
            ["restish", "--version"],
            capture_output=True,
            check=True,
            text=True
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


def get_restish_config_path() -> Path:
    """Get the path to restish config file."""
    config_dir = Path.home() / ".config" / "restish"
    return config_dir / "apis.json"


def ensure_api_configured(api_name: str, api_url: str, force_update: bool = False) -> str:
    """Ensure the API is configured in restish with correct URL."""
    config_path = get_restish_config_path()
    
    # Create config directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config or create new one
    if config_path.exists():
        with open(config_path, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                config = {}
    else:
        config = {}
    
    # Check if API is configured with correct URL
    needs_update = False
    if force_update or api_name not in config or "base" not in config[api_name]:
        needs_update = True
    # elif config[API_NAME].get("base") != API_URL:
    #     needs_update = True
    
    if not needs_update:
        return config[api_name]["base"]

    # To avoid conflicts, remove any existing API configuration with the same base URL
    for name, api_config in list(config.items()):
        if isinstance(api_config, dict) and ("base" in api_config) and api_config["base"] == api_url:
            del config[name]
            print(f"Removed conflicting API configuration: {name}", file=sys.stderr)

    # Configure the API
    config[api_name] = {
        "base": api_url,
        "spec_files": [f"{api_url}/openapi.json"]
    }
    
    # Write updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Sync the API spec
    try:
        subprocess.run(
            ["restish", "api", "sync", api_name],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to sync API spec: {e}", file=sys.stderr)
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
    # Check if restish is installed
    if not check_restish_installed():
        abort_with_install_instructions()
    
    # Check for "connect <URL>" command
    if len(sys.argv) == 3 and sys.argv[1] == "connect":
        # Extract URL from "connect <URL>" format
        url = sys.argv[2]
        if url:
            ensure_api_configured(API_NAME, url, True)
            print(f"Connected to {url}")
            sys.exit(0)
        else:
            print("Error: Invalid connect command. Usage: connect <URL>", file=sys.stderr)
            sys.exit(1)
    
    # Ensure API is configured
    api_url = ensure_api_configured(API_NAME, API_URL)
    
    # Delegate to restish, passing all arguments and filtering output
    try:
        # Build the command
        cmd = ["restish", API_NAME] + sys.argv[1:]
        
        # Run restish and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        # Filter out "Global Flags:" section from output
        output_lines = result.stdout.split('\n')
        filtered_lines = []
        skip_section = False
        found_global_flags = False
        
        for line in output_lines:
            if line.strip().startswith('Global Flags:'):
                skip_section = True
                found_global_flags = True
            elif skip_section and line and not line[0].isspace():
                # End of Global Flags section
                skip_section = False
            
            if not skip_section:
                line  = line.replace("restish ", "")
                filtered_lines.append(line)
        
        # If we found and skipped Global Flags section, append custom text
        if found_global_flags:
            filtered_lines.append(f"Connected to URL: {api_url}\n")
            filtered_lines.append("General commands:")
            filtered_lines.append(f"  connect <URL>\t\t\tconnect to an alternate {API_NAME} URL\n")
        
        # Print filtered output
        print('\n'.join(filtered_lines), end='')
        
        # Print stderr if any
        if result.stderr:
            print(result.stderr, file=sys.stderr, end='')
        
        # Exit with same code as restish
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"Error executing restish: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()