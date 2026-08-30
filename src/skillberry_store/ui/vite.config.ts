import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { existsSync, readFileSync } from 'fs';

// Read the ACL mode from access_control_config.yaml (or the file pointed at
// by SBS_ACCESS_CONTROL_CONFIG) at Vite start-up so the SPA gets it as a
// compile-time constant via `import.meta.env.VITE_ACL_MODE`. See §10.4 of
// docs/design/access-control.md.
//
// A minimal top-level scan is enough — the file starts with `mode: <value>`.
// We don't want a new runtime dep for this.
function readAclMode(): 'disabled' | 'standalone' {
  const explicit = process.env.SBS_ACCESS_CONTROL_CONFIG;
  const candidates = explicit
    ? [explicit]
    : [
        path.resolve(__dirname, '../../../access_control_config.yaml'),
        path.resolve(process.cwd(), 'access_control_config.yaml'),
      ];
  for (const p of candidates) {
    if (!existsSync(p)) continue;
    try {
      const text = readFileSync(p, 'utf-8');
      const m = text.match(/^\s*mode\s*:\s*(\S+)/m);
      if (m && m[1] === 'standalone') return 'standalone';
      return 'disabled';
    } catch {
      // fall through to disabled
    }
  }
  return 'disabled';
}

// Whether to emit sourcemaps for a production build. Opt-in, not default:
// sourcemaps embed the complete original TypeScript, and the built bundle is now
// served in-process by FastAPI on the *same, unauthenticated* port as the API
// (GET /ui* is on the allow-list), so it can no longer be firewalled separately
// the way the old port-8002 `vite preview` could. Emitting maps by default
// therefore publishes the frontend source to anyone who can reach the service.
// Turn them on deliberately when debugging a deployed build:
//   VITE_SOURCEMAP=true make ui-build
function sourcemapsEnabled(): boolean {
  const value = (process.env.VITE_SOURCEMAP ?? '').trim().toLowerCase();
  return value === 'true' || value === '1' || value === 'yes';
}

// Parse the VITE_ALLOWED_HOSTS env var into Vite's server.allowedHosts value.
// Unset  -> undefined (Vite default: only localhost is allowed).
// "true"/"all"/"*" -> true (allow any host; useful behind a trusted gateway).
// "a,b"  -> ["a", "b"] (explicit allow-list).
function parseAllowedHosts(value?: string): true | string[] | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  if (trimmed === 'true' || trimmed === 'all' || trimmed === '*') return true;
  return trimmed
    .split(',')
    .map((host) => host.trim())
    .filter(Boolean);
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_ACL_MODE': JSON.stringify(readAclMode()),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: parseInt(process.env.VITE_UI_PORT || '8002'),
    allowedHosts: parseAllowedHosts(process.env.VITE_ALLOWED_HOSTS),
    proxy: {
      // Forward every request that is NOT a Vite asset (src/, @vite/, @fs/,
      // node_modules/) and NOT the UI route to the FastAPI backend.
      // The API has no path prefix in this new layout — routes are served
      // directly at their canonical paths (e.g. /skills/, /tools/, /auth/).
      '^/(?!ui|@vite|@fs|src|node_modules)': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // `vite preview` serves the built bundle without filesystem watchers.
  // It reads this block, not `server:`, so port/host/allowedHosts/proxy
  // must be mirrored here for prod-style startup (see `make ui-build`).
  preview: {
    port: parseInt(process.env.VITE_UI_PORT || '8002'),
    host: true,
    allowedHosts: parseAllowedHosts(process.env.VITE_ALLOWED_HOSTS),
    proxy: {
      '^/(?!ui|@vite|@fs|src|node_modules)': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  base: '/ui/',
  build: {
    outDir: 'dist',
    sourcemap: sourcemapsEnabled(),
  },
});