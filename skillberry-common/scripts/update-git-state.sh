#!/usr/bin/env bash
#
# update-git-state.sh — content-idempotent update of the git-state manifest,
# with observability when state changes.
#
# usage: update-git-state.sh <version> <manifest-path> [<version-location>]
#
# The manifest file at <manifest-path> is the pivot of the build stamp graph
# (concepts 2 & 4 of docs/design/build_concepts.md). It is rewritten only
# when repository state actually changes, keeping its mtime stable so
# downstream builds don't re-fire spuriously.
#
# When state has changed, this script prints a human-readable summary of the
# files responsible. If <version-location> is supplied and non-empty, it also
# delegates to write-git-version.sh to update the app-visible version file
# (concept 2's optional projection).

set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "usage: $0 <version> <manifest-path> [<version-location>]" >&2
    exit 2
fi

version="$1"
manifest_path="$2"
version_location="${3:-}"

script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"

# All human-facing output goes to stderr so this script can be invoked from
# `$(shell ...)` in a Makefile without polluting captured stdout. Command
# substitution `$(...)` and explicit `> file` redirects still work normally.
exec 1>&2

if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Skipping git-state update: not inside a Git repository."
    exit 0
fi

new_manifest="$("$script_dir/git-state-manifest.sh")"

if [ -f "$manifest_path" ]; then
    old_manifest="$(cat -- "$manifest_path")"
    if [ "$old_manifest" = "$new_manifest" ]; then
        # No change → keep mtime stable so downstream stamps don't refire.
        exit 0
    fi
    prior_exists=1
else
    old_manifest=""
    prior_exists=0
fi

# --- observability ---
if [ "$prior_exists" = "0" ]; then
    echo "==> BUILD_VERSION set to '$version'. No prior BUILD_VERSION detected."
else
    echo "==> BUILD_VERSION updated to '$version'. The following changes have been detected since previous BUILD_VERSION:"

    old_head="$(printf '%s' "$old_manifest" | head -n1 | sed 's/^HEAD: //')"
    new_head="$(printf '%s' "$new_manifest" | head -n1 | sed 's/^HEAD: //')"

    if [ "$old_head" != "$new_head" ]; then
        echo "    HEAD: ${old_head} -> ${new_head}"
        if [ "$old_head" != "unknown" ] && [ "$new_head" != "unknown" ] && \
           git rev-parse --verify --quiet "$old_head" > /dev/null 2>&1; then
            git diff --name-only "$old_head" "$new_head" 2>/dev/null | \
                LC_ALL=C sort -u | sed 's|^|    ~ |'
        fi
    fi

    # Body deltas (dirty-set differences), aggregated by path so a content
    # change in one file shows as a single "!" line, not a "-" + "+" pair.
    tmp_old="$(mktemp)"
    tmp_new="$(mktemp)"
    trap 'rm -f -- "$tmp_old" "$tmp_new"' EXIT
    printf '%s' "$old_manifest" | tail -n +2 > "$tmp_old"
    printf '%s' "$new_manifest" | tail -n +2 > "$tmp_new"

    awk -F'\t' -v OFS='\t' '
        NR==FNR {
            if (NF >= 3) old[$3] = $1 OFS $2
            next
        }
        {
            if (NF >= 3) new[$3] = $1 OFS $2
        }
        END {
            n = 0
            for (p in old) if (!(p in seen)) { seen[p] = 1; paths[++n] = p }
            for (p in new) if (!(p in seen)) { seen[p] = 1; paths[++n] = p }
            # Insertion sort by path (n is small — dirty file count).
            for (i = 2; i <= n; i++) {
                key = paths[i]
                j = i - 1
                while (j >= 1 && paths[j] > key) {
                    paths[j+1] = paths[j]
                    j--
                }
                paths[j+1] = key
            }
            for (i = 1; i <= n; i++) {
                p = paths[i]
                has_o = (p in old); has_n = (p in new)
                if (has_o && has_n) {
                    if (old[p] != new[p]) print "    ! " p
                } else if (has_n) {
                    print "    + " p
                } else {
                    print "    - " p
                }
            }
        }
    ' "$tmp_old" "$tmp_new"
fi

# --- persist manifest & optional VERSION_LOCATION ---
mkdir -p -- "$(dirname -- "$manifest_path")"
printf '%s\n' "$new_manifest" > "$manifest_path"

if [ -n "$version_location" ]; then
    "$script_dir/write-git-version.sh" "$version" "$version_location"
fi
