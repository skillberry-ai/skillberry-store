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
 * Edge case and stress tests for the OpenAPI download feature
 * 
 * These tests verify:
 * 1. Connection state transitions during download
 * 2. Concurrent download attempts
 * 3. Large spec generation
 * 4. Memory cleanup
 * 5. Race conditions
 */
describe('VMCPServerDetailPage - Edge Cases and Stress Tests', () => {
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

  describe('Connection State Transitions', () => {
    it('should handle disconnection during download attempt', async () => {
      const user = userEvent.setup();
      
      // Start connected
      const mockClient = {
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      };

      vi.mocked(useMCPClient).mockReturnValue(mockClient);

      const mockSpec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      // Simulate disconnection during download
      vi.mocked(openApiGenerator.generateOpenAPISpec).mockImplementation(() => {
        // Simulate disconnection
        mockClient.isConnected = false;
        return mockSpec;
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'test-server' })).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      await user.click(downloadButton);

      // Should still complete the download that was initiated while connected
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalled();
      expect(openApiGenerator.downloadOpenAPISpec).toHaveBeenCalled();
    });

    it('should handle connection state change between button enable and click', async () => {
      const user = userEvent.setup();
      
      const mockClient = {
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: mockPrompts,
        error: null,
        connect: vi.fn(),
        disconnect: vi.fn(),
        getPrompt: vi.fn(),
      };

      vi.mocked(useMCPClient).mockReturnValue(mockClient);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      expect(downloadButton).toBeEnabled();

      // Disconnect before click
      mockClient.isConnected = false;

      // Click should still work with the state at click time
      await user.click(downloadButton);

      // Should not generate spec if disconnected at click time
      expect(openApiGenerator.generateOpenAPISpec).not.toHaveBeenCalled();
    });

    it('should handle reconnection after failed download', async () => {
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

      // First attempt fails
      vi.mocked(openApiGenerator.generateOpenAPISpec).mockImplementationOnce(() => {
        throw new Error('Generation failed');
      });

      // Second attempt succeeds
      const mockSpec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };
      vi.mocked(openApiGenerator.generateOpenAPISpec).mockImplementationOnce(() => mockSpec);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // First attempt
      await user.click(downloadButton);
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledTimes(1);

      // Second attempt should work
      await user.click(downloadButton);
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledTimes(2);
      expect(openApiGenerator.downloadOpenAPISpec).toHaveBeenCalledTimes(1);
    });
  });

  describe('Concurrent Operations', () => {
    it('should handle multiple rapid clicks gracefully', async () => {
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
      
      // Rapid fire clicks
      await user.click(downloadButton);
      await user.click(downloadButton);
      await user.click(downloadButton);
      await user.click(downloadButton);
      await user.click(downloadButton);

      // All clicks should be processed
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledTimes(5);
      expect(openApiGenerator.downloadOpenAPISpec).toHaveBeenCalledTimes(5);
    });

    it('should handle download while other operations are in progress', async () => {
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
      const editButton = screen.getByRole('button', { name: /edit/i });
      
      // Click download and edit simultaneously
      await Promise.all([
        user.click(downloadButton),
        user.click(editButton),
      ]);

      // Download should complete
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalled();
    });
  });

  describe('Large Spec Generation', () => {
    it('should handle server with many tools', async () => {
      const user = userEvent.setup();
      
      // Generate 100 tools
      const manyTools = Array.from({ length: 100 }, (_, i) => ({
        name: `tool_${i}`,
        description: `Tool number ${i}`,
        inputSchema: {
          type: 'object',
          properties: {
            param1: { type: 'string' },
            param2: { type: 'number' },
            param3: { type: 'boolean' },
          },
        },
      }));

      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: manyTools,
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
      await user.click(downloadButton);

      // Should handle large number of tools
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledWith(
        'test-server',
        'Test server description',
        8080,
        manyTools,
        mockPrompts
      );
    });

    it('should handle server with many prompts', async () => {
      const user = userEvent.setup();
      
      // Generate 100 prompts
      const manyPrompts = Array.from({ length: 100 }, (_, i) => ({
        name: `prompt_${i}`,
        description: `Prompt number ${i}`,
        arguments: [
          { name: 'arg1', required: true },
          { name: 'arg2', required: false },
        ],
      }));

      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: mockTools,
        prompts: manyPrompts,
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
      await user.click(downloadButton);

      // Should handle large number of prompts
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledWith(
        'test-server',
        'Test server description',
        8080,
        mockTools,
        manyPrompts
      );
    });

    it('should handle tools with deeply nested complex schemas', async () => {
      const user = userEvent.setup();
      
      const complexTools = [
        {
          name: 'complex_tool',
          description: 'Tool with complex schema',
          inputSchema: {
            type: 'object',
            properties: {
              config: {
                type: 'object',
                properties: {
                  database: {
                    type: 'object',
                    properties: {
                      connection: {
                        type: 'object',
                        properties: {
                          host: { type: 'string' },
                          port: { type: 'number' },
                          credentials: {
                            type: 'object',
                            properties: {
                              username: { type: 'string' },
                              password: { type: 'string' },
                            },
                          },
                        },
                      },
                    },
                  },
                },
              },
              data: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    id: { type: 'string' },
                    values: {
                      type: 'array',
                      items: { type: 'number' },
                    },
                  },
                },
              },
            },
          },
        },
      ];

      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: complexTools,
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
      await user.click(downloadButton);

      // Should handle complex nested schemas
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalled();
    });
  });

  describe('Memory and Resource Management', () => {
    it('should clean up resources after download', async () => {
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
      await user.click(downloadButton);

      // Verify URL.revokeObjectURL was called for cleanup
      expect(global.URL.revokeObjectURL).toHaveBeenCalled();
    });

    it('should handle multiple downloads without memory leaks', async () => {
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
      
      // Multiple downloads
      for (let i = 0; i < 10; i++) {
        await user.click(downloadButton);
      }

      // Each download should clean up
      expect(global.URL.revokeObjectURL).toHaveBeenCalledTimes(10);
    });
  });

  describe('Race Conditions', () => {
    it('should handle component unmount during download', async () => {
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

      const { unmount } = renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // Start download
      await user.click(downloadButton);
      
      // Unmount immediately
      unmount();

      // Should not throw errors
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalled();
    });

    it('should handle server data update during download', async () => {
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

      let callCount = 0;
      vi.mocked(openApiGenerator.generateOpenAPISpec).mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          // Simulate server data change during first download
          vi.mocked(vmcpApi.get).mockResolvedValue({
            ...mockServer,
            name: 'updated-server',
          });
        }
        return mockSpec;
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('test-server')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      
      // First download
      await user.click(downloadButton);
      
      // Should use original server data
      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledWith(
        'test-server',
        expect.any(String),
        expect.any(Number),
        expect.any(Array),
        expect.any(Array)
      );
    });
  });
});
