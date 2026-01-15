#!/bin/bash
set -euo pipefail

warn() { echo "WARNING: $*" >&2; }

# Return 0 if running inside an active venv, else 1.
in_active_venv() {
  command -v python >/dev/null 2>&1 || return 1
  python -c 'import sys; raise SystemExit(0 if sys.prefix != sys.base_prefix else 1)' >/dev/null 2>&1
}

# Extract current version as three integers: major minor micro
get_py_version() {
  python -c 'import sys; v=sys.version_info; print(f"{v[0]}.{v[1]}.{v[2]}")'
}

main() {

  local script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

  if (( $# < 1 )); then
    warn "No version specs provided."
    exit 1
  fi

  # 1) Ensure active venv
  if ! in_active_venv; then
    warn "No active virtual env found"
    exit 1
  fi

  # Current python version
  local current=$(get_py_version)

  local matcher=${script_dir}/match_spec.py

  # 2) Ensure python version matches one of the arguments
  for spec in "$@"; do
    if python "$matcher" "$spec" "$current" >/dev/null; then
      exit 0
    fi
  done

  warn "Unsupported Python version: ${current}. Allowed specs: $*"
  exit 1
}

main "$@"
