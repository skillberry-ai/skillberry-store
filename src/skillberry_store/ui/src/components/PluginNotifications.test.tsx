// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PluginNotifications } from './PluginNotifications';
import type { Plugin } from '@/types';

const mockFetch = vi.fn();
global.fetch = mockFetch;

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const PLUGIN_NO_NOTIFICATIONS: Plugin = {
  slug: 'other',
  name: 'Other Plugin',
  enabled: true,
  description: 'test plugin',
  version: '1.0.0',
  plugin_type: 'evaluator',
  has_router: false,
  has_cli: false,
  has_ui: false,
};

const PLUGIN_WITH_NOTIFICATIONS: Plugin = {
  slug: 'dedupe',
  name: 'Skill Deduplicator',
  enabled: true,
  description: 'detect duplicates',
  version: '0.1.0',
  plugin_type: 'evaluator',
  has_router: true,
  has_cli: false,
  has_ui: true,
  ui_config: {
    icon: '',
    color: '#C9190B',
    actions: [],
    notifications: {
      poll_endpoint: '/api/plugins/dedupe/decisions',
      item_schema: {
        title_field: 'skill_name',
        body_fields: ['duplicates'],
        actions: [
          {
            label: 'Keep',
            endpoint: '/api/plugins/dedupe/decisions/{uuid}/keep',
            method: 'POST',
            variant: 'primary',
          },
          {
            label: 'Delete',
            endpoint: '/api/plugins/dedupe/decisions/{uuid}/delete',
            method: 'POST',
            variant: 'danger',
          },
        ],
      },
    },
  },
};

describe('PluginNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when plugins have no notifications config', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([PLUGIN_NO_NOTIFICATIONS]),
    });

    const { container } = render(<PluginNotifications />, { wrapper });

    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith('/api/plugins/')
    );
    expect(container.querySelector('[role="dialog"]')).toBeNull();
  });

  it('renders nothing when decisions list is empty', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([PLUGIN_WITH_NOTIFICATIONS]),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      });

    const { container } = render(<PluginNotifications />, { wrapper });

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
    expect(container.querySelector('[role="dialog"]')).toBeNull();
  });

  it('renders modal with skill name when a pending decision exists', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([PLUGIN_WITH_NOTIFICATIONS]),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve([
            {
              uuid: 'skill-123',
              skill_name: 'My Web Searcher',
              duplicates: [{ name: 'existing searcher', reason: 'same purpose' }],
              detected_at: '2026-06-18T10:00:00Z',
            },
          ]),
      });

    render(<PluginNotifications />, { wrapper });

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
      expect(screen.getByText(/My Web Searcher/)).toBeDefined();
    });
  });

  it('renders Keep and Delete buttons', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([PLUGIN_WITH_NOTIFICATIONS]),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve([
            {
              uuid: 'skill-123',
              skill_name: 'My Skill',
              duplicates: [{ name: 'other', reason: 'same' }],
              detected_at: '2026-06-18T10:00:00Z',
            },
          ]),
      });

    render(<PluginNotifications />, { wrapper });

    await waitFor(() => screen.getByRole('dialog'));
    expect(screen.getByText('Keep')).toBeDefined();
    expect(screen.getByText('Delete')).toBeDefined();
  });

  it('calls keep endpoint with uuid substituted when Keep is clicked', async () => {
    const decision = {
      uuid: 'skill-abc',
      skill_name: 'My Skill',
      duplicates: [{ name: 'other', reason: 'same' }],
      detected_at: '2026-06-18T10:00:00Z',
    };

    mockFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([PLUGIN_WITH_NOTIFICATIONS]) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([decision]) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });

    render(<PluginNotifications />, { wrapper });
    await waitFor(() => screen.getByRole('dialog'));

    await userEvent.click(screen.getByText('Keep'));

    await waitFor(() => {
      const keepCall = mockFetch.mock.calls.find(
        (c) => c[0] === '/api/plugins/dedupe/decisions/skill-abc/keep'
      );
      expect(keepCall).toBeDefined();
      expect(keepCall![1].method).toBe('POST');
    });
  });

  it('calls delete endpoint with uuid substituted when Delete is clicked', async () => {
    const decision = {
      uuid: 'skill-xyz',
      skill_name: 'My Skill',
      duplicates: [{ name: 'other', reason: 'same' }],
      detected_at: '2026-06-18T10:00:00Z',
    };

    mockFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([PLUGIN_WITH_NOTIFICATIONS]) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([decision]) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });

    render(<PluginNotifications />, { wrapper });
    await waitFor(() => screen.getByRole('dialog'));

    await userEvent.click(screen.getByText('Delete'));

    await waitFor(() => {
      const deleteCall = mockFetch.mock.calls.find(
        (c) => c[0] === '/api/plugins/dedupe/decisions/skill-xyz/delete'
      );
      expect(deleteCall).toBeDefined();
    });
  });
});
