#!/usr/bin/env bash
#
# write-git-version.sh <version> <path>
#
# Content-idempotent write of the git version file. The file is written only
# when it does not exist or its content differs from the desired content, so
# the mtime is stable across invocations that observe the same state.
#
# This implements concept 2 of docs/design/build_concepts.md: every generated
# file that gates downstream builds must be rewritten only when its content
# actually changes.

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <version> <path>" >&2
    exit 2
fi

version="$1"
path="$2"

new_content="__git_version__ = \"${version}\""

if [ ! -f "$path" ]; then
    mkdir -p -- "$(dirname -- "$path")"
    printf '%s\n' "$new_content" > "$path"
    echo "Created git version file at $path"
    exit 0
fi

current_content="$(cat -- "$path" 2>/dev/null || true)"

# Compare with trailing-newline normalization (printf adds one; older files
# might not have one).
if [ "$current_content" = "$new_content" ]; then
    exit 0
fi

printf '%s\n' "$new_content" > "$path"
echo "Updated git version in $path to $version"
