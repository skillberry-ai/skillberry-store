// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  ButtonVariant,
  Card,
  CardBody,
  EmptyState,
  EmptyStateBody,
  Form,
  FormGroup,
  Label,
  Modal,
  ModalVariant,
  PageSection,
  Spinner,
  TextArea,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {
  Table,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import { externalMcpsApi } from '@/services/api';
import type { ExternalMCPStatus } from '@/services/api';

const SAMPLE_CONFIG = `{
  "mcpServers": {
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}`;

export function ExternalMCPsPage() {
  const navigate = useNavigate();
  const [servers, setServers] = useState<ExternalMCPStatus[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [listError, setListError] = useState<string | null>(null);

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [configText, setConfigText] = useState(SAMPLE_CONFIG);
  const [adding, setAdding] = useState(false);
  const [addResult, setAddResult] = useState<string | null>(null);
  const [addError, setAddError] = useState<string | null>(null);

  const [removingName, setRemovingName] = useState<string | null>(null);
  const [restartingName, setRestartingName] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setListError(null);
    try {
      const list = await externalMcpsApi.list();
      setServers(list);
    } catch (e) {
      setListError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleAdd() {
    setAdding(true);
    setAddError(null);
    setAddResult(null);
    try {
      const parsed = JSON.parse(configText);
      const res = await externalMcpsApi.create(parsed);
      const lines = (res.results || []).map((r) => {
        if (r.status === 'running') {
          const n = r.reconcile?.added?.length ?? 0;
          return `✅ ${r.name}: running (${n} primitives imported)`;
        }
        return `❌ ${r.name}: ${r.status}${r.error ? ' — ' + r.error : ''}`;
      });
      setAddResult(lines.join('\n'));
      await refresh();
    } catch (e) {
      setAddError(e instanceof Error ? e.message : String(e));
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(name: string) {
    if (!window.confirm(`Remove MCP server '${name}'? All its primitive tools will be deleted; composites that depend on it will be marked broken.`)) {
      return;
    }
    setRemovingName(name);
    try {
      await externalMcpsApi.remove(name);
      await refresh();
    } catch (e) {
      window.alert(`Remove failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setRemovingName(null);
    }
  }

  async function handleRestart(name: string) {
    setRestartingName(name);
    try {
      await externalMcpsApi.restart(name);
      await refresh();
    } catch (e) {
      window.alert(`Restart failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setRestartingName(null);
    }
  }

  const brokenBanner = useMemo(() => {
    const errored = servers.filter((s) => s.status === 'error');
    if (errored.length === 0) return null;
    return (
      <Alert variant="warning" title={`${errored.length} external MCP server(s) in error state`} isInline>
        Composites depending on these servers are marked <code>state=broken</code>. Fix the config and restart.
      </Alert>
    );
  }, [servers]);

  return (
    <PageSection>
      <Title headingLevel="h1" size="2xl">External MCPs</Title>
      <p style={{ marginTop: '0.5rem', marginBottom: '1rem', color: 'var(--pf-v5-global--Color--200)' }}>
        MCP servers the store connects to and imports tools from. Paste any
        standard <code>mcpServers</code> config (Claude Desktop style).
      </p>

      {brokenBanner}

      <Toolbar>
        <ToolbarContent>
          <ToolbarItem>
            <Button variant="primary" onClick={() => setIsAddOpen(true)}>
              Add External MCP
            </Button>
          </ToolbarItem>
          <ToolbarItem>
            <Button variant="link" onClick={refresh} isDisabled={loading}>
              Refresh
            </Button>
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>

      {listError && (
        <Alert variant="danger" title="Failed to load external MCPs" isInline>
          {listError}
        </Alert>
      )}

      <Card>
        <CardBody>
          {loading ? (
            <Spinner aria-label="loading" />
          ) : servers.length === 0 ? (
            <EmptyState>
              <Title headingLevel="h4" size="lg">No external MCP servers yet</Title>
              <EmptyStateBody>
                Click <strong>Add External MCP</strong> above to register one. Every
                exposed tool will be imported as a primitive named{' '}
                <code>&lt;server&gt;__&lt;tool&gt;</code>.
              </EmptyStateBody>
            </EmptyState>
          ) : (
            <Table aria-label="External MCP servers">
              <Thead>
                <Tr>
                  <Th>Name</Th>
                  <Th>Transport</Th>
                  <Th>Status</Th>
                  <Th>Primitives</Th>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {servers.map((s) => (
                  <Tr key={s.name}>
                    <Td>
                      <Button
                        variant="link"
                        isInline
                        onClick={() => navigate(`/external-mcps/${encodeURIComponent(s.name)}`)}
                      >
                        {s.name}
                      </Button>
                    </Td>
                    <Td>{s.transport}</Td>
                    <Td>
                      <Label color={s.status === 'running' ? 'green' : s.status === 'error' ? 'red' : 'grey'}>
                        {s.status}
                      </Label>
                      {s.last_error && (
                        <div style={{ fontSize: '0.8em', color: 'var(--pf-v5-global--danger-color--100)' }}>
                          {s.last_error}
                        </div>
                      )}
                    </Td>
                    <Td>{s.tool_count}</Td>
                    <Td>
                      <Button
                        variant={ButtonVariant.secondary}
                        size="sm"
                        onClick={() => handleRestart(s.name)}
                        isDisabled={restartingName === s.name}
                        style={{ marginRight: '0.5rem' }}
                      >
                        {restartingName === s.name ? 'Restarting…' : 'Restart'}
                      </Button>
                      <Button
                        variant={ButtonVariant.danger}
                        size="sm"
                        onClick={() => handleRemove(s.name)}
                        isDisabled={removingName === s.name}
                      >
                        {removingName === s.name ? 'Removing…' : 'Remove'}
                      </Button>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      <Modal
        variant={ModalVariant.large}
        title="Add External MCP Server(s)"
        isOpen={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        actions={[
          <Button key="add" variant="primary" onClick={handleAdd} isDisabled={adding}>
            {adding ? 'Adding…' : 'Add'}
          </Button>,
          <Button key="close" variant="link" onClick={() => setIsAddOpen(false)}>
            Close
          </Button>,
        ]}
      >
        <Form>
          <FormGroup
            label="Paste mcpServers JSON"
            fieldId="mcp-config-json"
          >
            <TextArea
              id="mcp-config-json"
              value={configText}
              onChange={(_e, v) => setConfigText(v)}
              rows={14}
              resizeOrientation="vertical"
              aria-label="mcpServers JSON"
              style={{ fontFamily: 'monospace' }}
            />
            <div style={{ marginTop: '0.25rem', fontSize: '0.85em', color: '#6a6e73' }}>
              Accepts the Claude-Desktop-style <code>{'{ mcpServers: {...} }'}</code> wrapper, a
              bare name→entry dict, a list form, a single entry, or{' '}
              <code>{'{ source_url: "..." }'}</code> to fetch a config.
            </div>
          </FormGroup>
          {addError && (
            <Alert variant="danger" title="Add failed" isInline>
              {addError}
            </Alert>
          )}
          {addResult && (
            <Alert variant="info" title="Result" isInline>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{addResult}</pre>
            </Alert>
          )}
        </Form>
      </Modal>
    </PageSection>
  );
}
