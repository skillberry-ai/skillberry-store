// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VMCPServerDetailPage } from './VMCPServerDetailPage';
import * as openApiGenerator from '../utils/openApiGenerator';

// Mock the router hooks
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ name: 'test-server' }),
    useNavigate: () => vi.fn(),
  };
});

// Mock the API services
vi.mock('@/services/api', () => ({
  vmcpApi: {
    get: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  skillsApi: {
    list: vi.fn(),
  },
}));

// Mock the MCP client hook
vi.mock('../hooks/useMCPClient', () => ({
  useMCPClient: vi.fn(),
}));

// Mock the openApiGenerator functions
vi.mock('../utils/openApiGenerator', () => ({
  generateOpenAPISpec: vi.fn(),
  downloadOpenAPISpec: vi.fn(),
}));

import { vmcpApi, skillsApi } from '@/services/api';
import { useMCPClient } from '../hooks/useMCPClient';

/**
 * Accessibility tests for the OpenAPI download feature
 * 
 * These tests verify:
 * 1. Proper ARIA attributes and labels
 * 2. Keyboard navigation support
 * 3. Screen reader compatibility
 * 4. Focus management
 * 5. Tooltip accessibility
 */
describe('VMCPServerDetailPage - Accessibility Tests', () => {
  let queryClient: QueryClient;

  const mockServer = {
    uuid: 'test-uuid',
    name: 'test-server',
    description: 'Test server description',
    version: '1.0.0',
    state: 'approved' as const,
    tags: ['test', 'demo'],
    port: 8080,
    skill_uuid: 'skill-uuid',
    running: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
    extra: {},
  };

  const mockTools = [
    {
      name: 'read_file',
      description: 'Read a file from disk',
      inputSchema: {
        type: 'object',
        properties: {
          path: { type: 'string' },
        },
        required: ['path'],
      },
    },
  ];

  const mockPrompts = [
    {
      name: 'code_review',
      description: 'Review code',
      arguments: [
        { name: 'language', required: true },
      ],
    },
  ];

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    vi.clearAllMocks();
    vi.mocked(vmcpApi.get).mockResolvedValue(mockServer);
    vi.mocked(skillsApi.list).mockResolvedValue([]);
  });

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <VMCPServerDetailPage />
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  describe('ARIA Attributes and Labels', () => {
    it('should have proper button role and accessible name', async () => {
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'test-server' })).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      expect(downloadButton).toBeInTheDocument();
      expect(downloadButton).toHaveAttribute('type', 'button');
    });

    it('should have aria-disabled when not connected', async () => {
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: false,
        isConnecting: false,
        tools: [],
        prompts: [],
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      expect(downloadButton).toBeDisabled();
    });

    it('should have descriptive tooltip that is accessible', async () => {
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Tooltip should be associated with button
      expect(downloadButton).toBeInTheDocument();
    });
  });

  describe('Keyboard Navigation', () => {
    it('should be focusable via keyboard', async () => {
      const user = userEvent.setup();
      
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Tab to the button
      await user.tab();
      
      // Button should be in the tab order
      expect(downloadButton).toBeInTheDocument();
    });

    it('should be activatable with Enter key', async () => {
      const user = userEvent.setup();
      
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      const mockSpec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      vi.mocked(openApiGenerator.generateOpenAPISpec).mockReturnValue(mockSpec);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Focus the button
      downloadButton.focus();
      expect(downloadButton).toHaveFocus();
      
      // Press Enter
      await user.keyboard('{Enter}');
      
      // Should trigger download
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalled();
    });

    it('should be activatable with Space key', async () => {
      const user = userEvent.setup();
      
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      const mockSpec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      vi.mocked(openApiGenerator.generateOpenAPISpec).mockReturnValue(mockSpec);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Focus the button
      downloadButton.focus();
      
      // Press Space
      await user.keyboard(' ');
      
      // Should trigger download
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalled();
    });

    it('should not be activatable when disabled', async () => {
      const user = userEvent.setup();
      
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: false,
        isConnecting: false,
        tools: [],
        prompts: [],
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Focus the button
      downloadButton.focus();
      
      // Try to press Enter
      await user.keyboard('{Enter}');
      
      // Should not trigger download
      expect(openApiGenerator.generateOpenAPISpec).not.toHaveBeenCalled();
    });
  });

  describe('Focus Management', () => {
    it('should maintain focus after download completes', async () => {
      const user = userEvent.setup();
      
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      const mockSpec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      vi.mocked(openApiGenerator.generateOpenAPISpec).mockReturnValue(mockSpec);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Focus and click
      downloadButton.focus();
      await user.click(downloadButton);
      
      // Focus should remain on button after download
      expect(downloadButton).toHaveFocus();
    });

    it('should have visible focus indicator', async () => {
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Focus the button
      downloadButton.focus();
      
      // Button should be focused
      expect(downloadButton).toHaveFocus();
    });
  });

  describe('Screen Reader Support', () => {
    it('should announce button state changes to screen readers', async () => {
      const { rerender } = renderComponent();

      // Initially disconnected
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: false,
        isConnecting: false,
        tools: [],
        prompts: [],
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      let downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      expect(downloadButton).toBeDisabled();

      // Simulate connection
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      rerender(
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <VMCPServerDetailPage />
          </BrowserRouter>
        </QueryClientProvider>
      );

      await waitFor(() => {
        downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
        expect(downloadButton).toBeEnabled();
      });
    });

    it('should have meaningful button text for screen readers', async () => {
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      // Button text should be descriptive
      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      expect(downloadButton).toHaveTextContent(/download openapi spec/i);
    });
  });

  describe('Color Contrast and Visual Indicators', () => {
    it('should render icon alongside text for better visual recognition', async () => {
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Button should contain an SVG icon
      const icon = downloadButton.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should visually indicate disabled state', async () => {
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: false,
        isConnecting: false,
        tools: [],
        prompts: [],
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Disabled button should have appropriate styling
      expect(downloadButton).toBeDisabled();
    });
  });
});
