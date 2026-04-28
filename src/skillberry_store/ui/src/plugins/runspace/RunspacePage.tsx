// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PageSection,
  Card,
  CardBody,
  Title,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  Button,
  Alert,
  Divider,
  Spinner,
  Tabs,
  Tab,
  TabTitleText,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  ExpandableSection,
  Label,
  Text,
} from '@patternfly/react-core';
import {
  TrashIcon,
  PlusCircleIcon,
  ExternalLinkAltIcon,
  AutomationIcon,
  FolderOpenIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@patternfly/react-icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  runspaceSettingsApi,
  runspaceAgentApi,
  DEFAULT_RUNSPACE_URL,
  type AiSettingsEnvVar,
} from './api';

const VALUE_PLACEHOLDERS: Record<string, string> = {
  ANTHROPIC_AUTH_TOKEN: 'your-auth-token',
  ANTHROPIC_BASE_URL: 'https://your-anthropic-base-url',
};

interface SessionDetail {
  session_id: string;
  status: string;
  total_tokens?: number;
  total_cost_usd?: number | null;
  duration_seconds?: number | null;
  error?: string | null;
  has_summary?: boolean;
}

export function RunspacePage() {
  const navigate = useNavigate();
  const [activeTabKey, setActiveTabKey] = useState(0);

  const [runspaceUrl, setRunspaceUrl] = useState(DEFAULT_RUNSPACE_URL);
  const [envVars, setEnvVars] = useState<AiSettingsEnvVar[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [savedMessage, setSavedMessage] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const saveTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debounceTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isLoaded = useRef(false);

  const [isEnvVarsExpanded, setIsEnvVarsExpanded] = useState(false);
  const [visibleValues, setVisibleValues] = useState<Set<number>>(new Set());

  const stored = useRef(() => {
    try {
      const raw = sessionStorage.getItem('storeAgentSession');
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  }).current();

  const [agentPrompt, setAgentPrompt] = useState(stored?.prompt || '');
  const [contextFiles, setContextFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isSendingAgent, setIsSendingAgent] = useState(false);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [agentSessionId, setAgentSessionId] = useState<string | null>(stored?.sessionId || null);
  const [agentSessionDetail, setAgentSessionDetail] = useState<SessionDetail | null>(stored?.detail || null);
  const [agentSummary, setAgentSummary] = useState<string | null>(stored?.summary || null);

  const agentSessionStatus = agentSessionDetail?.status || null;

  useEffect(() => {
    const data: Record<string, any> = {};
    if (agentSessionId) data.sessionId = agentSessionId;
    if (agentSessionDetail) data.detail = agentSessionDetail;
    if (agentSummary) data.summary = agentSummary;
    if (agentPrompt && agentSessionId) data.prompt = agentPrompt;
    if (Object.keys(data).length > 0) {
      sessionStorage.setItem('storeAgentSession', JSON.stringify(data));
    } else {
      sessionStorage.removeItem('storeAgentSession');
    }
  }, [agentSessionId, agentSessionDetail, agentSummary, agentPrompt]);

  useEffect(() => {
    runspaceSettingsApi
      .get()
      .then((data) => {
        setRunspaceUrl(data.runspace_url || DEFAULT_RUNSPACE_URL);
        setEnvVars(
          (data.env_vars || []).map((v) => ({
            key: v.key,
            value: v.value.startsWith('<') && v.value.endsWith('>') ? '' : v.value,
          }))
        );
        isLoaded.current = true;
      })
      .catch((err) => {
        setSettingsError(`Failed to load settings: ${err.message}`);
        isLoaded.current = true;
      })
      .finally(() => setIsLoading(false));
  }, []);

  const saveToBackend = useCallback(
    (url: string, vars: AiSettingsEnvVar[]) => {
      if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
      debounceTimeout.current = setTimeout(() => {
        runspaceSettingsApi
          .save({ runspace_url: url, env_vars: vars })
          .then(() => {
            setSavedMessage(true);
            if (saveTimeout.current) clearTimeout(saveTimeout.current);
            saveTimeout.current = setTimeout(() => setSavedMessage(false), 2000);
          })
          .catch((err) => setSettingsError(`Failed to save: ${err.message}`));
      }, 500);
    },
    []
  );

  useEffect(() => {
    if (!isLoaded.current) return;
    saveToBackend(runspaceUrl, envVars);
  }, [runspaceUrl, envVars, saveToBackend]);

  const handleEnvKeyChange = (index: number, value: string) => {
    setEnvVars((prev) => prev.map((v, i) => (i === index ? { ...v, key: value } : v)));
  };

  const handleEnvValueChange = (index: number, value: string) => {
    setEnvVars((prev) => prev.map((v, i) => (i === index ? { ...v, value: value } : v)));
  };

  const handleAddVar = () => {
    setEnvVars((prev) => [...prev, { key: '', value: '' }]);
  };

  const handleRemoveVar = (index: number) => {
    setEnvVars((prev) => prev.filter((_, i) => i !== index));
  };

  const handleResetDefaults = () => {
    setRunspaceUrl(DEFAULT_RUNSPACE_URL);
    setIsLoading(true);
    runspaceSettingsApi
      .save({ runspace_url: DEFAULT_RUNSPACE_URL, env_vars: [] })
      .then(() => runspaceSettingsApi.get())
      .then((data) => {
        setRunspaceUrl(data.runspace_url || DEFAULT_RUNSPACE_URL);
        setEnvVars(
          (data.env_vars || []).map((v) => ({
            key: v.key,
            value: v.value.startsWith('<') && v.value.endsWith('>') ? '' : v.value,
          }))
        );
      })
      .catch((err) => setSettingsError(`Failed to reset: ${err.message}`))
      .finally(() => setIsLoading(false));
  };

  const handleRunAgent = async () => {
    if (!agentPrompt.trim()) return;
    setIsSendingAgent(true);
    setAgentError(null);
    setAgentSessionId(null);
    setAgentSessionDetail(null);
    setAgentSummary(null);

    try {
      const requestBody = await runspaceAgentApi.buildStoreRequest(agentPrompt, contextFiles.length > 0 ? contextFiles : undefined);
      const agentRunspaceUrl = requestBody._runspace_url || runspaceUrl;
      delete requestBody._runspace_url;

      const resp = await fetch(`${agentRunspaceUrl}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText || `Server returned ${resp.status}`);
      }

      const data = await resp.json();
      setAgentSessionId(data.session_id);
      setAgentSessionDetail({ session_id: data.session_id, status: data.status || 'pending' });
    } catch (err: any) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setAgentError(
          `Could not reach Runspace at ${runspaceUrl}. ` +
          'Make sure the server is running (runspace-srv).'
        );
      } else {
        setAgentError(`Failed to run agent: ${err.message}`);
      }
    } finally {
      setIsSendingAgent(false);
    }
  };

  useEffect(() => {
    if (!agentSessionId || !runspaceUrl) return;
    if (agentSessionStatus === 'completed' || agentSessionStatus === 'failed') return;

    const agentRunspaceUrl = runspaceUrl;
    const poll = async () => {
      try {
        const resp = await fetch(`${agentRunspaceUrl}/sessions/${agentSessionId}`);
        if (resp.ok) {
          const data: SessionDetail = await resp.json();
          setAgentSessionDetail(data);
        }
      } catch {
        // Non-fatal during polling
      }
    };

    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, [agentSessionId, agentSessionStatus, runspaceUrl]);

  useEffect(() => {
    if (agentSessionStatus !== 'completed' || !agentSessionId || !runspaceUrl) return;
    if (agentSummary !== null) return;

    fetch(`${runspaceUrl}/sessions/${agentSessionId}/summary`)
      .then((resp) => {
        if (resp.ok) return resp.text();
        return null;
      })
      .then((text) => {
        if (!text) return;
        try {
          const parsed = JSON.parse(text);
          setAgentSummary(parsed.content || text);
        } catch {
          setAgentSummary(text);
        }
      })
      .catch(() => {});
  }, [agentSessionStatus, agentSessionId, runspaceUrl, agentSummary]);

  const formatDuration = (seconds: number | null | undefined) => {
    if (seconds == null) return '-';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(0);
    return `${mins}m ${secs}s`;
  };

  const getStatusVariant = () => {
    switch (agentSessionStatus) {
      case 'completed': return 'success' as const;
      case 'failed': return 'danger' as const;
      default: return 'info' as const;
    }
  };

  const handleNewAgentSession = () => {
    setAgentPrompt('');
    setContextFiles([]);
    setAgentSessionId(null);
    setAgentSessionDetail(null);
    setAgentSummary(null);
    setAgentError(null);
    sessionStorage.removeItem('storeAgentSession');
  };

  if (isLoading) {
    return (
      <PageSection style={{ textAlign: 'center', paddingTop: '4rem' }}>
        <Spinner size="xl" />
      </PageSection>
    );
  }

  return (
    <>
      <PageSection>
        <Title headingLevel="h1" size="2xl">
          Runspace
        </Title>
        <div style={{ marginTop: '0.5rem', fontSize: '0.925rem', color: '#6a6e73' }}>
          Build and export agents via the Runspace daemon (runspace-srv). Configure settings
          or chat with the Runspace Store Agent to create tools, skills, and VMCP servers on your behalf.
        </div>
      </PageSection>

      <PageSection>
        <Tabs activeKey={activeTabKey} onSelect={(_, tabIndex) => setActiveTabKey(tabIndex as number)}>
          <Tab eventKey={0} title={<TabTitleText>Settings</TabTitleText>}>
            <Card style={{ marginTop: '1rem' }}>
              <CardBody>
                {savedMessage && (
                  <Alert variant="success" title="Settings saved" isInline isPlain style={{ marginBottom: '1rem' }} />
                )}
                {settingsError && (
                  <Alert variant="danger" title={settingsError} isInline style={{ marginBottom: '1rem' }} />
                )}

                <Title headingLevel="h2" size="lg" style={{ marginBottom: '0.5rem' }}>
                  Runspace Configuration
                </Title>
                <Alert variant="info" title="Runspace Agent Server" isInline isPlain style={{ marginBottom: '1rem' }}>
                  The Runspace URL is the address of your Runspace server. You need to run{' '}
                  <code>runspace-srv</code> from the runspace project so your agent is up and running.
                </Alert>
                <Form>
                  <FormGroup label="Runspace URL" fieldId="runspace-url">
                    <TextInput
                      type="text"
                      id="runspace-url"
                      value={runspaceUrl}
                      onChange={(_event, value) => setRunspaceUrl(value)}
                      placeholder={DEFAULT_RUNSPACE_URL}
                    />
                  </FormGroup>
                </Form>

                <Divider style={{ margin: '1.5rem 0' }} />

                <ExpandableSection
                  toggleText={`Agent Environment Variables (${envVars.length})`}
                  isExpanded={isEnvVarsExpanded}
                  onToggle={(_event, expanded) => setIsEnvVarsExpanded(expanded)}
                >
                  <Alert variant="info" title="Environment for Claude Code Agent" isInline isPlain style={{ marginBottom: '1rem' }}>
                    These environment variables are passed to the Claude Code agent running in the Runspace.
                  </Alert>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                      <div style={{ flex: 1, fontWeight: 600, fontSize: '0.875rem' }}>Variable Name</div>
                      <div style={{ flex: 1, fontWeight: 600, fontSize: '0.875rem' }}>Value</div>
                      <div style={{ width: '72px' }} />
                    </div>
                    {envVars.map((envVar, index) => (
                      <div key={index} style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                        <TextInput
                          type="text"
                          aria-label={`Variable name ${index}`}
                          value={envVar.key}
                          onChange={(_event, value) => handleEnvKeyChange(index, value)}
                          placeholder="VARIABLE_NAME"
                          style={{ flex: 1 }}
                        />
                        <TextInput
                          type={visibleValues.has(index) ? 'text' : 'password'}
                          aria-label={`Variable value ${index}`}
                          value={envVar.value}
                          onChange={(_event, value) => handleEnvValueChange(index, value)}
                          placeholder={VALUE_PLACEHOLDERS[envVar.key] || 'value'}
                          style={{ flex: 1 }}
                        />
                        <Button
                          variant="plain"
                          aria-label={visibleValues.has(index) ? `Hide value ${envVar.key || index}` : `Show value ${envVar.key || index}`}
                          onClick={() => setVisibleValues((prev) => {
                            const next = new Set(prev);
                            if (next.has(index)) next.delete(index); else next.add(index);
                            return next;
                          })}
                        >
                          {visibleValues.has(index) ? <EyeSlashIcon /> : <EyeIcon />}
                        </Button>
                        <Button variant="plain" aria-label={`Remove variable ${envVar.key || index}`} onClick={() => handleRemoveVar(index)}>
                          <TrashIcon />
                        </Button>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                    <Button variant="secondary" icon={<PlusCircleIcon />} onClick={handleAddVar}>
                      Add Variable
                    </Button>
                    <Button variant="tertiary" onClick={handleResetDefaults}>
                      Reset to Defaults
                    </Button>
                  </div>
                </ExpandableSection>
              </CardBody>
            </Card>
          </Tab>

          <Tab eventKey={1} title={<TabTitleText>Runspace Store Agent</TabTitleText>}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
              <Alert variant="info" title="Runspace Store Agent" isInline isPlain style={{ marginTop: '0.25rem' }}>
                The Runspace Store Agent is a Claude Code agent that runs securely in a Docker container via Runspace,
                already connected to the Store MCP. It can create tools, skills, snippets, and VMCP servers on your behalf.
                To connect your own agent directly, see the <Button variant="link" isInline onClick={() => navigate('/agent-connect')}>Connect Your Agent</Button> page.
              </Alert>

              <div>
                <Text component="small" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block', color: '#6a6e73' }}>
                  Try an example:
                </Text>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {[
                    'Create an MCP for math operations with add, subtract, multiply, and divide tools',
                    'Create a skill called "data-processing" with tools for CSV parsing, JSON validation, and text cleanup',
                    'Remove tool "old-calculator" from skill "math-ops"',
                    'List all tools and find any that are duplicates or overlap in functionality',
                    'Optimize skill "web-scraper" based on the execution traces I added as context',
                    'Read the code of tool "api-fetcher" and add proper error handling and retries',
                    'Create a VMCP server for skill "dev-tools" so I can use it in Claude Code',
                  ].map((example) => (
                    <Label
                      key={example}
                      color="blue"
                      style={{
                        cursor: (agentSessionStatus === 'running' || agentSessionStatus === 'pending') ? 'default' : 'pointer',
                        opacity: (agentSessionStatus === 'running' || agentSessionStatus === 'pending') ? 0.6 : 1,
                      }}
                      onClick={!(agentSessionStatus === 'running' || agentSessionStatus === 'pending') ? () => { handleNewAgentSession(); setAgentPrompt(example); } : undefined}
                    >
                      {example.length > 65 ? example.slice(0, 62) + '...' : example}
                    </Label>
                  ))}
                </div>
              </div>

              <Card>
                <CardBody>
                  <Form>
                    <FormGroup label="What would you like the agent to do?" fieldId="agent-prompt">
                      <TextArea
                        id="agent-prompt"
                        value={agentPrompt}
                        onChange={(_event, value) => setAgentPrompt(value)}
                        placeholder="e.g., Create me an MCP for math operations with add, subtract, multiply, and divide tools"
                        rows={4}
                        isDisabled={!!agentSessionId && agentSessionStatus !== 'completed' && agentSessionStatus !== 'failed'}
                        resizeOrientation="vertical"
                      />
                    </FormGroup>

                    <FormGroup label="Context Files (optional)" fieldId="context-files">
                      <div style={{ fontSize: '0.85rem', color: '#6a6e73', marginBottom: '0.5rem' }}>
                        Upload files to give the agent additional context (e.g., requirements, specs, code samples).
                      </div>
                      <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        style={{ display: 'none' }}
                        onChange={(e) => {
                          if (e.target.files) {
                            setContextFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
                            e.target.value = '';
                          }
                        }}
                        disabled={!!agentSessionId && agentSessionStatus !== 'completed' && agentSessionStatus !== 'failed'}
                      />
                      <Button
                        variant="secondary"
                        icon={<FolderOpenIcon />}
                        onClick={() => fileInputRef.current?.click()}
                        isDisabled={!!agentSessionId && agentSessionStatus !== 'completed' && agentSessionStatus !== 'failed'}
                        size="sm"
                      >
                        Add Files
                      </Button>
                      {contextFiles.length > 0 && (
                        <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                          {contextFiles.map((file, idx) => (
                            <Label
                              key={`${file.name}-${idx}`}
                              color="blue"
                              onClose={(!agentSessionId || agentSessionStatus === 'completed' || agentSessionStatus === 'failed') ? () => setContextFiles((prev) => prev.filter((_, i) => i !== idx)) : undefined}
                            >
                              {file.name} ({(file.size / 1024).toFixed(1)} KB)
                            </Label>
                          ))}
                        </div>
                      )}
                    </FormGroup>
                  </Form>

                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                    {!agentSessionId || agentSessionStatus === 'completed' || agentSessionStatus === 'failed' ? (
                      <Button
                        variant="primary"
                        icon={<AutomationIcon />}
                        onClick={handleRunAgent}
                        isLoading={isSendingAgent}
                        isDisabled={!agentPrompt.trim() || isSendingAgent}
                      >
                        {isSendingAgent ? 'Sending...' : 'Run Agent'}
                      </Button>
                    ) : (
                      <Button
                        variant="secondary"
                        onClick={handleNewAgentSession}
                        isDisabled={agentSessionStatus !== 'completed' && agentSessionStatus !== 'failed'}
                      >
                        New Session
                      </Button>
                    )}
                  </div>
                </CardBody>
              </Card>

              {agentError && (
                <Alert variant="danger" title="Error" isInline>
                  {agentError}
                </Alert>
              )}

              {agentSessionDetail && (
                <Alert variant={getStatusVariant()} title={`Session: ${agentSessionStatus}`} isInline>
                  <DescriptionList isCompact isHorizontal style={{ marginTop: '0.5rem' }}>
                    <DescriptionListGroup>
                      <DescriptionListTerm>Session ID</DescriptionListTerm>
                      <DescriptionListDescription>
                        <code style={{ fontSize: '0.85rem' }}>{agentSessionDetail.session_id}</code>
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                    {agentSessionDetail.duration_seconds != null && (
                      <DescriptionListGroup>
                        <DescriptionListTerm>Duration</DescriptionListTerm>
                        <DescriptionListDescription>{formatDuration(agentSessionDetail.duration_seconds)}</DescriptionListDescription>
                      </DescriptionListGroup>
                    )}
                    {agentSessionDetail.total_tokens != null && agentSessionDetail.total_tokens > 0 && (
                      <DescriptionListGroup>
                        <DescriptionListTerm>Tokens</DescriptionListTerm>
                        <DescriptionListDescription>{agentSessionDetail.total_tokens.toLocaleString()}</DescriptionListDescription>
                      </DescriptionListGroup>
                    )}
                    {agentSessionDetail.total_cost_usd != null && (
                      <DescriptionListGroup>
                        <DescriptionListTerm>Cost</DescriptionListTerm>
                        <DescriptionListDescription>${agentSessionDetail.total_cost_usd.toFixed(4)}</DescriptionListDescription>
                      </DescriptionListGroup>
                    )}
                    {agentSessionDetail.error && (
                      <DescriptionListGroup>
                        <DescriptionListTerm>Error</DescriptionListTerm>
                        <DescriptionListDescription style={{ color: '#c9190b' }}>{agentSessionDetail.error}</DescriptionListDescription>
                      </DescriptionListGroup>
                    )}
                  </DescriptionList>

                  {agentSessionStatus !== 'completed' && agentSessionStatus !== 'failed' && (
                    <div style={{ marginTop: '0.75rem' }}>
                      <Spinner size="sm" /> Polling for status...
                    </div>
                  )}

                  <div style={{ marginTop: '0.75rem' }}>
                    <a
                      href={`${runspaceUrl}/ui/sessions/${agentSessionId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <ExternalLinkAltIcon /> Open in Runspace UI
                    </a>
                  </div>
                </Alert>
              )}

              {agentSummary && (
                <Card>
                  <CardBody>
                    <Title headingLevel="h3" size="md" style={{ marginBottom: '1rem' }}>
                      Agent Summary
                    </Title>
                    <div className="markdown-body" style={{
                      padding: '1rem',
                      backgroundColor: '#f5f5f5',
                      borderRadius: '6px',
                      border: '1px solid #d2d2d2',
                      lineHeight: '1.6',
                    }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{agentSummary}</ReactMarkdown>
                    </div>
                  </CardBody>
                </Card>
              )}
            </div>
          </Tab>
        </Tabs>
      </PageSection>
    </>
  );
}
