"""CLI module for {{API_NAME}} SDK using restish."""
import json
import os
import subprocess
import sys
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


def ensure_api_configured() -> None:
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
    if API_NAME not in config:
        needs_update = True
    elif config[API_NAME].get("base") != API_URL:
        needs_update = True
    
    if needs_update:
        # Configure the API
        config[API_NAME] = {
            "base": API_URL,
            "spec_files": [f"{API_URL}/openapi.json"]
        }
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Sync the API spec
        try:
            subprocess.run(
                ["restish", "api", "sync", API_NAME],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to sync API spec: {e}", file=sys.stderr)


def cli() -> None:
    """Main CLI entry point."""
    # Check if restish is installed
    if not check_restish_installed():
        abort_with_install_instructions()
    
    # Ensure API is configured
    ensure_api_configured()
    
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
        
        for line in output_lines:
            if line.strip().startswith('Global Flags:'):
                skip_section = True
            elif skip_section and line and not line[0].isspace():
                # End of Global Flags section
                skip_section = False
            
            if not skip_section:
                filtered_lines.append(line)
        
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