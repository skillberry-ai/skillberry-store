import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

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