#!/usr/bin/env bash
#
# git-version.sh — compute the BUILD_VERSION label for the current repo state.
#
# The label is a pure function of repository state:
#   - clean at a release commit:                    <release>            (e.g. 0.5.3)
#   - N commits past the latest release:            <release>-<N>-g<sha> (e.g. 0.5.3-5-gc9b7ddd)
#   - no releases in the repo yet:                  g<sha>               (e.g. gc9b7ddd)
#   - any dirty state (staged/unstaged/untracked
#     non-ignored) appends:                         -dirty-<hash7>
#
# The dirty fingerprint is a hash over the concatenation of `git diff HEAD`
# (which covers both staged and unstaged tracked-file changes) and the sorted
# list plus contents of untracked non-ignored files. This ensures different
# dirty states produce different labels, while equivalent states produce the
# same label.
#
# Prints a single line, no quotes.

set -euo pipefail

if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "unknown"
    exit 0
fi

# Base label: release-aware, matching git-describe conventions.
latest_release="$(git branch -r 2>/dev/null | grep 'branch-' | sed 's|.*/branch-||' | sort -V | tail -n 1 | head -n 1 || true)"
current_commit="$(git rev-parse --short=7 HEAD 2>/dev/null || echo "0000000")"

if [ -z "$latest_release" ]; then
    base="g${current_commit}"
else
    # Count commits in HEAD past the release tag. If the tag is not resolvable
    # locally, fall back to the "no-release" form to avoid spurious labels.
    if commit_count="$(git rev-list --count "${latest_release}..HEAD" 2>/dev/null)"; then
        if [ "$commit_count" = "0" ]; then
            base="$latest_release"
        else
            base="${latest_release}-${commit_count}-g${current_commit}"
        fi
    else
        base="g${current_commit}"
    fi
fi

# Dirty detection: git status --porcelain is the authoritative source per
# concept 1 (covers staged, unstaged, and untracked non-ignored files).
porcelain="$(git status --porcelain 2>/dev/null || true)"

if [ -z "$porcelain" ]; then
    printf '%s\n' "$base"
    exit 0
fi

# Dirty: compute a fingerprint over the actual diff and untracked contents so
# different dirty states get different labels.
dirty_hash="$(
    {
        # Tracked-file changes (staged + unstaged), relative to HEAD.
        git diff HEAD 2>/dev/null || true
        # Untracked, non-ignored files: names first (sorted), then contents.
        git ls-files --others --exclude-standard -z 2>/dev/null | LC_ALL=C sort -z | \
        while IFS= read -r -d '' f; do
            printf '\n== %s ==\n' "$f"
            cat -- "$f" 2>/dev/null || true
        done
    } | git hash-object --stdin | cut -c1-7
)"

printf '%s-dirty-%s\n' "$base" "$dirty_hash"
