// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CatalogImportView } from './CatalogImportView';
import type { CatalogImportConfig, Plugin } from '@/types';

// A deliberately generic "widget" config: proves the component bakes in NO plugin-specific
// strings, endpoints, or field names — everything comes from `config` + the CatalogItem contract.
const CONFIG: CatalogImportConfig = {
  type: 'catalog-import',
  title: 'Import widgets',
  description: 'Search the widget catalog.',
  search_endpoint: '/api/plugins/widgetcat/search',
  detail_endpoint: '/api/plugins/widgetcat/detail/{id}',
  import_endpoint: '/api/plugins/widgetcat/import',
  search_placeholder: 'Search widgets…',
  min_query_chars: 2,
  import_button_label: 'Import selected',
  columns: { primary: 'Name', secondary: 'Source', description: 'Description' },
};

const PLUGIN = { slug: 'widgetcat', name: 'Widget Catalog', enabled: true, status: 'OK' } as unknown as Plugin;

const mockFetch = vi.fn();
global.fetch = mockFetch as unknown as typeof fetch;

function jsonResponse(body: any, ok = true) {
  return Promise.resolve({ ok, status: ok ? 200 : 500, statusText: 'x', json: () => Promise.resolve(body) });
}

beforeEach(() => {
  mockFetch.mockReset();
  // Silence IntersectionObserver in jsdom: fire the callback immediately as "visible".
  (global as any).IntersectionObserver = class {
    cb: any;
    constructor(cb: any) { this.cb = cb; }
    observe() { this.cb([{ isIntersecting: true }]); }
    disconnect() {}
  };
});

function renderView() {
  render(<CatalogImportView config={CONFIG} plugin={PLUGIN} isOpen={true} onClose={vi.fn()} />);
}

describe('CatalogImportView', () => {
  it('searches, lazy-loads a description, selects, and imports', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.endsWith('/search')) {
        return jsonResponse({
          success: true, message: 'Found 1',
          data: { items: [{ id: 'w1', title: 'Widget One', subtitle: 'w1', source: 'acme', description: null, details: [{ label: 'ID', value: 'w1' }], badges: [] }], count: 1 },
        });
      }
      if (url.includes('/detail/')) return jsonResponse({ description: 'A fine widget' });
      if (url.endsWith('/import')) {
        return jsonResponse({ success: true, message: 'Imported 1 skill', data: { imported: [{ id: 'w1', title: 'Widget One', summary: '2 tools, 0 snippets' }], failed: [] } });
      }
      return jsonResponse({}, false);
    });

    renderView();
    fireEvent.change(screen.getByLabelText('Search query'), { target: { value: 'wid' } });
    fireEvent.click(screen.getByRole('button', { name: /search/i }));

    // findByText throws if absent, so these assert presence on their own.
    expect(await screen.findByText('Widget One')).toBeTruthy();
    expect(await screen.findByText('A fine widget')).toBeTruthy();

    // Select the row's checkbox then import.
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /import selected/i }));

    expect(await screen.findByText('Imported 1 skill')).toBeTruthy();
    expect(screen.getByText(/2 tools, 0 snippets/)).toBeTruthy();
  });

  it('shows a disabled banner and setup steps when the plugin is not enabled', async () => {
    const disabled = { ...PLUGIN, enabled: false, status: 'Disabled: no token' } as unknown as Plugin;
    const cfg = { ...CONFIG, setup_instructions: { title: 'Auth required', steps: [{ label: 'Option A', description: 'do x' }], docs_url: 'https://d' } };
    render(<CatalogImportView config={cfg} plugin={disabled} isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByText('Auth required')).toBeTruthy();
    expect(screen.getByText('Option A')).toBeTruthy();
  });
});
