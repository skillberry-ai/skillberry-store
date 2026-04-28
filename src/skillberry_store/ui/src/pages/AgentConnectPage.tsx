// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useEffect } from 'react';
import {
  PageSection,
  Title,
  Card,
  CardBody,
  CardTitle,
  Alert,
  Spinner,
  CodeBlock,
  CodeBlockCode,
  ClipboardCopyButton,
  ExpandableSection,
  Label,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Button,
  Text,
  ToggleGroup,
  ToggleGroupItem,
} from '@patternfly/react-core';
import { CheckCircleIcon, ExclamationCircleIcon, PluggedIcon, UnpluggedIcon } from '@patternfly/react-icons';
import { adminApi } from '@/services/api';
import type { ServerInfo } from '@/services/api';
import { useMCPClient } from '@/hooks/useMCPClient';

type McpScope = 'project' | 'user';
type McpMode = 'curated' | 'full';

export function AgentConnectPage() {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [isManualConfigExpanded, setIsManualConfigExpanded] = useState(false);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [serverInfo, setServerInfo] = useState<ServerInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mcpScope, setMcpScope] = useState<McpScope>('project');
  const [mcpMode, setMcpMode] = useState<McpMode>('curated');

  useEffect(() => {
    adminApi.getServerInfo()
      .then((info) => setServerInfo(info))
      .catch((err) => setLoadError(err.message))
      .finally(() => setIsLoading(false));
  }, []);

  const curatedMcpUrl = serverInfo?.agent_mcp_url || `http://localhost:${serverInfo?.agent_mcp_port || 9999}/sse`;
  const fullMcpUrl = serverInfo?.control_mcp_url || `http://localhost:${serverInfo?.port || 8000}/control_sse`;

  const isCurated = mcpMode === 'curated';
  const mcpUrl = isCurated ? curatedMcpUrl : fullMcpUrl;
  const mcpServerName = isCurated ? 'skillberry-store' : 'skillberry-store-full';

  const mcpClient = useMCPClient(undefined, mcpServerName, isTestingConnection ? mcpUrl : undefined);

  const handleCopy = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const scopeFlag = mcpScope === 'project' ? 'project' : 'user';
  const addCommand = `claude mcp add ${mcpServerName} -s ${scopeFlag} -t sse ${mcpUrl}`;
  const removeCommand = `claude mcp remove ${mcpServerName} -s ${scopeFlag}`;

  const settingsJson = JSON.stringify({
    mcpServers: {
      [mcpServerName]: {
        url: mcpUrl,
      },
    },
  }, null, 2);

  if (isLoading) {
    return (
      <PageSection>
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <Spinner size="xl" />
        </div>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection>
        <Title headingLevel="h1" size="2xl">
          Connect Your Agent
        </Title>
        <Text style={{ marginTop: '0.5rem', color: '#6a6e73' }}>
          Connect AI agents to the Skillberry Store via MCP.
          Once connected, your agent can list, create, update, and manage tools, skills, snippets, and VMCP servers.
        </Text>
        <Text style={{ marginTop: '0.75rem', color: '#6a6e73' }}>
          Two endpoints are available:
        </Text>
        <ul style={{ margin: '0.25rem 0 0 0', paddingLeft: '1.25rem', color: '#6a6e73', lineHeight: '1.7' }}>
          <li>
            <strong>Curated</strong> (default, port 9999) — a compact, hand-picked set of ~15 tools with
            LLM-friendly names and docstrings. Smaller context footprint, fewer tokens spent on tool discovery.
            Recommended for most agent workflows.
          </li>
          <li>
            <strong>Full</strong> (port 8000) — every FastAPI route auto-exposed as an MCP tool.
            More complete coverage (delete, snippets, admin, import/export, etc.) but larger context footprint
            and HTTP-style tool names. Pick this when the curated set is missing an operation you need.
          </li>
        </ul>
      </PageSection>

      <PageSection>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {loadError && (
            <Alert variant="warning" title="Could not fetch server info" isInline>
              {loadError}. Using default values.
            </Alert>
          )}

          {/* MCP Endpoint Info */}
          <Card>
            <CardTitle>MCP Endpoint</CardTitle>
            <CardBody>
              <div style={{ marginBottom: '1rem' }}>
                <Text component="small" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                  Connection mode:
                </Text>
                <ToggleGroup aria-label="MCP mode selection">
                  <ToggleGroupItem
                    text="Curated (recommended)"
                    buttonId="mode-curated"
                    isSelected={mcpMode === 'curated'}
                    onChange={() => setMcpMode('curated')}
                  />
                  <ToggleGroupItem
                    text="Full (all FastAPI endpoints)"
                    buttonId="mode-full"
                    isSelected={mcpMode === 'full'}
                    onChange={() => setMcpMode('full')}
                  />
                </ToggleGroup>
                <Text component="small" style={{ marginTop: '0.5rem', display: 'block', color: '#6a6e73', fontSize: '0.8rem' }}>
                  {isCurated
                    ? 'A compact, hand-picked set of ~15 tools with LLM-friendly names and docstrings. Smaller context footprint — the agent spends fewer tokens figuring out what to call. Recommended for most agent workflows.'
                    : 'Exposes every FastAPI route as an MCP tool (auto-generated). More complete coverage (delete, snippets, admin, import/export, etc.) but larger context footprint and HTTP-style tool names. Pick this when the curated set is missing an operation you need.'}
                </Text>
              </div>
              <DescriptionList isHorizontal>
                <DescriptionListGroup>
                  <DescriptionListTerm>{isCurated ? 'Agent MCP URL' : 'Full MCP URL'}</DescriptionListTerm>
                  <DescriptionListDescription>
                    <code style={{ fontSize: '0.95rem' }}>{mcpUrl}</code>
                  </DescriptionListDescription>
                </DescriptionListGroup>
                {serverInfo && (
                  <>
                    {!isCurated && (
                      <DescriptionListGroup>
                        <DescriptionListTerm>API Docs</DescriptionListTerm>
                        <DescriptionListDescription>
                          <a href={serverInfo.api_docs} target="_blank" rel="noopener noreferrer">
                            {serverInfo.api_docs}
                          </a>
                          <Text component="small" style={{ display: 'block', color: '#6a6e73', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                            The Full MCP exposes every route from this OpenAPI surface.
                          </Text>
                        </DescriptionListDescription>
                      </DescriptionListGroup>
                    )}
                    <DescriptionListGroup>
                      <DescriptionListTerm>Status</DescriptionListTerm>
                      <DescriptionListDescription>
                        {isCurated ? (
                          <Label color={serverInfo.agent_mcp_url ? 'green' : 'orange'}>
                            {serverInfo.agent_mcp_url ? 'Running' : 'Not yet started'}
                          </Label>
                        ) : (
                          <Label color="green">Running</Label>
                        )}
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  </>
                )}
              </DescriptionList>
            </CardBody>
          </Card>

          {/* Claude Code CLI Commands */}
          <Card>
            <CardTitle>Claude Code CLI Commands</CardTitle>
            <CardBody>
              <Text style={{ marginBottom: '1rem' }}>
                Run these commands in your terminal to connect or disconnect Claude Code:
              </Text>

              <div style={{ marginBottom: '1rem' }}>
                <Text component="small" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                  Install scope:
                </Text>
                <ToggleGroup aria-label="MCP scope selection">
                  <ToggleGroupItem
                    text="This project only"
                    buttonId="scope-project"
                    isSelected={mcpScope === 'project'}
                    onChange={() => setMcpScope('project')}
                  />
                  <ToggleGroupItem
                    text="Global (all projects)"
                    buttonId="scope-user"
                    isSelected={mcpScope === 'user'}
                    onChange={() => setMcpScope('user')}
                  />
                </ToggleGroup>
                <Text component="small" style={{ marginTop: '0.5rem', display: 'block', color: '#6a6e73', fontSize: '0.8rem' }}>
                  {mcpScope === 'project'
                    ? 'Saves to .claude/settings.json in your project — only available when working in this repo.'
                    : 'Saves to ~/.claude/settings.json — available across all your projects.'}
                </Text>
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <Text component="small" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                  Add MCP server:
                </Text>
                <CodeBlock
                  actions={
                    <ClipboardCopyButton
                      id="copy-add-cmd"
                      textId="add-cmd"
                      aria-label="Copy add command"
                      onClick={() => handleCopy(addCommand, 'add')}
                      variant="plain"
                    >
                      {copiedField === 'add' ? 'Copied!' : 'Copy'}
                    </ClipboardCopyButton>
                  }
                >
                  <CodeBlockCode id="add-cmd">{addCommand}</CodeBlockCode>
                </CodeBlock>
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <Text component="small" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                  Remove MCP server:
                </Text>
                <CodeBlock
                  actions={
                    <ClipboardCopyButton
                      id="copy-remove-cmd"
                      textId="remove-cmd"
                      aria-label="Copy remove command"
                      onClick={() => handleCopy(removeCommand, 'remove')}
                      variant="plain"
                    >
                      {copiedField === 'remove' ? 'Copied!' : 'Copy'}
                    </ClipboardCopyButton>
                  }
                >
                  <CodeBlockCode id="remove-cmd">{removeCommand}</CodeBlockCode>
                </CodeBlock>
              </div>

              <ExpandableSection
                toggleText={isManualConfigExpanded ? 'Hide JSON config' : 'Or add JSON config to your agent'}
                isExpanded={isManualConfigExpanded}
                onToggle={(_event, expanded) => setIsManualConfigExpanded(expanded)}
              >
                <Text style={{ marginBottom: '0.75rem' }}>
                  Add the following MCP server configuration to your agent:
                </Text>
                <CodeBlock
                  actions={
                    <ClipboardCopyButton
                      id="copy-json"
                      textId="json-config"
                      aria-label="Copy JSON config"
                      onClick={() => handleCopy(settingsJson, 'json')}
                      variant="plain"
                    >
                      {copiedField === 'json' ? 'Copied!' : 'Copy'}
                    </ClipboardCopyButton>
                  }
                >
                  <CodeBlockCode id="json-config">{settingsJson}</CodeBlockCode>
                </CodeBlock>
              </ExpandableSection>
            </CardBody>
          </Card>

          {/* Connection Test */}
          <Card>
            <CardTitle>Connection Test</CardTitle>
            <CardBody>
              <div style={{ marginBottom: '1rem' }}>
                <Text component="small" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                  Test against:
                </Text>
                <ToggleGroup aria-label="Connection test target">
                  <ToggleGroupItem
                    text="Curated MCP"
                    buttonId="test-mode-curated"
                    isSelected={mcpMode === 'curated'}
                    onChange={() => {
                      if (isTestingConnection) {
                        mcpClient.disconnect();
                        setIsTestingConnection(false);
                      }
                      setMcpMode('curated');
                    }}
                  />
                  <ToggleGroupItem
                    text="Full MCP (over FastAPI)"
                    buttonId="test-mode-full"
                    isSelected={mcpMode === 'full'}
                    onChange={() => {
                      if (isTestingConnection) {
                        mcpClient.disconnect();
                        setIsTestingConnection(false);
                      }
                      setMcpMode('full');
                    }}
                  />
                </ToggleGroup>
                <Text component="small" style={{ marginTop: '0.5rem', display: 'block', color: '#6a6e73', fontSize: '0.8rem' }}>
                  Currently targeting: <code>{mcpUrl}</code>
                </Text>
              </div>

              {!isTestingConnection ? (
                <Button
                  variant="secondary"
                  icon={<PluggedIcon />}
                  onClick={() => setIsTestingConnection(true)}
                >
                  Test Connection
                </Button>
              ) : (
                <div>
                  {mcpClient.isConnecting && (
                    <Alert variant="info" title="Connecting..." isInline>
                      <Spinner size="sm" /> Attempting to connect to {mcpUrl}
                    </Alert>
                  )}
                  {mcpClient.isConnected && (
                    <>
                      <Alert
                        variant="success"
                        title="Connected"
                        isInline
                        customIcon={<CheckCircleIcon />}
                      >
                        Successfully connected to the MCP server. Found{' '}
                        <strong>{mcpClient.tools.length}</strong> tool(s) and{' '}
                        <strong>{mcpClient.prompts.length}</strong> prompt(s).
                      </Alert>

                      <ExpandableSection
                        toggleText={`Available Operations (${mcpClient.tools.length} tools, ${mcpClient.prompts.length} prompts)`}
                        style={{ marginTop: '1rem' }}
                      >
                        {mcpClient.tools.length > 0 && (
                          <div style={{ marginBottom: '1rem' }}>
                            <Text component="small" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                              Tools:
                            </Text>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                              {mcpClient.tools.map((tool) => (
                                <ExpandableSection
                                  key={tool.name}
                                  toggleContent={
                                    <span style={{ fontSize: '0.875rem' }}>
                                      <strong>{tool.name}</strong>
                                      {tool.description && (
                                        <span style={{ color: '#6a6e73', marginLeft: '0.5rem' }}>— {tool.description}</span>
                                      )}
                                    </span>
                                  }
                                >
                                  <CodeBlock style={{ marginTop: '0.5rem', marginBottom: '0.5rem' }}>
                                    <CodeBlockCode>{JSON.stringify(tool.inputSchema, null, 2)}</CodeBlockCode>
                                  </CodeBlock>
                                </ExpandableSection>
                              ))}
                            </div>
                          </div>
                        )}
                        {mcpClient.prompts.length > 0 && (
                          <div>
                            <Text component="small" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                              Prompts:
                            </Text>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                              {mcpClient.prompts.map((prompt) => (
                                <ExpandableSection
                                  key={prompt.name}
                                  toggleContent={
                                    <span style={{ fontSize: '0.875rem' }}>
                                      <strong>{prompt.name}</strong>
                                      {prompt.description && (
                                        <span style={{ color: '#6a6e73', marginLeft: '0.5rem' }}>— {prompt.description}</span>
                                      )}
                                    </span>
                                  }
                                >
                                  {prompt.arguments && prompt.arguments.length > 0 ? (
                                    <CodeBlock style={{ marginTop: '0.5rem', marginBottom: '0.5rem' }}>
                                      <CodeBlockCode>{JSON.stringify(prompt.arguments, null, 2)}</CodeBlockCode>
                                    </CodeBlock>
                                  ) : (
                                    <Text component="small" style={{ color: '#6a6e73', marginTop: '0.5rem', display: 'block' }}>
                                      No arguments
                                    </Text>
                                  )}
                                </ExpandableSection>
                              ))}
                            </div>
                          </div>
                        )}
                      </ExpandableSection>
                    </>
                  )}
                  {mcpClient.error && (
                    <Alert
                      variant="danger"
                      title="Connection failed"
                      isInline
                      customIcon={<ExclamationCircleIcon />}
                    >
                      {mcpClient.error}
                      <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                        Make sure the Skillberry Store server is running and the Agent MCP server is started.
                      </div>
                    </Alert>
                  )}
                  <div style={{ marginTop: '0.75rem' }}>
                    <Button
                      variant="link"
                      icon={<UnpluggedIcon />}
                      onClick={() => {
                        mcpClient.disconnect();
                        setIsTestingConnection(false);
                      }}
                    >
                      Disconnect
                    </Button>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          {/* Example Use Cases */}
          <Card>
            <CardTitle>Example Use Cases</CardTitle>
            <CardBody>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', lineHeight: '2' }}>
                <li>"List all tools and their descriptions"</li>
                <li>"Read the code of the calculator tool and add input validation"</li>
                <li>"Create a new tool that fetches weather data from an API"</li>
                <li>"Search for tools related to data processing"</li>
                <li>"Create a skill called 'data-analysis' and add relevant tools to it"</li>
                <li>"Create a VMCP server for the data-analysis skill so I can use it in Claude Code"</li>
                <li>"Look at the execution metrics for the calculator tool and optimize it"</li>
              </ul>
            </CardBody>
          </Card>
        </div>
      </PageSection>
    </>
  );
}
