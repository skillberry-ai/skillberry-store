#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# make-pr-common.sh
#
# Creates a PR in the "common" repo based on subtree changes in SB_COMMON_PATH.
#
# Inputs (env vars):
#   SB_COMMON_REMOTE   - git remote name for the common repo (must exist)
#   SB_COMMON_BRANCH   - base branch in common repo (e.g., main)
#   SB_COMMON_PATH     - subtree folder path (e.g., skillberry-common)
#   PR_COMMON_BRANCH_PREFIX (optional) - prefix for new branches (default: pr/common)
#
# Behavior:
#   - No fetch is performed. Uses local refs for SB_COMMON_REMOTE/SB_COMMON_BRANCH.
#   - Aborts early if no new subtree content compared to local remote-tracking ref.
#   - Pushes subtree content to a new branch on SB_COMMON_REMOTE (creates branch remotely).
#   - Uses gh pr create -e to open editor for title/body.
#   - Uses GH_REPO to target the common repo without needing --repo.
# ------------------------------------------------------------------------------

: "${SB_COMMON_REMOTE:?Missing env var SB_COMMON_REMOTE}"
: "${SB_COMMON_BRANCH:?Missing env var SB_COMMON_BRANCH}"
: "${SB_COMMON_PATH:?Missing env var SB_COMMON_PATH}"
PR_COMMON_BRANCH_PREFIX="${PR_COMMON_BRANCH_PREFIX:-pr/common}"

die() { echo "ERROR: $*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

need_cmd git
need_cmd sed
need_cmd gh

# Ensure we run from repo root (safer)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die "Not inside a git repository"
cd "$REPO_ROOT"

# Ensure the remote exists (per requirement: assume it exists; fail if missing)
git remote get-url "$SB_COMMON_REMOTE" >/dev/null 2>&1 \
  || die "git remote '$SB_COMMON_REMOTE' does not exist"

# No-fetch constraint: require local remote-tracking ref to exist
BASE_REF="refs/remotes/${SB_COMMON_REMOTE}/${SB_COMMON_BRANCH}"
git show-ref --verify --quiet "$BASE_REF" \
  || die "Missing local ref $BASE_REF (no fetch requested). Run: git fetch ${SB_COMMON_REMOTE} ${SB_COMMON_BRANCH}"

REMOTE_SHA="$(git rev-parse "$BASE_REF")"

# Compute subtree split commit representing current SB_COMMON_PATH content
SPLIT_SHA="$(git subtree split --prefix "$SB_COMMON_PATH" HEAD)"

# No changes check:
# If SPLIT_SHA is already reachable from the remote-tracking branch, nothing new to PR.
if git merge-base --is-ancestor "$SPLIT_SHA" "$REMOTE_SHA"; then
  echo "No changes detected in '${SB_COMMON_PATH}' relative to ${SB_COMMON_REMOTE}/${SB_COMMON_BRANCH}. Aborting."
  exit 0
fi

# Create a unique branch name
TS="$(date +%Y%m%d-%H%M%S)"
USER_SLUG="$(git config user.name 2>/dev/null | tr ' ' '-' | tr -cd '[:alnum:]-' | tr '[:upper:]' '[:lower:]' || true)"
[[ -n "$USER_SLUG" ]] || USER_SLUG="user"
BRANCH="${PR_COMMON_BRANCH_PREFIX}/${USER_SLUG}/${TS}"

echo "==> Pushing subtree '${SB_COMMON_PATH}' to ${SB_COMMON_REMOTE}:${BRANCH}"
git subtree push --prefix "$SB_COMMON_PATH" "$SB_COMMON_REMOTE" "$BRANCH"

# Derive GH_REPO from SB_COMMON_REMOTE URL
# Supports:
# - SSH:   git@host:org/repo.git
# - HTTPS: https://host/org/repo.git
URL="$(git remote get-url "$SB_COMMON_REMOTE")"

HOST="$(echo "$URL" | sed -E 's#^git@([^:]+):.*#\1#; s#^https?://([^/]+)/.*#\1#')"
SLUG="$(echo "$URL" | sed -E 's#^git@[^:]+:##; s#^https?://[^/]+/##; s#\.git$##')"

[[ -n "$HOST" ]] || die "Failed to parse host from remote URL: $URL"
[[ -n "$SLUG" ]] || die "Failed to parse repo slug from remote URL: $URL"

REPO="${HOST}/${SLUG}"

echo "==> Creating PR in ${REPO}: ${BRANCH} -> ${SB_COMMON_BRANCH}"
# -e / --editor: opens editor for title/body (first line title, rest body)
# GH_REPO: tells gh which repo to operate on when not in that repo directory
GH_REPO="$REPO" gh pr create \
  --base "$SB_COMMON_BRANCH" \
  --head "$BRANCH" \
  -e

echo "==> Done."
