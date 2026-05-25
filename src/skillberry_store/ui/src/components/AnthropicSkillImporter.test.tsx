// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AnthropicSkillImporter } from './AnthropicSkillImporter';

const mockListSkills = vi.fn();

vi.mock('@/services/api', () => ({
  skillsApi: {
    list: (...args: unknown[]) => mockListSkills(...args),
  },
}));

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe('AnthropicSkillImporter batch import', () => {
  const onClose = vi.fn();
  const onImportComplete = vi.fn();
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockListSkills.mockResolvedValue([]);
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });

  const renderComponent = () =>
    render(
      <AnthropicSkillImporter
        isOpen
        onClose={onClose}
        onImportComplete={onImportComplete}
      />
    );

  async function enableFolderBatchMode() {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => {
      expect(mockListSkills).toHaveBeenCalled();
    });

    await user.click(screen.getByRole('button', { name: /local folder/i }));
    const batchModeCheckbox = screen.getByLabelText(
      /import multiple skills from subdirectories/i
    );
    await user.click(batchModeCheckbox);

    const folderInput = screen.getByPlaceholderText('/path/to/skill/folder');
    await user.clear(folderInput);
    await user.type(folderInput, '/tmp/anthropic-skills');

    return { user, batchModeCheckbox, folderInput };
  }

  it('renders the batch mode help text and disables batch mode for zip imports', async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => {
      expect(mockListSkills).toHaveBeenCalled();
    });

    expect(
      screen.getByText(/scan for subdirectories containing SKILL\.md files/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /zip file/i }));

    expect(
      screen.getByLabelText(/import multiple skills from subdirectories/i)
    ).toBeDisabled();
  });

  it('imports each detected local skill sequentially and shows aggregate reviewer-visible results', async () => {
    const { user } = await enableFolderBatchMode();

    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          subdirectories: [
            { name: 'alpha-skill', path: '/tmp/anthropic-skills/alpha-skill', has_skill_md: true },
            { name: 'notes', path: '/tmp/anthropic-skills/notes', has_skill_md: false },
            { name: 'beta-skill', path: '/tmp/anthropic-skills/beta-skill', has_skill_md: true },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'alpha_skill',
          tools_created: 2,
          snippets_created: 1,
          ignored_files: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'beta_skill',
          tools_created: 1,
          snippets_created: 3,
          ignored_files: ['README.md'],
        }),
      });

    await user.click(screen.getByRole('button', { name: /^import$/i }));

    await waitFor(() => {
      expect(screen.getByText(/batch import completed: 2\/2 skills imported successfully/i)).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/admin/list-subdirectories',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: '/tmp/anthropic-skills' }),
      })
    );

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/skills/import-anthropic',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );

    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/skills/import-anthropic',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );

    const secondBody = fetchMock.mock.calls[1][1].body as FormData;
    const thirdBody = fetchMock.mock.calls[2][1].body as FormData;

    expect(secondBody.get('source_type')).toBe('folder');
    expect(secondBody.get('folder_path')).toBe('/tmp/anthropic-skills/alpha-skill');
    expect(secondBody.get('snippet_mode')).toBe('file');
    expect(secondBody.get('treat_all_as_documents')).toBe('false');
    expect(secondBody.getAll('tags')).toEqual(['namespace:default']);

    expect(thirdBody.get('folder_path')).toBe('/tmp/anthropic-skills/beta-skill');

    expect(screen.getByText(/total: 3 tools, 4 snippets\./i)).toBeInTheDocument();
    expect(screen.getByText(/detailed results:/i)).toBeInTheDocument();
    expect(screen.getByText('alpha_skill')).toBeInTheDocument();
    expect(screen.getByText('beta_skill')).toBeInTheDocument();
    expect(screen.getByText(/2 tool\(s\), 1 snippet\(s\)/i)).toBeInTheDocument();
    expect(screen.getByText(/1 tool\(s\), 3 snippet\(s\)/i)).toBeInTheDocument();
    expect(onImportComplete).toHaveBeenCalledTimes(1);
  });

  it('shows mixed batch results when one skill import fails and another succeeds', async () => {
    const { user } = await enableFolderBatchMode();

    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          subdirectories: [
            { name: 'broken-skill', path: '/tmp/anthropic-skills/broken-skill', has_skill_md: true },
            { name: 'working-skill', path: '/tmp/anthropic-skills/working-skill', has_skill_md: true },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: false,
        text: async () => 'invalid SKILL.md metadata',
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'working_skill',
          tools_created: 1,
          snippets_created: 0,
          ignored_files: [],
        }),
      });

    await user.click(screen.getByRole('button', { name: /^import$/i }));

    await waitFor(() => {
      expect(screen.getByText(/batch import completed: 1\/2 skills imported successfully/i)).toBeInTheDocument();
    });

    const alert = screen.getByText(/batch import completed: 1\/2 skills imported successfully/i).closest('[class]');
    expect(screen.getByText('working_skill')).toBeInTheDocument();
    expect(screen.getByText(/failed to import broken-skill: invalid SKILL\.md metadata/i)).toBeInTheDocument();
    expect(screen.getByText('Skill 1')).toBeInTheDocument();
    expect(alert).toBeTruthy();
  });

  it('disables the batch mode toggle while batch import is running', async () => {
    const { user } = await enableFolderBatchMode();

    const deferredList = createDeferred<{
      ok: boolean;
      json: () => Promise<{
        subdirectories: Array<{ name: string; path: string; has_skill_md: boolean }>;
      }>;
    }>();

    fetchMock.mockReturnValueOnce(deferredList.promise);

    await user.click(screen.getByRole('button', { name: /^import$/i }));

    const batchModeCheckbox = screen.getByLabelText(
      /import multiple skills from subdirectories/i
    );
    expect(batchModeCheckbox).toBeDisabled();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    deferredList.resolve({
      ok: true,
      json: async () => ({
        subdirectories: [],
      }),
    });

    await waitFor(() => {
      expect(screen.getByText(/no subdirectories with SKILL\.md files found/i)).toBeInTheDocument();
    });
  });

  it('resets batch-specific form state after completing an import and closing the modal', async () => {
    const { user } = await enableFolderBatchMode();

    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          subdirectories: [
            { name: 'alpha-skill', path: '/tmp/anthropic-skills/alpha-skill', has_skill_md: true },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'alpha_skill',
          tools_created: 1,
          snippets_created: 1,
          ignored_files: [],
        }),
      });

    await user.click(screen.getByRole('button', { name: /^import$/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /done/i }));
    expect(onClose).toHaveBeenCalledTimes(1);

    renderComponent();

    await waitFor(() => {
      expect(mockListSkills).toHaveBeenCalled();
    });

    await user.click(screen.getByRole('button', { name: /local folder/i }));

    expect(
      screen.getByLabelText(/import multiple skills from subdirectories/i)
    ).not.toBeChecked();
    expect(screen.getByPlaceholderText('/path/to/skill/folder')).toHaveValue('');
    expect(screen.queryByText(/detailed results:/i)).not.toBeInTheDocument();
  });

  it('applies selected namespaces to each imported skill request', async () => {
    const { user } = await enableFolderBatchMode();

    const namespaceToggle = screen.getByRole('button', {
      name: /select or add namespace/i,
    });
    await user.click(namespaceToggle);

    const namespaceInput = screen.getByPlaceholderText(/type to search or add new/i);
    await user.type(namespaceInput, 'frontend-batch');
    await user.keyboard('{Enter}');

    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          subdirectories: [
            { name: 'alpha-skill', path: '/tmp/anthropic-skills/alpha-skill', has_skill_md: true },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'alpha_skill',
          tools_created: 1,
          snippets_created: 0,
          ignored_files: [],
        }),
      });

    await user.click(screen.getByRole('button', { name: /^import$/i }));

    await waitFor(() => {
      expect(screen.getByText(/batch import completed: 1\/1 skills imported successfully/i)).toBeInTheDocument();
    });

    const importBody = fetchMock.mock.calls[1][1].body as FormData;
    expect(importBody.getAll('tags')).toEqual(['namespace:frontend-batch']);
    expect(within(screen.getByText(/detailed results:/i).closest('div') as HTMLElement).getByText('alpha_skill')).toBeInTheDocument();
  });
});
