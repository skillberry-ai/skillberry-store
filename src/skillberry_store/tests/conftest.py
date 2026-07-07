"""Root pytest configuration for skillberry-store tests.

Sets ``SKILLBERRY_PLUGIN_STATE_FILE=""`` so SBS boots empty (no plugins persisted)
during tests, per docs/plugin-process-migration-plan.md § Stage 3.
"""

import os

os.environ.setdefault("SKILLBERRY_PLUGIN_STATE_FILE", "")
