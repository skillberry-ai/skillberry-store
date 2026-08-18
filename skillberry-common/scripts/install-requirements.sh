#!/usr/bin/env bash
#
# install-requirements.sh <odeps> <skipopt>
#
# Runs `uv pip install -e .[<odeps>]` and maintains the install stamps per
# concept 6 of docs/design/build_concepts.md:
#
#   * `uv pip install -e .[X]` replaces the previous set of extras, so any
#     older non-empty-ODEPS stamp becomes a lie.
#   * `uv pip install -e .[X]` also installs the base package, so the
#     empty-ODEPS stamp is always valid after any successful install.
#   * If SKIPOPT=1 and the extras install fails, fall back to installing just
#     the base package; in that case only the empty-ODEPS stamp is valid.
#   * On outright failure, touch nothing so retry is forced.

set -eu

odeps="${1:-}"
skipopt="${2:-}"

stamp_dir=".stamps"
mkdir -p -- "$stamp_dir"

# Marks the current environment as base-only (empty-ODEPS). Called on any
# successful install path.
touch_base_only() {
    rm -f -- "$stamp_dir"/install-requirements-*
    touch -- "$stamp_dir/install-requirements-"
}

# Marks the current environment as base + <odeps>.
touch_with_extras() {
    rm -f -- "$stamp_dir"/install-requirements-*
    touch -- "$stamp_dir/install-requirements-"
    touch -- "$stamp_dir/install-requirements-$odeps"
}

if [ -z "$odeps" ]; then
    uv pip install -e . || exit 1
    touch_base_only
    exit 0
fi

if uv pip install -e ".[$odeps]"; then
    touch_with_extras
    exit 0
fi

if [ "$skipopt" = "1" ]; then
    echo "Optional dependency install failed for ODEPS=$odeps; retrying without optional dependencies because SKIPOPT=1" >&2
    uv pip install -e . || exit 1
    touch_base_only
    exit 0
fi

exit 1
