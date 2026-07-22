#!/usr/bin/env bash
# Preview the static GitHub Pages site locally.
# Serves site/ over http://localhost:${PORT:-8080} with no build step.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$REPO_ROOT/site"
PORT="${PORT:-8080}"

if [ ! -f "$SITE_DIR/index.html" ]; then
  echo "error: $SITE_DIR/index.html not found" >&2
  exit 1
fi

echo "Serving $SITE_DIR at http://localhost:$PORT (Ctrl-C to stop)"
cd "$SITE_DIR"
exec python3 -m http.server "$PORT"
