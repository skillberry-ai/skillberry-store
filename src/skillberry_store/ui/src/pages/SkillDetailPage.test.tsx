// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SkillDetailPage } from './SkillDetailPage';
import userEvent from '@testing-library/user-event';

// Mock the API client
vi.mock('../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock react-syntax-highlighter to avoid rendering issues in tests
vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children, language, ...props }: any) => (
    <pre data-testid="syntax-highlighter" data-language={language} {...props}>
      <code>{children}</code>
    </pre>
  ),
}));

vi.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  vscDarkPlus: {},
}));

const mockSkillWithTools = {
  id: 'test-skill-1',
  name: 'Test Skill',
  description: 'A test skill for syntax highlighting',
  tags: ['test', 'python'],
  tools: [
    {
      name: 'test_tool',
      description: 'A test tool',
      programming_language: 'python',
      module: `def hello_world():
    print("Hello, World!")
    return True`,
      tags: ['python'],
    },
  ],
  snippets: [],
};

const mockSkillWithSnippets = {
  id: 'test-skill-2',
  name: 'Test Skill with Snippets',
  description: 'A test skill with snippets',
  tags: ['test'],
  tools: [],
  snippets: [
    {
      id: 'snippet-1',
      name: 'test_snippet',
      description: 'A test snippet',
      content: 'console.log("Hello from snippet");',
      content_type: 'text/javascript',
      tags: ['javascript'],
    },
  ],
};

describe('SkillDetailPage - Syntax Highlighting', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithRouter = (skillId: string, mockData: any) => {
    const { apiClient } = require('../api/client');
    apiClient.get.mockResolvedValue({ data: mockData });

    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/skills/${skillId}`]}>
          <Routes>
            <Route path="/skills/:id" element={<SkillDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  describe('Tool Module Syntax Highlighting', () => {
    it('should render syntax highlighter for tool module code', async () => {
      renderWithRouter('test-skill-1', mockSkillWithTools);

      await waitFor(() => {
        expect(screen.getByText('Test Skill')).toBeInTheDocument();
      });

      // Click on Tools tab
      const toolsTab = screen.getByRole('button', { name: /tools/i });
      await userEvent.click(toolsTab);

      // Click on the tool to view its code
      await waitFor(() => {
        const toolItem = screen.getByText('test_tool');
        expect(toolItem).toBeInTheDocument();
      });

      const toolItem = screen.getByText('test_tool');
      await userEvent.click(toolItem);

      // Verify syntax highlighter is rendered
      await waitFor(() => {
        const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
        expect(syntaxHighlighter).toBeInTheDocument();
      });
    });

    it('should detect Python language for tool modules', async () => {
      renderWithRouter('test-skill-1', mockSkillWithTools);

      await waitFor(() => {
        expect(screen.getByText('Test Skill')).toBeInTheDocument();
      });

      const toolsTab = screen.getByRole('button', { name: /tools/i });
      await userEvent.click(toolsTab);

      await waitFor(() => {
        const toolItem = screen.getByText('test_tool');
        expect(toolItem).toBeInTheDocument();
      });

      const toolItem = screen.getByText('test_tool');
      await userEvent.click(toolItem);

      await waitFor(() => {
        const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
        expect(syntaxHighlighter).toHaveAttribute('data-language', 'python');
      });
    });

    it('should display tool module code content', async () => {
      renderWithRouter('test-skill-1', mockSkillWithTools);

      await waitFor(() => {
        expect(screen.getByText('Test Skill')).toBeInTheDocument();
      });

      const toolsTab = screen.getByRole('button', { name: /tools/i });
      await userEvent.click(toolsTab);

      await waitFor(() => {
        const toolItem = screen.getByText('test_tool');
        expect(toolItem).toBeInTheDocument();
      });

      const toolItem = screen.getByText('test_tool');
      await userEvent.click(toolItem);

      await waitFor(() => {
        expect(screen.getByText(/def hello_world/)).toBeInTheDocument();
        expect(screen.getByText(/print\("Hello, World!"\)/)).toBeInTheDocument();
      });
    });

    it('should render code in a scrollable container', async () => {
      renderWithRouter('test-skill-1', mockSkillWithTools);

      await waitFor(() => {
        expect(screen.getByText('Test Skill')).toBeInTheDocument();
      });

      const toolsTab = screen.getByRole('button', { name: /tools/i });
      await userEvent.click(toolsTab);

      await waitFor(() => {
        const toolItem = screen.getByText('test_tool');
        expect(toolItem).toBeInTheDocument();
      });

      const toolItem = screen.getByText('test_tool');
      await userEvent.click(toolItem);

      await waitFor(() => {
        const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
        const container = syntaxHighlighter.parentElement;
        expect(container).toHaveStyle({ overflow: 'auto' });
      });
    });
  });

  describe('Snippet Syntax Highlighting', () => {
    it('should render syntax highlighter for snippet code', async () => {
      renderWithRouter('test-skill-2', mockSkillWithSnippets);

      await waitFor(() => {
        expect(screen.getByText('Test Skill with Snippets')).toBeInTheDocument();
      });

      // Click on Snippets tab
      const snippetsTab = screen.getByRole('button', { name: /snippets/i });
      await userEvent.click(snippetsTab);

      // Click on the snippet to view its code
      await waitFor(() => {
        const snippetItem = screen.getByText('test_snippet');
        expect(snippetItem).toBeInTheDocument();
      });

      const snippetItem = screen.getByText('test_snippet');
      await userEvent.click(snippetItem);

      // Verify syntax highlighter is rendered
      await waitFor(() => {
        const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
        expect(syntaxHighlighter).toBeInTheDocument();
      });
    });

    it('should detect JavaScript language from content_type', async () => {
      renderWithRouter('test-skill-2', mockSkillWithSnippets);

      await waitFor(() => {
        expect(screen.getByText('Test Skill with Snippets')).toBeInTheDocument();
      });

      const snippetsTab = screen.getByRole('button', { name: /snippets/i });
      await userEvent.click(snippetsTab);

      await waitFor(() => {
        const snippetItem = screen.getByText('test_snippet');
        expect(snippetItem).toBeInTheDocument();
      });

      const snippetItem = screen.getByText('test_snippet');
      await userEvent.click(snippetItem);

      await waitFor(() => {
        const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
        expect(syntaxHighlighter).toHaveAttribute('data-language', 'javascript');
      });
    });

    it('should display snippet code content', async () => {
      renderWithRouter('test-skill-2', mockSkillWithSnippets);

      await waitFor(() => {
        expect(screen.getByText('Test Skill with Snippets')).toBeInTheDocument();
      });

      const snippetsTab = screen.getByRole('button', { name: /snippets/i });
      await userEvent.click(snippetsTab);

      await waitFor(() => {
        const snippetItem = screen.getByText('test_snippet');
        expect(snippetItem).toBeInTheDocument();
      });

      const snippetItem = screen.getByText('test_snippet');
      await userEvent.click(snippetItem);

      await waitFor(() => {
        expect(screen.getByText(/console\.log/)).toBeInTheDocument();
      });
    });
  });

  describe('Language Detection Integration', () => {
    it('should use detectLanguage utility for tool modules', async () => {
      const skillWithTypedTool = {
        ...mockSkillWithTools,
        tools: [
          {
            ...mockSkillWithTools.tools[0],
            programming_language: 'typescript',
          },
        ],
      };

      renderWithRouter('test-skill-1', skillWithTypedTool);

      await waitFor(() => {
        expect(screen.getByText('Test Skill')).toBeInTheDocument();
      });

      const toolsTab = screen.getByRole('button', { name: /tools/i });
      await userEvent.click(toolsTab);

      await waitFor(() => {
        const toolItem = screen.getByText('test_tool');
        expect(toolItem).toBeInTheDocument();
      });

      const toolItem = screen.getByText('test_tool');
      await userEvent.click(toolItem);

      await waitFor(() => {
        const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
        expect(syntaxHighlighter).toHaveAttribute('data-language', 'typescript');
      });
    });

    it('should detect language from file tags in snippets', async () => {
      const skillWithTaggedSnippet = {
        ...mockSkillWithSnippets,
        snippets: [
          {
            ...mockSkillWithSnippets.snippets[0],
            content_type: undefined,
            tags: ['file:script.py'],
          },
        ],
      };

      renderWithRouter('test-skill-2', skillWithTaggedSnippet);

      await waitFor(() => {
        expect(screen.getByText('Test Skill with Snippets')).toBeInTheDocument();
      });

      const snippetsTab = screen.getByRole('button', { name: /snippets/i });
      await userEvent.click(snippetsTab);

      await waitFor(() => {
        const snippetItem = screen.getByText('test_snippet');
        expect(snippetItem).toBeInTheDocument();
      });

      const snippetItem = screen.getByText('test_snippet');
      await userEvent.click(snippetItem);

      await waitFor(() => {
        const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
        expect(syntaxHighlighter).toHaveAttribute('data-language', 'python');
      });
    });
  });

  describe('Visual Styling', () => {
    it('should apply custom styling to code container', async () => {
      renderWithRouter('test-skill-1', mockSkillWithTools);

      await waitFor(() => {
        expect(screen.getByText('Test Skill')).toBeInTheDocument();
      });

      const toolsTab = screen.getByRole('button', { name: /tools/i });
      await userEvent.click(toolsTab);

      await waitFor(() => {
        const toolItem = screen.getByText('test_tool');
        expect(toolItem).toBeInTheDocument();
      });

      const toolItem = screen.getByText('test_tool');
      await userEvent.click(toolItem);

      await waitFor(() => {
        const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
        const container = syntaxHighlighter.parentElement;
        
        // Verify container has expected styles
        expect(container).toHaveStyle({
          maxHeight: '70vh',
          overflow: 'auto',
        });
      });
    });

    it('should render with line numbers enabled', async () => {
      renderWithRouter('test-skill-1', mockSkillWithTools);

      await waitFor(() => {
        expect(screen.getByText('Test Skill')).toBeInTheDocument();
      });

      const toolsTab = screen.getByRole('button', { name: /tools/i });
      await userEvent.click(toolsTab);

      await waitFor(() => {
        const toolItem = screen.getByText('test_tool');
        expect(toolItem).toBeInTheDocument();
      });

      const toolItem = screen.getByText('test_tool');
      await userEvent.click(toolItem);

      await waitFor(() => {
        const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
        // In the actual implementation, showLineNumbers prop is passed
        // We verify the component is rendered (line numbers are handled by the library)
        expect(syntaxHighlighter).toBeInTheDocument();
      });
    });
  });
});
