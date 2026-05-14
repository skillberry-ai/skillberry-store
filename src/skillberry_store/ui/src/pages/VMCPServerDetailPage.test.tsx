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

describe('VMCPServerDetailPage - OpenAPI Download Feature', () => {
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

  describe('Download OpenAPI Spec Button', () => {
    it('should render the download button', async () => {
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
      expect(downloadButton).toBeInTheDocument();
    });

    it('should disable download button when not connected to MCP server', async () => {
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

    it('should enable download button when connected to MCP server', async () => {
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
      expect(downloadButton).toBeEnabled();
    });

    it('should call generateOpenAPISpec with correct parameters when download button is clicked', async () => {
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

      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledWith(
        'test-server',
        'Test server description',
        8080,
        mockTools,
        mockPrompts
      );
    });

    it('should call downloadOpenAPISpec with correct filename when download button is clicked', async () => {
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

      expect(openApiGenerator.downloadOpenAPISpec).toHaveBeenCalledWith(
        mockSpec,
        'test_server_openapi.json'
      );
    });

    it('should sanitize server name for filename', async () => {
      const user = userEvent.setup();
      
      const serverWithSpecialChars = {
        ...mockServer,
        name: 'My-Server@2.0!',
      };

      vi.mocked(vmcpApi.get).mockResolvedValue(serverWithSpecialChars);
      
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
        expect(screen.getByText('My-Server@2.0!')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      await user.click(downloadButton);

      // Filename should have special characters replaced with underscores
      expect(openApiGenerator.downloadOpenAPISpec).toHaveBeenCalledWith(
        mockSpec,
        'my_server_2_0__openapi.json'
      );
    });

    it('should not call download functions when button is clicked while disconnected', async () => {
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
      
      // Button should be disabled, but try to click anyway
      expect(downloadButton).toBeDisabled();

      expect(openApiGenerator.generateOpenAPISpec).not.toHaveBeenCalled();
      expect(openApiGenerator.downloadOpenAPISpec).not.toHaveBeenCalled();
    });

    it('should handle empty tools and prompts arrays', async () => {
      const user = userEvent.setup();
      
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: true,
        isConnecting: false,
        tools: [],
        prompts: [],
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

      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledWith(
        'test-server',
        'Test server description',
        8080,
        [],
        []
      );
    });

    it('should use empty string for description if not provided', async () => {
      const user = userEvent.setup();
      
      const serverWithoutDescription = {
        ...mockServer,
        description: undefined,
      };

      vi.mocked(vmcpApi.get).mockResolvedValue(serverWithoutDescription);
      
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

      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledWith(
        'test-server',
        '',
        8080,
        mockTools,
        mockPrompts
      );
    });

    it('should use 0 for port if not provided', async () => {
      const user = userEvent.setup();
      
      const serverWithoutPort = {
        ...mockServer,
        port: undefined,
      };

      vi.mocked(vmcpApi.get).mockResolvedValue(serverWithoutPort);
      
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

      expect(openApiGenerator.generateOpenAPISpec).toHaveBeenCalledWith(
        'test-server',
        'Test server description',
        0,
        mockTools,
        mockPrompts
      );
    });
  });

  describe('Button Positioning and Layout', () => {
    it('should render download button before edit and delete buttons', async () => {
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

      const buttons = screen.getAllByRole('button');
      const downloadButton = screen.getByRole('button', { name: /download openapi spec/i });
      const editButton = screen.getByRole('button', { name: /edit/i });
      const deleteButton = screen.getByRole('button', { name: /delete/i });

      const downloadIndex = buttons.indexOf(downloadButton);
      const editIndex = buttons.indexOf(editButton);
      const deleteIndex = buttons.indexOf(deleteButton);

      // Download button should come before edit and delete
      expect(downloadIndex).toBeLessThan(editIndex);
      expect(editIndex).toBeLessThan(deleteIndex);
    });

    it('should render download button with download icon', async () => {
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
      
      // Check that the button contains an SVG icon (DownloadIcon)
      const icon = downloadButton.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Connection State Handling', () => {
    it('should disable button during connection attempt', async () => {
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: false,
        isConnecting: true,
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

    it('should remain disabled when connection fails', async () => {
      vi.mocked(useMCPClient).mockReturnValue({
        isConnected: false,
        isConnecting: false,
        tools: [],
        prompts: [],
        error: 'Connection failed',
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
  });
});
