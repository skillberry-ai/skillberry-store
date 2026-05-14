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

describe('VMCPServerDetailPage - OpenAPI Download Error Handling', () => {
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

    // Reset all mocks
    vi.clearAllMocks();

    // Setup default mock implementations
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

  describe('Error Handling', () => {
    it('should handle generateOpenAPISpec throwing an error', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
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

      vi.mocked(openApiGenerator.generateOpenAPISpec).mockImplementation(() => {
        throw new Error('Failed to generate OpenAPI spec');
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Click should not crash the app
      await user.click(downloadButton);

      // Verify generateOpenAPISpec was called
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalled();
      
      // Verify downloadOpenAPISpec was not called due to error
      expect(openApiGenerator.downloadOpenAPISpec).not.toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });

    it('should handle downloadOpenAPISpec throwing an error', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
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
      vi.mocked(openApiGenerator.downloadOpenAPISpec).mockImplementation(() => {
        throw new Error('Failed to download file');
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Click should not crash the app
      await user.click(downloadButton);

      // Verify both functions were called
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalled();
      expect(openApiGenerator.downloadOpenAPISpec).toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });

    it('should handle MCP client with malformed tools data', async () => {
      const user = userEvent.setup();
      
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: [
          {
            name: 'malformed_tool',
            description: null as any,
            inputSchema: null as any,
          },
        ],
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
      
      // Should handle malformed data gracefully
      await user.click(downloadButton);

      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledWith(
        'test-server',
        'Test server description',
        8080,
        expect.arrayContaining([
          expect.objectContaining({
            name: 'malformed_tool',
          }),
        ]),
        mockPrompts
      );
    });

    it('should handle MCP client with malformed prompts data', async () => {
      const user = userEvent.setup();
      
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: [
          {
            name: 'malformed_prompt',
            description: null as any,
            arguments: null as any,
          },
        ],
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
      
      // Should handle malformed data gracefully
      await user.click(downloadButton);

      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledWith(
        'test-server',
        'Test server description',
        8080,
        mockTools,
        expect.arrayContaining([
          expect.objectContaining({
            name: 'malformed_prompt',
          }),
        ])
      );
    });

    it('should not attempt download if server data is missing', async () => {
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

      vi.mocked(vmcpApi.get).mockResolvedValue(null as any);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText(/error loading/i)).toBeInTheDocument();
      });

      // Download button should not be present if server data failed to load
      const downloadButton = screen.queryByRole('button', { name: /download openapi spec/i });
      expect(downloadButton).not.toBeInTheDocument();
    });

    it('should handle rapid successive clicks gracefully', async () => {
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
      
      // Click multiple times rapidly
      await user.click(downloadButton);
      await user.click(downloadButton);
      await user.click(downloadButton);

      // All clicks should be handled without errors
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledTimes(3);
      expect(openApiGenerator.downloadOpenAPISpec).toHaveBeenCalledTimes(3);
    });
  });
});
