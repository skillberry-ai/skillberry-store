#!/usr/bin/env bash
#
# git-state-manifest.sh — emit a canonical manifest of the current repository
# state.
#
# Same state → byte-identical manifest. Different states → different
# manifests. Two manifests can be diffed to enumerate which files changed.
#
# Format:
#   HEAD: <sha>
#   <status>\t<hash>\t<path>
#   <status>\t<hash>\t<path>
#   ...
#
# Where:
#   - <status> is the 2-char `git status --porcelain=v1` XY code.
#   - <hash>   is `git hash-object` of the working-tree file, or `-` for a
#              deleted file, `<dir>` for an untracked directory (rare with
#              --untracked-files=all but possible for empty dirs), or
#              `<missing>` for an entry with no accessible content.
#   - <path>   is the working-tree path (renames use the destination path;
#              the origin is intentionally dropped — we care about *what
#              state we are in*, not the rename history).
#
# Body lines are LC_ALL=C sorted so equivalent states produce byte-identical
# manifests.

set -euo pipefail

if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "HEAD: unknown"
    exit 0
fi

printf 'HEAD: %s\n' "$(git rev-parse HEAD 2>/dev/null || echo unknown)"

git status --porcelain=v1 -z --untracked-files=all 2>/dev/null | {
    while IFS= read -r -d '' entry; do
        status="${entry:0:2}"
        path="${entry:3}"
        # Renames and copies emit `new\0orig` as two NUL-separated slots; we
        # only care about the destination (the current on-disk state).
        first="${status:0:1}"
        if [ "$first" = "R" ] || [ "$first" = "C" ]; then
            IFS= read -r -d '' _orig || true
        fi
        second="${status:1:1}"
        if [ "$first" = "D" ] || [ "$second" = "D" ]; then
            hash='-'
        elif [ -f "$path" ]; then
            hash="$(git hash-object -- "$path" 2>/dev/null || echo unknown)"
        elif [ -d "$path" ]; then
            hash='<dir>'
        else
            hash='<missing>'
        fi
        printf '%s\t%s\t%s\n' "$status" "$hash" "$path"
    done
} | LC_ALL=C sort
