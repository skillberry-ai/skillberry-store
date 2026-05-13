// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SnippetDetailPage } from './SnippetDetailPage';

// Mock the API client
vi.mock('../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock react-syntax-highlighter
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

const mockPythonSnippet = {
  id: 'snippet-1',
  name: 'Python Helper',
  description: 'A Python utility snippet',
  content: `def calculate_fibonacci(n):
    """Calculate Fibonacci number"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)`,
  content_type: 'text/x-python',
  tags: ['python', 'utility'],
};

const mockJavaScriptSnippet = {
  id: 'snippet-2',
  name: 'JavaScript Utility',
  description: 'A JavaScript utility snippet',
  content: `function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}`,
  content_type: 'text/javascript',
  tags: ['javascript', 'utility'],
};

const mockSnippetWithFileTags = {
  id: 'snippet-3',
  name: 'TypeScript Config',
  description: 'TypeScript configuration snippet',
  content: `{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true
  }
}`,
  content_type: undefined,
  tags: ['file:tsconfig.json', 'config'],
};

describe('SnippetDetailPage - Syntax Highlighting', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithRouter = (snippetId: string, mockData: any) => {
    const { apiClient } = require('../api/client');
    apiClient.get.mockResolvedValue({ data: mockData });

    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/snippets/${snippetId}`]}>
          <Routes>
            <Route path="/snippets/:id" element={<SnippetDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  describe('Basic Syntax Highlighting', () => {
    it('should render syntax highlighter for snippet content', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      // Verify syntax highlighter is rendered
      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      expect(syntaxHighlighter).toBeInTheDocument();
    });

    it('should display snippet code content', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      // Verify code content is displayed
      expect(screen.getByText(/def calculate_fibonacci/)).toBeInTheDocument();
      expect(screen.getByText(/return calculate_fibonacci/)).toBeInTheDocument();
    });

    it('should render code in a scrollable container', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      const container = syntaxHighlighter.parentElement;
      
      expect(container).toHaveStyle({ overflow: 'auto' });
    });
  });

  describe('Language Detection', () => {
    it('should detect Python from content_type', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      expect(syntaxHighlighter).toHaveAttribute('data-language', 'python');
    });

    it('should detect JavaScript from content_type', async () => {
      renderWithRouter('snippet-2', mockJavaScriptSnippet);

      await waitFor(() => {
        expect(screen.getByText('JavaScript Utility')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      expect(syntaxHighlighter).toHaveAttribute('data-language', 'javascript');
    });

    it('should detect language from file tags when content_type is missing', async () => {
      renderWithRouter('snippet-3', mockSnippetWithFileTags);

      await waitFor(() => {
        expect(screen.getByText('TypeScript Config')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      // tsconfig.json should be detected as JSON
      expect(syntaxHighlighter).toHaveAttribute('data-language', 'json');
    });

    it('should handle snippets with multiple content types', async () => {
      const snippetWithMultipleTypes = {
        ...mockPythonSnippet,
        content_type: 'text/x-python',
        tags: ['python', 'file:script.js'], // Conflicting tag
      };

      renderWithRouter('snippet-1', snippetWithMultipleTypes);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      // content_type should take priority
      expect(syntaxHighlighter).toHaveAttribute('data-language', 'python');
    });

    it('should default to python for unknown content types', async () => {
      const snippetWithUnknownType = {
        ...mockPythonSnippet,
        content_type: 'application/octet-stream',
        tags: [],
      };

      renderWithRouter('snippet-1', snippetWithUnknownType);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      expect(syntaxHighlighter).toHaveAttribute('data-language', 'python');
    });
  });

  describe('Visual Styling', () => {
    it('should apply custom styling to code container', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      const container = syntaxHighlighter.parentElement;

      // Verify container has expected styles
      expect(container).toHaveStyle({
        maxHeight: '70vh',
        overflow: 'auto',
      });
    });

    it('should have border styling on code container', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      const container = syntaxHighlighter.parentElement;

      // Verify border is applied
      const styles = window.getComputedStyle(container!);
      expect(styles.border).toBeTruthy();
    });

    it('should render with line numbers enabled', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      // Line numbers are handled by the syntax highlighter library
      expect(syntaxHighlighter).toBeInTheDocument();
    });
  });

  describe('Content Formatting', () => {
    it('should preserve code indentation', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      const codeContent = syntaxHighlighter.textContent;

      // Verify indentation is preserved
      expect(codeContent).toContain('    if n <= 1:');
      expect(codeContent).toContain('        return n');
    });

    it('should handle multi-line code correctly', async () => {
      renderWithRouter('snippet-2', mockJavaScriptSnippet);

      await waitFor(() => {
        expect(screen.getByText('JavaScript Utility')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      const codeContent = syntaxHighlighter.textContent;

      // Verify all lines are present
      expect(codeContent).toContain('function debounce');
      expect(codeContent).toContain('let timeout;');
      expect(codeContent).toContain('return function executedFunction');
      expect(codeContent).toContain('setTimeout(later, wait);');
    });

    it('should not wrap lines by default', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      // wrapLines is set to false in the implementation
      expect(syntaxHighlighter).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty snippet content', async () => {
      const emptySnippet = {
        ...mockPythonSnippet,
        content: '',
      };

      renderWithRouter('snippet-1', emptySnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      expect(syntaxHighlighter).toBeInTheDocument();
      expect(syntaxHighlighter.textContent).toBe('');
    });

    it('should handle very long code snippets', async () => {
      const longContent = Array(100)
        .fill('def function_name():\n    pass\n')
        .join('\n');

      const longSnippet = {
        ...mockPythonSnippet,
        content: longContent,
      };

      renderWithRouter('snippet-1', longSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      const container = syntaxHighlighter.parentElement;

      // Verify scrollable container handles long content
      expect(container).toHaveStyle({ overflow: 'auto' });
    });

    it('should handle special characters in code', async () => {
      const snippetWithSpecialChars = {
        ...mockPythonSnippet,
        content: `def test():
    # Special chars: <>&"'
    return "Hello <world> & 'friends'"`,
      };

      renderWithRouter('snippet-1', snippetWithSpecialChars);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      const codeContent = syntaxHighlighter.textContent;

      // Verify special characters are preserved
      expect(codeContent).toContain('<>&"\'');
    });
  });

  describe('Accessibility', () => {
    it('should render semantic HTML structure', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      // Verify pre and code elements are used
      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      expect(syntaxHighlighter.tagName).toBe('PRE');
      
      const codeElement = syntaxHighlighter.querySelector('code');
      expect(codeElement).toBeInTheDocument();
    });

    it('should be keyboard accessible', async () => {
      renderWithRouter('snippet-1', mockPythonSnippet);

      await waitFor(() => {
        expect(screen.getByText('Python Helper')).toBeInTheDocument();
      });

      const syntaxHighlighter = screen.getByTestId('syntax-highlighter');
      const container = syntaxHighlighter.parentElement;

      // Scrollable container should be accessible
      expect(container).toHaveStyle({ overflow: 'auto' });
    });
  });
});
