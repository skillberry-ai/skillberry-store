#!/usr/bin/env bash
set -euo pipefail

# Script for creating a PR: the PR target is provided as argument, and if not provided, it is auto-detected 
# from the git repository. If there are new commits compared to target branch head (recommended running "git fetch" before this script),
# then a PR can be created. In that case, a new unique branch is generated and pushed into, and then a PR is created using gh CLI.

die() { echo "ERROR: $*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"; }

need_cmd git
need_cmd gh
need_cmd tr
need_cmd date
need_cmd sed

# 1) Check we are in a git repository
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "Not inside a git repository. Please run this from within a git working tree."

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$CURRENT_BRANCH" != "HEAD" ]] || die "Detached HEAD state. Please checkout a branch first."

PR_BRANCH=""
TARGET_BRANCH=""
BASE_REF=""
REMOTE_PUSHED=0
PR_CREATED=0
PUSH_REMOTE="origin"

cleanup() {
  # Don't let cleanup errors mask the original failure
  set +e

  # If PR wasn't created but we pushed the remote branch, delete it
  if [[ "$PR_CREATED" -eq 0 && "$REMOTE_PUSHED" -eq 1 && -n "$PR_BRANCH" ]]; then
    echo "==> PR was not created; deleting remote branch ${PUSH_REMOTE}/${PR_BRANCH}"
    # Delete remote branch (ignore failures)
    git push "$PUSH_REMOTE" --delete "$PR_BRANCH" >/dev/null 2>&1 || true
  fi

  # Always delete local PR branch if it exists
  if [[ -n "$PR_BRANCH" ]] && git show-ref --verify --quiet "refs/heads/${PR_BRANCH}"; then
    echo "==> Deleting local branch ${PR_BRANCH}"
    git branch -D "$PR_BRANCH" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

# 0) Optional argument TARGET_BRANCH.
# If not provided, auto-detect from origin/HEAD (remote default branch).
TARGET_BRANCH="${1:-}"

if [[ -z "${TARGET_BRANCH}" ]]; then
  # Prefer symbolic-ref because origin/HEAD is typically a symref to origin/<default>
  if git symbolic-ref -q --short refs/remotes/origin/HEAD >/dev/null 2>&1; then
    # e.g. "origin/main" -> "main"
    TARGET_BRANCH="$(git symbolic-ref -q --short refs/remotes/origin/HEAD | sed 's#^origin/##')"
  else
    die "No TARGET_BRANCH provided and cannot auto-detect default branch: refs/remotes/origin/HEAD is not set.
Fix: run 'git remote set-head origin -a' (may contact the remote) and try again."
  fi
fi

# Resolve TARGET_BRANCH to a remote-tracking ref
BASE_REF=""
if git show-ref --verify --quiet "refs/remotes/origin/${TARGET_BRANCH}"; then
  BASE_REF="refs/remotes/origin/${TARGET_BRANCH}"
else
  die "Target branch '${TARGET_BRANCH}' not found as origin/${TARGET_BRANCH} (refs/remotes)."
fi

REMOTE_SHA="$(git rev-parse "$BASE_REF")"

# 2) Check that HEAD has new commits compared to TARGET_BRANCH head
if git merge-base --is-ancestor HEAD "$REMOTE_SHA"; then
  echo "No changes detected in local HEAD relative to ${TARGET_BRANCH}. Aborting."
  exit 0
fi

# 3) Create PR branch name: pr/TARGET_BRANCH/user/timestamp
USER_SLUG="$(git config user.name 2>/dev/null | tr ' ' '-' | tr -cd '[:alnum:]-' | tr '[:upper:]' '[:lower:]' || true)"
[[ -n "$USER_SLUG" ]] || USER_SLUG="user"
TS="$(date +%Y%m%d-%H%M%S)"

# Sanitize TARGET_BRANCH for inclusion in branch name.
TARGET_SAFE="$(echo "$TARGET_BRANCH" | tr -cd '[:alnum:]._/-' | sed -E 's#^/+##; s#/+$##')"
[[ -n "$TARGET_SAFE" ]] || die "TARGET_BRANCH became empty after sanitization; original was '${TARGET_BRANCH}'."

PR_BRANCH="pr/${TARGET_SAFE}/${USER_SLUG}/${TS}"

# Avoid collisions locally
if git show-ref --verify --quiet "refs/heads/${PR_BRANCH}"; then
  die "Local branch '${PR_BRANCH}' already exists."
fi

echo "==> Current branch: ${CURRENT_BRANCH}"
echo "==> Target branch:  ${TARGET_BRANCH} (ref: ${BASE_REF})"
echo "==> PR branch:      ${PR_BRANCH}"

# Create local branch ref pointing at HEAD (no checkout needed)
git branch "${PR_BRANCH}" HEAD

# 4) Push commits to the PR branch (remote: origin)
echo "==> Pushing to origin: ${PR_BRANCH}"
git push -u origin "refs/heads/${PR_BRANCH}:refs/heads/${PR_BRANCH}"
REMOTE_PUSHED=1

# Derive GH_REPO from SB_COMMON_REMOTE URL
# Supports:
# - SSH:   git@host:org/repo.git
# - HTTPS: https://host/org/repo.git
URL="$(git remote get-url origin)"

HOST="$(echo "$URL" | sed -E 's#^git@([^:]+):.*#\1#; s#^https?://([^/]+)/.*#\1#')"
SLUG="$(echo "$URL" | sed -E 's#^git@[^:]+:##; s#^https?://[^/]+/##; s#\.git$##')"

[[ -n "$HOST" ]] || die "Failed to parse host from remote URL: $URL"
[[ -n "$SLUG" ]] || die "Failed to parse repo slug from remote URL: $URL"

REPO="${HOST}/${SLUG}"

# 5) Create PR to TARGET_BRANCH from PR_BRANCH using gh with editor mode
# GH_REPO: tells gh which repo to operate on when not in that repo directory
GH_REPO="$REPO" gh pr create \
  --base "${TARGET_BRANCH}" \
  --head "${PR_BRANCH}" \
  --fill-verbose \
  -e
PR_CREATED=1

echo "==> Done."
