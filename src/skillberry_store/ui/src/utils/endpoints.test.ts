// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect } from 'vitest';
import { normalizeEndpoint } from './endpoints';

// Regression net for PR #308 review issue #1: with the Vite `/api` rewrite proxy
// gone, any plugin-declared URL that keeps its legacy `/api` prefix 404s.
describe('normalizeEndpoint', () => {
  it('strips a leading /api prefix from plugin-declared endpoints', () => {
    expect(normalizeEndpoint('/api/plugins/dedupe/decisions')).toBe('/plugins/dedupe/decisions');
    expect(normalizeEndpoint('/api/plugins/coffee/status/job-1')).toBe('/plugins/coffee/status/job-1');
  });

  it('maps the bare /api root to /', () => {
    expect(normalizeEndpoint('/api')).toBe('/');
  });

  it('leaves already-normalised paths untouched', () => {
    expect(normalizeEndpoint('/plugins/dedupe/decisions')).toBe('/plugins/dedupe/decisions');
    expect(normalizeEndpoint('/')).toBe('/');
    expect(normalizeEndpoint('')).toBe('');
  });

  it('only strips the prefix at the start of the path', () => {
    expect(normalizeEndpoint('/plugins/api/thing')).toBe('/plugins/api/thing');
    expect(normalizeEndpoint('/v1/api/thing')).toBe('/v1/api/thing');
  });

  it('does not strip look-alike prefixes', () => {
    expect(normalizeEndpoint('/apiary/things')).toBe('/apiary/things');
    expect(normalizeEndpoint('/api-docs')).toBe('/api-docs');
  });

  it('leaves absolute URLs to other hosts untouched', () => {
    expect(normalizeEndpoint('https://example.com/api/x')).toBe('https://example.com/api/x');
  });
});
