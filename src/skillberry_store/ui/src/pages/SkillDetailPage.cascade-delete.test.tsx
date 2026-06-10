import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SkillDetailPage } from './SkillDetailPage';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useParams: () => ({ uuid: 'sk1' }), useNavigate: () => vi.fn() };
});

const mockDelete = vi.hoisted(() => vi.fn().mockResolvedValue({ message: 'ok' }));

vi.mock('@/services/api', () => ({
  skillsApi: {
    get: vi.fn().mockResolvedValue({
      uuid: 'sk1', name: 'myskill', description: 'desc',
      tools: [{ uuid: 't1', name: 'tool1' }],
      snippets: [],
      tags: [], version: '', extra: {},
    }),
    delete: mockDelete,
    search: vi.fn().mockResolvedValue([]),
  },
  toolsApi: { list: vi.fn().mockResolvedValue([]) },
  snippetsApi: { list: vi.fn().mockResolvedValue([]) },
}));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <BrowserRouter>
      <QueryClientProvider client={qc}>
        <SkillDetailPage />
      </QueryClientProvider>
    </BrowserRouter>
  );
}

describe('SkillDetailPage cascade delete modal', () => {
  beforeEach(() => { mockDelete.mockClear(); });

  async function openModal() {
    renderPage();
    // The Delete button is only rendered after skill data loads — wait for it
    const deleteBtn = await screen.findByRole('button', { name: /^delete$/i });
    await userEvent.click(deleteBtn);
    return screen.findByRole('dialog');
  }

  it('shows both checkboxes checked by default', async () => {
    const modal = await openModal();
    expect(within(modal).getByRole('checkbox', { name: /delete associated tools/i })).toBeChecked();
    expect(within(modal).getByRole('checkbox', { name: /delete associated snippets/i })).toBeChecked();
  });

  it('shows the shared-skills note', async () => {
    const modal = await openModal();
    expect(within(modal).getByText(/shared with other skills will not be deleted/i)).toBeInTheDocument();
  });

  it('calls skillsApi.delete with both flags when confirmed', async () => {
    const modal = await openModal();
    await userEvent.click(within(modal).getByRole('button', { name: /^delete$/i }));
    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('sk1', { deleteTools: true, deleteSnippets: true });
    });
  });

  it('calls skillsApi.delete with deleteTools: false when that checkbox is unchecked', async () => {
    const modal = await openModal();
    await userEvent.click(within(modal).getByRole('checkbox', { name: /delete associated tools/i }));
    await userEvent.click(within(modal).getByRole('button', { name: /^delete$/i }));
    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('sk1', { deleteTools: false, deleteSnippets: true });
    });
  });
});
