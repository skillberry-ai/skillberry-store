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
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});