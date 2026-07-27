"""CLI module for sbs SDK using restish."""
import getpass
import json
import os
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn, Optional


API_NAME = "sbs"
API_URL = "http://0.0.0.0:8000"

# See docs/design/access-control.md §10.1 for the CLI/auth story.
# Env override for CI / scripting; if set, used as-is (and never written).
SBS_TOKEN_ENV = "SBS_TOKEN"


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

    return api_url


def _load_config() -> tuple[dict, Path]:
    """Return (config, path). Missing file => empty dict."""
    config_path = get_restish_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        return {}, config_path
    try:
        with open(config_path, "r") as fh:
            return json.load(fh) or {}, config_path
    except json.JSONDecodeError:
        return {}, config_path


def _write_config(config: dict, path: Path) -> None:
    with open(path, "w") as fh:
        json.dump(config, fh, indent=2)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass


def _api_base_url(api_name: str, default: str) -> str:
    config, _ = _load_config()
    entry = config.get(api_name) or {}
    return entry.get("base") or default


def _do_login(api_name: str, api_url: str) -> int:
    """`sbs login` — prompt for creds, POST /auth/login, persist bearer."""
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    if not username or not password:
        print("Username and password are required", file=sys.stderr)
        return 2

    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail", "")
        except Exception:  # noqa: BLE001
            detail = ""
        if e.code == 401:
            print(f"Login failed: {detail or 'invalid_credentials'}", file=sys.stderr)
        else:
            print(f"Login failed ({e.code}): {detail or e.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Cannot reach {api_url}: {e.reason}", file=sys.stderr)
        return 1

    token = body.get("token")
    if not token:
        print("Server did not return a token", file=sys.stderr)
        return 1

    ensure_api_configured(api_name, api_url)
    config, path = _load_config()
    entry = config.setdefault(api_name, {"base": api_url})
    headers = entry.setdefault("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    _write_config(config, path)
    print(f"Signed in as {body.get('tenant_id', username)}")
    return 0


def _do_logout(api_name: str, api_url: str) -> int:
    """`sbs logout` — best-effort revoke, then wipe the stored header."""
    config, path = _load_config()
    entry = config.get(api_name) or {}
    headers = entry.get("headers") or {}
    token: Optional[str] = None
    auth = headers.get("Authorization") or ""
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]

    if token:
        req = urllib.request.Request(
            f"{api_url.rstrip('/')}/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=15).read()
        except Exception:  # noqa: BLE001
            pass  # server-side best-effort; always clear local state.

    if "Authorization" in headers:
        headers.pop("Authorization", None)
        if not headers:
            entry.pop("headers", None)
        _write_config(config, path)
    print("Signed out")
    return 0


def _do_whoami(api_url: str, token_override: Optional[str]) -> int:
    """`sbs whoami` — GET /auth/whoami and pretty-print the result."""
    config, _ = _load_config()
    entry = config.get(API_NAME) or {}
    headers = entry.get("headers") or {}
    auth = token_override or headers.get("Authorization")
    if token_override:
        auth = f"Bearer {token_override}"
    if not auth:
        print("Not signed in — run `sbs login`", file=sys.stderr)
        return 1
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/auth/whoami",
        headers={"Authorization": auth},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("Session expired or invalid — run `sbs login`", file=sys.stderr)
        else:
            print(f"whoami failed ({e.code})", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Cannot reach {api_url}: {e.reason}", file=sys.stderr)
        return 1
    print(json.dumps(body, indent=2))
    return 0


def cli() -> None:
    """Main CLI entry point."""
    # Intercept auth subcommands before any restish check — they use plain
    # HTTP and don't need restish installed.
    if len(sys.argv) >= 2 and sys.argv[1] in ("login", "logout", "whoami"):
        api_url = _api_base_url(API_NAME, API_URL)
        if sys.argv[1] == "login":
            sys.exit(_do_login(API_NAME, api_url))
        if sys.argv[1] == "logout":
            sys.exit(_do_logout(API_NAME, api_url))
        if sys.argv[1] == "whoami":
            override = os.environ.get(SBS_TOKEN_ENV)
            sys.exit(_do_whoami(api_url, override))

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

        # SBS_TOKEN, if set, overrides any stored token for this invocation
        # (mirrors `gh`'s GH_TOKEN — see design §10.1). The env var is
        # forwarded via restish's per-request header mechanism if that
        # existed; instead we set restish's config via env and let restish
        # merge headers. Simpler: prepend an explicit -H when set.
        env = os.environ.copy()
        override_token = env.get(SBS_TOKEN_ENV)
        if override_token:
            cmd += ["-H", f"Authorization: Bearer {override_token}"]

        # Run restish and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
        )

        # 401 from the server surfaces as a restish non-zero exit; give the
        # user an actionable hint.
        combined_lower = (result.stdout + result.stderr).lower()
        if result.returncode != 0 and (
            "401" in combined_lower
            or "unauthorized" in combined_lower
            or "invalid_or_expired_token" in combined_lower
            or "missing_authorization" in combined_lower
        ):
            print(
                "Session expired or invalid — run `sbs login`",
                file=sys.stderr,
            )
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            sys.exit(result.returncode or 1)
        
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