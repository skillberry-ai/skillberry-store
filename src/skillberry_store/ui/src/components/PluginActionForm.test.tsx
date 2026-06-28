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

  it('keeps the result and does not time out once the job is ready', async () => {
    // Job is already ready; the rendered markdown must survive past the timeout
    // window (regression: a stale deadline used to wipe the completed result).
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ready', summary_md: '# Hello world' }),
    });
    const onSubmit = vi.fn().mockResolvedValue(PENDING_RESULT);
    const action: PluginAction = {
      ...ASYNC_ACTION,
      async_action: {
        ...ASYNC_ACTION.async_action!,
        result_markdown_field: 'summary_md',
        poll_interval_ms: 20,
        timeout_ms: 60,
      },
    };

    renderForm(action, onSubmit);
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));

    await waitFor(() => expect(screen.getByText('Hello world')).toBeDefined());
    // Wait well past timeout_ms — the result must remain and no timeout alert appears.
    await new Promise((r) => setTimeout(r, 150));
    expect(screen.queryByText(/Lost track of the kettle/i)).toBeNull();
    expect(screen.getByText('Hello world')).toBeDefined();
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

  it('prefills sibling fields when a preset is selected', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => [
        { id: 'opt1', label: 'Opt 1', prompt: 'hello prompt', skills: ['a', 'b'] },
      ],
    });
    const action = {
      label: 'Run preset',
      endpoint: '/plugins/ask-runspace/run',
      method: 'POST',
      params_schema: {
        type: 'object',
        properties: {
          preset_id: {
            type: 'string',
            'x-options-from': '/x/presets',
            'x-option-label': 'label',
            'x-option-value': 'id',
            'x-prefill': { request: 'prompt', skills: 'skills' },
          },
          request: { type: 'string', format: 'textarea' },
          skills: { type: 'array' },
        },
      },
    } as any;

    renderForm(action, async () => ({ success: true }));

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Opt 1' })).toBeDefined();
    });

    fireEvent.change(document.getElementById('preset_id') as HTMLSelectElement, {
      target: { value: 'opt1' },
    });

    await waitFor(() => {
      expect((document.getElementById('request') as HTMLTextAreaElement).value).toBe('hello prompt');
    });
    // The array `skills` field now renders as a list: the two values "a" and "b"
    // appear as separate inputs.
    const skillsGroup = document.getElementById('skills')!.closest('[class*="c-form__group"]')!;
    const skillInputs = Array.from(
      skillsGroup.querySelectorAll('input')
    ) as HTMLInputElement[];
    const values = skillInputs.map((i) => i.value);
    expect(values).toContain('a');
    expect(values).toContain('b');
  });

  it('prefills an object field as JSON and submits it parsed back to an object', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: 'optimize',
          label: 'Optimize',
          prompt: 'optimize it',
          skills: [],
          env: { CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: '1' },
        },
      ],
    });
    const onSubmit = vi.fn().mockResolvedValue({ success: true } as PluginActionResult);
    const action = {
      label: 'Run preset',
      endpoint: '/plugins/ask-runspace/run',
      method: 'POST',
      params_schema: {
        type: 'object',
        properties: {
          preset_id: {
            type: 'string',
            'x-options-from': '/x/presets',
            'x-option-label': 'label',
            'x-option-value': 'id',
            'x-prefill': { request: 'prompt', skills: 'skills', agent_env: 'env' },
          },
          request: { type: 'string', format: 'textarea' },
          skills: { type: 'array' },
          agent_env: { type: 'object', title: 'Environment overrides (optional)' },
        },
      },
    } as any;

    renderForm(action, onSubmit);

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Optimize' })).toBeDefined();
    });

    fireEvent.change(document.getElementById('preset_id') as HTMLSelectElement, {
      target: { value: 'optimize' },
    });

    // The object field renders as a textarea prefilled with the env as JSON.
    await waitFor(() => {
      const env = document.getElementById('agent_env') as HTMLTextAreaElement;
      expect(env.tagName).toBe('TEXTAREA');
      expect(env.value).toContain('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS');
    });

    // Submitting parses the JSON back into an object.
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ agent_env: { CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: '1' } })
      );
    });
  });

  it('renders an array field as an add/remove list', () => {
    const action = {
      label: 'Tag it',
      endpoint: '/plugins/ask-runspace/run',
      method: 'POST',
      params_schema: {
        type: 'object',
        properties: {
          tags: { type: 'array', title: 'Tags' },
        },
      },
    } as any;

    renderForm(action, async () => ({ success: true }));

    const group = document.getElementById('tags')!.closest('[class*="c-form__group"]')!;
    const inputsOf = () => Array.from(group.querySelectorAll('input')) as HTMLInputElement[];

    // An "Add" control exists, and there is initially one (empty) row.
    const addButton = screen.getByRole('button', { name: 'Add' });
    expect(addButton).toBeDefined();
    expect(inputsOf().length).toBe(1);

    // Type into the first input.
    fireEvent.change(inputsOf()[0], { target: { value: 'first' } });
    expect(inputsOf()[0].value).toBe('first');

    // Clicking Add appends an extra input.
    fireEvent.click(addButton);
    expect(inputsOf().length).toBe(2);

    fireEvent.change(inputsOf()[1], { target: { value: 'second' } });
    expect(inputsOf()[1].value).toBe('second');

    // Removing a row drops the input count.
    fireEvent.click(screen.getByRole('button', { name: 'Remove Tags item 2' }));
    expect(inputsOf().length).toBe(1);
  });

  it('uploads a selected skills folder and submits the returned token', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: { upload_id: 'up-123', file_count: 1 } }),
    });
    const onSubmit = vi.fn().mockResolvedValue({ success: true } as PluginActionResult);
    const action = {
      label: 'Run task',
      endpoint: '/plugins/ask-runspace/run',
      method: 'POST',
      params_schema: {
        type: 'object',
        properties: {
          skills_upload_id: {
            type: 'string',
            title: 'Skills folder',
            format: 'directory-upload',
            'x-upload-endpoint': '/api/plugins/ask-runspace/upload-skills',
          },
        },
      },
    } as any;

    renderForm(action, onSubmit);

    // The drop zone is shown instead of a text input.
    expect(screen.getByText(/Drag-drop a skills folder/i)).toBeDefined();

    const input = document.getElementById('skills_upload_id-dirinput') as HTMLInputElement;
    const file = new File(['# A'], 'SKILL.md', { type: 'text/markdown' });
    Object.defineProperty(file, 'webkitRelativePath', { value: 'my-skills/skill-a/SKILL.md' });
    fireEvent.change(input, { target: { files: [file] } });

    // It uploads to the field's endpoint and reports the folder as ready.
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/plugins/ask-runspace/upload-skills',
        expect.objectContaining({ method: 'POST' })
      );
      expect(screen.getByText(/file\(s\) ready/i)).toBeDefined();
    });

    // Submitting sends the returned upload token as the field value.
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ skills_upload_id: 'up-123' }));
    });
  });

  it('renders an external session link on success when result_link.field is present', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ready', session_url: 'http://localhost:6767/ui/sessions/s1' }),
    });
    const onSubmit = vi.fn().mockResolvedValue(PENDING_RESULT);
    const action: PluginAction = {
      ...ASYNC_ACTION,
      async_action: {
        ...ASYNC_ACTION.async_action!,
        result_link: { field: 'session_url', label: 'Open session in Runspace ↗' },
      },
    };

    renderForm(action, onSubmit);
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));

    await waitFor(() => {
      const link = screen.getByRole('link', { name: /Open session in Runspace/i }) as HTMLAnchorElement;
      expect(link.href).toContain('/ui/sessions/s1');
      expect(link.target).toBe('_blank');
    });
  });

  it('shows the result_link as soon as it appears in the pending status payload', async () => {
    // Status stays "pending" but already carries the session URL.
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'pending', session_url: 'http://localhost:6767/ui/sessions/abc' }),
    });
    const onSubmit = vi.fn().mockResolvedValue(PENDING_RESULT);
    const action: PluginAction = {
      ...ASYNC_ACTION,
      async_action: {
        ...ASYNC_ACTION.async_action!,
        result_link: { field: 'session_url', label: 'Open session in Runspace ↗' },
      },
    };

    renderForm(action, onSubmit);
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));

    await waitFor(() => {
      const link = screen.getByRole('link', { name: /Open session in Runspace/i }) as HTMLAnchorElement;
      expect(link.href).toContain('/ui/sessions/abc');
    });
    // Still pending — the link shows before completion.
    expect(screen.getByText(/Brewing your coffee/i)).toBeDefined();
  });

  it('shows an x-visible-when field only when its controlling box is ticked', () => {
    const action = {
      label: 'Run task',
      endpoint: '/x/run',
      method: 'POST',
      params_schema: {
        type: 'object',
        properties: {
          use_server: { type: 'boolean', title: 'Use server' },
          url: {
            type: 'string',
            title: 'URL',
            default: 'http://localhost:6767',
            'x-visible-when': { field: 'use_server', equals: true },
          },
        },
      },
    } as any;

    renderForm(action, async () => ({ success: true }));

    // The dependent field is hidden until the controlling checkbox is ticked.
    expect(document.getElementById('url')).toBeNull();
    fireEvent.click(document.getElementById('use_server') as HTMLInputElement);
    expect(document.getElementById('url')).not.toBeNull();
  });

  it('submits a prefilled default even when the field is left untouched', async () => {
    const onSubmit = vi.fn().mockResolvedValue({ success: true } as PluginActionResult);
    const action = {
      label: 'Run task',
      endpoint: '/x/run',
      method: 'POST',
      params_schema: {
        type: 'object',
        properties: {
          mcp_servers: {
            type: 'string',
            format: 'textarea',
            title: 'MCP servers',
            default: '{"skillberry-store": {"type": "sse", "url": "http://localhost:8000/control_sse"}}',
          },
        },
      },
    } as any;

    renderForm(action, onSubmit);
    // Submit without editing the prefilled textarea.
    fireEvent.click(screen.getByRole('button', { name: /Execute/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          mcp_servers: '{"skillberry-store": {"type": "sse", "url": "http://localhost:8000/control_sse"}}',
        })
      );
    });
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
