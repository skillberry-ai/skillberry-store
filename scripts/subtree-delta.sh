#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  subtree-delta.sh <REMOTE> <BRANCH> <PREFIX>

Args:
  REMOTE  - git remote name used for the subtree (e.g., upstream-libfoo)
  BRANCH  - branch name on that remote (e.g., main)
  PREFIX  - path to the subtree directory in this repo (e.g., third_party/libfoo)

What it does (non-squashed subtree workflow):
  1) Fetches REMOTE/BRANCH
  2) Computes a subtree-only commit for PREFIX using: git subtree split -P <PREFIX>
  3) Prints how many commits the local subtree is ahead/behind the remote branch

Examples:
  subtree-delta.sh upstream-libfoo main third_party/libfoo
  subtree-delta.sh vendor-libbar master deps/libbar
EOF
}

# Accept -h/--help as well as missing args
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 3 ]]; then
  usage >&2
  exit 2
fi

REMOTE="$1"
BRANCH="$2"
PREFIX="$3"

REMOTE_HEAD="$REMOTE/$BRANCH"

# Compute a subtree-only commit representing the current state/history of PREFIX
# git subtree split extracts the history of a subdirectory into its own commit/branch. [1](https://www.gnu.org/s/make/manual/html_node/Options_002fRecursion.html)[2](https://getdocs.org/Make/docs/latest/Options_002fRecursion)
LOCAL_SPLIT="$(git subtree split -P "$PREFIX")"

# Count commits reachable from LOCAL_SPLIT but not from REMOTE_HEAD (ahead)
# and commits reachable from REMOTE_HEAD but not from LOCAL_SPLIT (behind).
# Range A..B is shorthand for commits in B excluding those reachable from A. [3](https://www.gnu.org/software/make/manual/html_node/POSIX-Jobserver.html)
AHEAD="$(git rev-list --count "$REMOTE_HEAD..$LOCAL_SPLIT")"
BEHIND="$(git rev-list --count "$LOCAL_SPLIT..$REMOTE_HEAD")"

echo "REMOTE:        $REMOTE"
echo "BRANCH:        $BRANCH"
echo "PREFIX:        $PREFIX"
echo "REMOTE_HEAD:   $REMOTE_HEAD"
echo "LOCAL_SPLIT:   $LOCAL_SPLIT"
echo "AHEAD:         $AHEAD   (local subtree commits not in remote)"
echo "BEHIND:        $BEHIND  (remote commits not in local subtree)"
