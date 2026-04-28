// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  Alert,
  Spinner,
  ClipboardCopy,
  ClipboardCopyVariant,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
} from '@patternfly/react-core';
import { DownloadIcon, ExternalLinkAltIcon } from '@patternfly/react-icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  runspaceSettingsApi,
  runspaceSkillApi,
  envVarsToRecord,
} from './api';

interface AgenticExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  skillName: string;
}

interface SessionDetail {
  session_id: string;
  status: string;
  total_tokens?: number;
  total_cost_usd?: number | null;
  duration_seconds?: number | null;
  error?: string | null;
  has_summary?: boolean;
}

export function AgenticExportModal({
  isOpen,
  onClose,
  skillName,
}: AgenticExportModalProps) {
  const [runspaceUrl, setRunspaceUrl] = useState('http://localhost:6767');
  const [requestBody, setRequestBody] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null);
  const [summary, setSummary] = useState<string | null>(null);

  const sessionStatus = sessionDetail?.status || null;

  const resetState = useCallback(() => {
    setRequestBody('');
    setError(null);
    setSessionId(null);
    setSessionDetail(null);
    setSummary(null);
    setIsSending(false);
  }, []);

  useEffect(() => {
    if (!isOpen || !skillName) return;
    resetState();
    setIsLoading(true);

    Promise.all([
      runspaceSkillApi.exportAgentRequest(skillName),
      runspaceSettingsApi.get(),
    ])
      .then(([data, settings]) => {
        if (settings.runspace_url) {
          setRunspaceUrl(settings.runspace_url);
        }
        if (data.agent_settings) {
          data.agent_settings.env = envVarsToRecord(settings.env_vars || []);
        }
        setRequestBody(JSON.stringify(data, null, 2));
      })
      .catch((err) => {
        setError(`Failed to build request: ${err.message}`);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isOpen, skillName, resetState]);

  useEffect(() => {
    if (!sessionId || !runspaceUrl) return;
    if (sessionStatus === 'completed' || sessionStatus === 'failed') return;

    const poll = async () => {
      try {
        const resp = await fetch(`${runspaceUrl}/sessions/${sessionId}`);
        if (resp.ok) {
          const data: SessionDetail = await resp.json();
          setSessionDetail(data);
        }
      } catch {
        // Network errors during polling are non-fatal
      }
    };

    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, [sessionId, sessionStatus, runspaceUrl]);

  useEffect(() => {
    if (sessionStatus !== 'completed' || !sessionId || !runspaceUrl) return;
    if (summary !== null) return;

    fetch(`${runspaceUrl}/sessions/${sessionId}/summary`)
      .then((resp) => {
        if (resp.ok) return resp.text();
        return null;
      })
      .then((text) => {
        if (!text) return;
        try {
          const parsed = JSON.parse(text);
          setSummary(parsed.content || text);
        } catch {
          setSummary(text);
        }
      })
      .catch(() => {});
  }, [sessionStatus, sessionId, runspaceUrl, summary]);

  const handleSend = async () => {
    setIsSending(true);
    setError(null);

    try {
      const parsed = JSON.parse(requestBody);
      const resp = await fetch(`${runspaceUrl}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText || `Server returned ${resp.status}`);
      }

      const data = await resp.json();
      setSessionId(data.session_id);
      setSessionDetail({ session_id: data.session_id, status: data.status || 'pending' });
    } catch (err: any) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError(
          `Could not reach Runspace at ${runspaceUrl}. ` +
            'Make sure the server is running and CORS is enabled. ' +
            'You can use "Copy as cURL" as a fallback.'
        );
      } else {
        setError(`Failed to send: ${err.message}`);
      }
    } finally {
      setIsSending(false);
    }
  };

  const handleDownloadEditable = () => {
    if (!sessionId || !runspaceUrl) return;
    window.open(`${runspaceUrl}/sessions/${sessionId}/editable.zip`, '_blank');
  };

  const buildCurlCommand = () => {
    const body = requestBody.replace(/'/g, "'\\''");
    return `curl -X POST ${runspaceUrl}/run \\\n  -H "Content-Type: application/json" \\\n  -d '${body}'`;
  };

  const handleClose = () => {
    if (!isSending) {
      resetState();
      onClose();
    }
  };

  const getStatusVariant = () => {
    switch (sessionStatus) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'danger';
      case 'running':
        return 'info';
      default:
        return 'info';
    }
  };

  const formatDuration = (seconds: number | null | undefined) => {
    if (seconds == null) return '-';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(0);
    return `${mins}m ${secs}s`;
  };

  return (
    <Modal
      variant={ModalVariant.large}
      title="Export with Runspace Agent"
      isOpen={isOpen}
      onClose={handleClose}
      actions={[
        ...(sessionStatus === 'completed'
          ? [
              <Button
                key="download"
                variant="primary"
                icon={<DownloadIcon />}
                onClick={handleDownloadEditable}
              >
                Download Result
              </Button>,
            ]
          : [
              <Button
                key="send"
                variant="primary"
                onClick={handleSend}
                isDisabled={isLoading || isSending || !requestBody || !!sessionId}
              >
                {isSending ? (
                  <>
                    <Spinner size="md" /> Sending...
                  </>
                ) : (
                  'Send to Agent'
                )}
              </Button>,
            ]),
        <Button key="close" variant="link" onClick={handleClose} isDisabled={isSending}>
          {sessionId ? 'Close' : 'Cancel'}
        </Button>,
      ]}
    >
      <Form>
        <FormGroup label="Runspace URL" isRequired fieldId="runspace-url">
          <TextInput
            type="text"
            id="runspace-url"
            value={runspaceUrl}
            onChange={(_event, value) => setRunspaceUrl(value)}
            isDisabled={!!sessionId}
            placeholder="http://localhost:6767"
          />
          <div style={{ fontSize: '0.875rem', color: '#6a6e73', marginTop: '0.25rem' }}>
            Start Runspace with: <code>runspace-srv</code>
          </div>
        </FormGroup>

        {!sessionId && (
          <>
            <FormGroup label="Request Body" isRequired fieldId="request-body">
              {isLoading ? (
                <div style={{ textAlign: 'center', padding: '2rem' }}>
                  <Spinner size="lg" />
                  <div style={{ marginTop: '0.5rem' }}>Building request...</div>
                </div>
              ) : (
                <TextArea
                  id="request-body"
                  value={requestBody}
                  onChange={(_event, value) => setRequestBody(value)}
                  rows={20}
                  style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
                  resizeOrientation="vertical"
                />
              )}
              <div style={{ fontSize: '0.875rem', color: '#6a6e73', marginTop: '0.25rem' }}>
                Defines the environment where the Claude Code agent will run.
                Fill in any placeholder values (e.g. <code>ANTHROPIC_AUTH_TOKEN</code>) before sending.
              </div>
            </FormGroup>

            {!isLoading && requestBody && (
              <FormGroup label="Copy as cURL" fieldId="curl-copy">
                <ClipboardCopy
                  isReadOnly
                  hoverTip="Copy"
                  clickTip="Copied"
                  variant={ClipboardCopyVariant.expansion}
                  isExpanded={false}
                >
                  {buildCurlCommand()}
                </ClipboardCopy>
              </FormGroup>
            )}
          </>
        )}

        {error && (
          <Alert variant="danger" title="Error" isInline style={{ marginTop: '1rem' }}>
            {error}
          </Alert>
        )}

        {sessionDetail && (
          <Alert
            variant={getStatusVariant()}
            title={`Session: ${sessionStatus}`}
            isInline
            style={{ marginTop: '1rem' }}
          >
            <DescriptionList isCompact isHorizontal style={{ marginTop: '0.5rem' }}>
              <DescriptionListGroup>
                <DescriptionListTerm>Session ID</DescriptionListTerm>
                <DescriptionListDescription>
                  <code style={{ fontSize: '0.85rem' }}>{sessionDetail.session_id}</code>
                </DescriptionListDescription>
              </DescriptionListGroup>
              {sessionDetail.duration_seconds != null && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Duration</DescriptionListTerm>
                  <DescriptionListDescription>
                    {formatDuration(sessionDetail.duration_seconds)}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
              {sessionDetail.total_tokens != null && sessionDetail.total_tokens > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Tokens</DescriptionListTerm>
                  <DescriptionListDescription>
                    {sessionDetail.total_tokens.toLocaleString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
              {sessionDetail.total_cost_usd != null && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Cost</DescriptionListTerm>
                  <DescriptionListDescription>
                    ${sessionDetail.total_cost_usd.toFixed(4)}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
              {sessionDetail.error && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Error</DescriptionListTerm>
                  <DescriptionListDescription style={{ color: '#c9190b' }}>
                    {sessionDetail.error}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
            </DescriptionList>

            {sessionStatus !== 'completed' && sessionStatus !== 'failed' && (
              <div style={{ marginTop: '0.75rem' }}>
                <Spinner size="sm" /> Polling for status...
              </div>
            )}

            <div style={{ marginTop: '0.75rem' }}>
              <a
                href={`${runspaceUrl}/ui/sessions/${sessionId}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLinkAltIcon /> Open in Runspace UI
              </a>
            </div>
          </Alert>
        )}

        {summary && (
          <FormGroup label="Agent Summary" fieldId="agent-summary" style={{ marginTop: '1rem' }}>
            <div className="markdown-body" style={{
              padding: '1rem',
              background: '#f5f5f5',
              borderRadius: '6px',
              border: '1px solid #d2d2d2',
              maxHeight: '400px',
              overflow: 'auto',
              fontSize: '0.9rem',
              lineHeight: '1.6',
            }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
            </div>
          </FormGroup>
        )}
      </Form>
    </Modal>
  );
}
