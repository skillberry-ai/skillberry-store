// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

// Normalise a plugin-supplied endpoint URL by stripping a leading "/api"
// prefix if present. Plugin authors write "/api/plugins/..." because the Vite
// proxy used to strip it before forwarding to FastAPI; now that the UI is
// served in-process by FastAPI, no proxy exists and the routes are accessed
// directly (e.g. "/plugins/..."). Keeping this normaliser means existing
// plugins do not need to be updated.
//
// Every raw `fetch()` of a plugin-declared URL MUST go through this helper.
// Missing one is a silent 404 at runtime (see PR #308 review issue #1), and
// `test_no_unnormalized_api_urls.py` guards the invariant statically.
const API_PREFIX = '/api';

export function normalizeEndpoint(url: string): string {
  if (url === API_PREFIX) return '/';
  return url.startsWith(`${API_PREFIX}/`) ? url.slice(API_PREFIX.length) : url;
}
