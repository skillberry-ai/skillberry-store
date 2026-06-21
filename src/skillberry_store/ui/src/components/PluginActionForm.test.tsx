// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PluginActionForm } from './PluginActionForm';
import type { PluginAction, PluginActionResult } from '@/types';

// A deliberately non-"simulate" plugin action: proves the form has NO plugin-specific
// strings or protocol baked in — every user-facing label comes from async_action.labels.
const ASYNC_ACTION: PluginAction = {
  label: 'Brew coffee',
  endpoint: '/api/plugins/coffee/brew',
  method: 'POST',
  params_schema: { type: 'object', properties: {} },
  async_action: {
    status_endpoint: '/api/plugins/coffee/status/{job_id}',
    poll_interval_ms: 20,
    timeout_ms: 10_000,
    labels: {
      pending: 'Brewing your coffee…',
      ready: 'Coffee is ready',
      failed: 'Brew failed',
      timeout: 'Lost track of the kettle',
      done: 'Grab it',
    },
  },
};

const PENDING_RESULT: PluginActionResult = {
  success: true,
  message: 'Brew started',
  data: { job_id: 'job-xyz', status: 'pending' },
};

const mockFetch = vi.fn();
global.fetch = mockFetch as unknown as typeof fetch;

function renderForm(
  action: PluginAction,
  onSubmit: () => Promise<PluginActionResult>,
  onClose = vi.fn()
) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <PluginActionForm
        action={action}
        pluginName="coffee"
        isOpen={true}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </QueryClientProvider>
  );
}

describe('PluginActionForm — generic async actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the plugin-supplied pending label and disables the button while polling', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: 'pending' }) });
    const onSubmit = vi.fn().mockResolvedValue(PENDING_RESULT);

    renderForm(ASYNC_ACTION, onSubmit);
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));

    await waitFor(() => {
      expect(screen.getByText(/Brewing your coffee/i)).toBeDefined();
    });
    // The submit button is busy/disabled while a job is pending.
    const submit = screen.getAllByRole('button').find((b) => (b as HTMLButtonElement).disabled);
    expect(submit).toBeDefined();
  });

  it('polls the interpolated status endpoint and shows the ready label + done button', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ready', sim_vmcp_uuid: 'x-1' }),
    });
    const onSubmit = vi.fn().mockResolvedValue(PENDING_RESULT);

    renderForm(ASYNC_ACTION, onSubmit);
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));

    await waitFor(() => {
      expect(screen.getByText(/Coffee is ready/i)).toBeDefined();
    });
    expect(mockFetch).toHaveBeenCalledWith('/api/plugins/coffee/status/job-xyz');
    const done = screen.getByRole('button', { name: /Grab it/i });
    expect((done as HTMLButtonElement).disabled).toBe(false);
  });

  it('shows the failed label with the API detail and restores the submit button', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'failed', detail: 'kettle exploded' }),
    });
    const onSubmit = vi.fn().mockResolvedValue(PENDING_RESULT);

    renderForm(ASYNC_ACTION, onSubmit);
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));

    await waitFor(() => {
      expect(screen.getByText(/Brew failed/i)).toBeDefined();
      expect(screen.getByText(/kettle exploded/i)).toBeDefined();
    });
    expect(screen.getByRole('button', { name: /Execute/i })).toBeDefined();
  });

  it('shows the timeout label when the job never resolves', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ status: 'pending' }) });
    const onSubmit = vi.fn().mockResolvedValue(PENDING_RESULT);
    const action: PluginAction = {
      ...ASYNC_ACTION,
      async_action: { ...ASYNC_ACTION.async_action!, poll_interval_ms: 20, timeout_ms: 60 },
    };

    renderForm(action, onSubmit);
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));

    await waitFor(
      () => {
        expect(screen.getByText(/Lost track of the kettle/i)).toBeDefined();
      },
      { timeout: 2000 }
    );
  });

  it('renders a textarea for format: textarea fields', () => {
    const action = {
      label: 'Run task',
      endpoint: '/plugins/ask-runspace/run',
      method: 'POST',
      params_schema: {
        type: 'object',
        properties: { request: { type: 'string', format: 'textarea', title: 'Your request' } },
        required: ['request'],
      },
    } as any;
    renderForm(action, async () => ({ success: true }));
    expect(document.querySelector('textarea')).toBeTruthy();
  });

  it('behaves synchronously for actions without async_action (no polling)', async () => {
    const syncAction: PluginAction = {
      label: 'Plain action',
      endpoint: '/api/plugins/coffee/plain',
      method: 'POST',
      params_schema: { type: 'object', properties: {} },
    };
    const onSubmit = vi
      .fn()
      .mockResolvedValue({ success: true, message: 'All done' } as PluginActionResult);

    renderForm(syncAction, onSubmit);
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));

    await waitFor(() => expect(screen.getByText(/All done/i)).toBeDefined());
    expect(mockFetch).not.toHaveBeenCalled();
  });
});
