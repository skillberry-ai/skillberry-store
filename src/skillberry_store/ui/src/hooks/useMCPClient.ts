// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useEffect, useCallback } from 'react';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

interface MCPTool {
  name: string;
  description?: string;
  inputSchema: any;
}

interface MCPPrompt {
  name: string;
  description?: string;
  arguments?: any[];
}

interface MCPPromptMessage {
  role: 'user' | 'assistant';
  content: {
    type: 'text' | 'image' | 'resource';
    text?: string;
    data?: string;
    mimeType?: string;
  };
}

interface MCPPromptContent {
  description?: string;
  messages: MCPPromptMessage[];
}

interface MCPClientState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  tools: MCPTool[];
  prompts: MCPPrompt[];
}

export function useMCPClient(serverPort: number | undefined, serverName: string) {
  const [state, setState] = useState<MCPClientState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    tools: [],
    prompts: [],
  });

  const [client, setClient] = useState<Client | null>(null);

  const connect = useCallback(async () => {
    if (!serverPort) {
      console.error('[MCP Client] No server port provided');
      setState(prev => ({ ...prev, error: 'Server port not available' }));
      return;
    }

    console.log(`[MCP Client] Starting connection to port ${serverPort}`);
    setState(prev => ({ ...prev, isConnecting: true, error: null }));

    try {
      console.log('[MCP Client] Creating MCP client...');
      // Create MCP client
      const mcpClient = new Client(
        {
          name: 'Skillberry Store UI',
          version: '1.0.0',
        },
        {
          capabilities: {
            tools: {},
            prompts: {},
          },
        }
      );
      console.log('[MCP Client] MCP client created successfully');

      // Create SSE transport
      const sseUrl = `http://localhost:${serverPort}/sse`;
      console.log(`[MCP Client] Creating SSE transport to ${sseUrl}`);
      const transport = new SSEClientTransport(
        new URL(sseUrl)
      );
      console.log('[MCP Client] SSE transport created');

      // Connect to server
      console.log('[MCP Client] Connecting to server...');
      await mcpClient.connect(transport);
      console.log('[MCP Client] Connected successfully!');

      // List available tools
      console.log('[MCP Client] Listing tools...');
      const toolsResponse = await mcpClient.listTools();
      console.log(`[MCP Client] Received ${toolsResponse.tools.length} tools:`, toolsResponse.tools);
      const tools = toolsResponse.tools.map((tool: any) => ({
        name: tool.name,
        description: tool.description,
        inputSchema: tool.inputSchema,
      }));

      // List available prompts
      console.log('[MCP Client] Listing prompts...');
      const promptsResponse = await mcpClient.listPrompts();
      console.log(`[MCP Client] Received ${promptsResponse.prompts.length} prompts:`, promptsResponse.prompts);
      const prompts = promptsResponse.prompts.map((prompt: any) => ({
        name: prompt.name,
        description: prompt.description,
        arguments: prompt.arguments,
      }));

      setClient(mcpClient);
      setState({
        isConnected: true,
        isConnecting: false,
        error: null,
        tools,
        prompts,
      });
      console.log('[MCP Client] Connection complete!');
    } catch (error) {
      console.error('[MCP Client] Connection failed:', error);
      console.error('[MCP Client] Error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined,
        error: error,
      });
      setState({
        isConnected: false,
        isConnecting: false,
        error: error instanceof Error ? error.message : 'Failed to connect to MCP server',
        tools: [],
        prompts: [],
      });
    }
  }, [serverPort]);

  const disconnect = useCallback(async () => {
    if (client) {
      try {
        console.log('[MCP Client] Disconnecting...');
        await client.close();
        console.log('[MCP Client] Disconnected successfully');
      } catch (error) {
        console.error('[MCP Client] Error disconnecting:', error);
      }
      setClient(null);
      setState({
        isConnected: false,
        isConnecting: false,
        error: null,
        tools: [],
        prompts: [],
      });
    }
  }, [client]);

  const getPrompt = useCallback(async (promptName: string, args?: Record<string, string>): Promise<MCPPromptContent | null> => {
    if (!client || !state.isConnected) {
      console.error('[MCP Client] Cannot get prompt: not connected');
      return null;
    }

    try {
      console.log(`[MCP Client] Getting prompt: ${promptName}`, args);
      const response = await client.getPrompt({ name: promptName, arguments: args });
      console.log(`[MCP Client] Received prompt content:`, response);
      
      return {
        description: response.description,
        messages: response.messages as MCPPromptMessage[],
      };
    } catch (error) {
      console.error(`[MCP Client] Error getting prompt ${promptName}:`, error);
      return null;
    }
  }, [client, state.isConnected]);

  // Auto-connect when component mounts
  useEffect(() => {
    console.log(`[MCP Client] useEffect triggered - serverPort: ${serverPort}, serverName: ${serverName}`);
    if (serverPort) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      console.log('[MCP Client] Component unmounting, cleaning up...');
      if (client) {
        client.close().catch(console.error);
      }
    };
  }, [serverPort]);

  return {
    ...state,
    connect,
    disconnect,
    getPrompt,
    client,
  };
}