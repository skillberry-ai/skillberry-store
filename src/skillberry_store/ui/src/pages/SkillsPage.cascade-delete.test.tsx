import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SkillsPage } from './SkillsPage';

const mockDelete = vi.hoisted(() => vi.fn().mockResolvedValue({ message: 'ok' }));

vi.mock('@/services/api', () => ({
  skillsApi: {
    list: vi.fn().mockResolvedValue([
      { uuid: 'sk1', name: 'skill-one', description: 'desc', tools: [], snippets: [], tags: [] },
    ]),
    delete: mockDelete,
    search: vi.fn().mockResolvedValue([]),
  },
  toolsApi: { list: vi.fn().mockResolvedValue([]) },
  snippetsApi: { list: vi.fn().mockResolvedValue([]) },
}));

vi.mock('../components/AnthropicSkillImporter', () => ({
  AnthropicSkillImporter: () => null,
}));

vi.mock('../components/SkillCardView', () => ({
  SkillCardView: ({ onSelectSkill }: { onSelectSkill: (name: string, selected: boolean) => void }) => (
    <button data-testid="select-skill" onClick={() => onSelectSkill('skill-one', true)}>
      skill-one
    </button>
  ),
}));

vi.mock('../components/SkillListView', () => ({ SkillListView: () => null }));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <BrowserRouter>
      <QueryClientProvider client={qc}>
        <SkillsPage />
      </QueryClientProvider>
    </BrowserRouter>
  );
}

describe('SkillsPage cascade delete modal', () => {
  beforeEach(() => { mockDelete.mockClear(); });

  async function openDeleteModal() {
    renderPage();
    await userEvent.click(await screen.findByTestId('select-skill'));
    await userEvent.click(screen.getByRole('button', { name: 'Delete (1)' }));
    return screen.findByRole('dialog');
  }

  it('shows both checkboxes checked by default', async () => {
    const modal = await openDeleteModal();
    expect(within(modal).getByRole('checkbox', { name: /delete associated tools/i })).toBeChecked();
    expect(within(modal).getByRole('checkbox', { name: /delete associated snippets/i })).toBeChecked();
  });

  it('shows the shared-skills note', async () => {
    const modal = await openDeleteModal();
    expect(within(modal).getByText(/shared with other skills will not be deleted/i)).toBeInTheDocument();
  });

  it('calls skillsApi.delete with both flags when confirmed', async () => {
    const modal = await openDeleteModal();
    await userEvent.click(within(modal).getByRole('button', { name: /^delete$/i }));
    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('skill-one', { deleteTools: true, deleteSnippets: true });
    });
  });
});
