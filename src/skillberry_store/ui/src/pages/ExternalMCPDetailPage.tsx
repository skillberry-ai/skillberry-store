// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Breadcrumb,
  BreadcrumbItem,
  Button,
  ButtonVariant,
  Card,
  CardBody,
  CardTitle,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
  Label,
  List,
  ListItem,
  PageSection,
  Spinner,
  Title,
} from '@patternfly/react-core';
import { externalMcpsApi } from '@/services/api';
import type { ExternalMCPStatus } from '@/services/api';

export function ExternalMCPDetailPage() {
  const { name: rawName } = useParams<{ name: string }>();
  const name = decodeURIComponent(rawName ?? '');
  const navigate = useNavigate();

  const [server, setServer] = useState<ExternalMCPStatus | null>(null);
  const [dependents, setDependents] = useState<string[]>([]);
  const [remoteTools, setRemoteTools] = useState<Array<{ name: string; description: string }> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restarting, setRestarting] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [s, deps] = await Promise.all([
        externalMcpsApi.get(name),
        externalMcpsApi.dependents(name).catch(() => ({ name, dependents: [] })),
      ]);
      setServer(s);
      setDependents(deps.dependents || []);
      if (s.status === 'running') {
        try {
          setRemoteTools(await externalMcpsApi.listRemoteTools(name));
        } catch {
          setRemoteTools(null);
        }
      } else {
        setRemoteTools(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (name) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  async function handleRestart() {
    setRestarting(true);
    try {
      await externalMcpsApi.restart(name);
      await refresh();
    } catch (e) {
      window.alert(`Restart failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setRestarting(false);
    }
  }

  return (
    <PageSection>
      <Breadcrumb>
        <BreadcrumbItem onClick={() => navigate('/external-mcps')} to="#">
          External MCPs
        </BreadcrumbItem>
        <BreadcrumbItem isActive>{name}</BreadcrumbItem>
      </Breadcrumb>

      <Title headingLevel="h1" size="2xl" style={{ marginTop: '1rem' }}>
        {name}
      </Title>

      {error && (
        <Alert variant="danger" title="Failed to load" isInline>
          {error}
        </Alert>
      )}

      {loading || !server ? (
        <Spinner aria-label="loading" />
      ) : (
        <>
          <Card style={{ marginTop: '1rem' }}>
            <CardTitle>Status</CardTitle>
            <CardBody>
              <DescriptionList isCompact>
                <DescriptionListGroup>
                  <DescriptionListTerm>Status</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Label color={server.status === 'running' ? 'green' : server.status === 'error' ? 'red' : 'grey'}>
                      {server.status}
                    </Label>
                    {server.last_error && (
                      <div style={{ marginTop: '0.25rem', color: 'var(--pf-v5-global--danger-color--100)' }}>
                        {server.last_error}
                      </div>
                    )}
                  </DescriptionListDescription>
                </DescriptionListGroup>
                <DescriptionListGroup>
                  <DescriptionListTerm>Transport</DescriptionListTerm>
                  <DescriptionListDescription>{server.transport}</DescriptionListDescription>
                </DescriptionListGroup>
                <DescriptionListGroup>
                  <DescriptionListTerm>Primitives imported</DescriptionListTerm>
                  <DescriptionListDescription>{server.tool_count}</DescriptionListDescription>
                </DescriptionListGroup>
                {server.transport === 'stdio' && (
                  <DescriptionListGroup>
                    <DescriptionListTerm>Command</DescriptionListTerm>
                    <DescriptionListDescription>
                      <code>{server.config.command} {(server.config.args || []).join(' ')}</code>
                    </DescriptionListDescription>
                  </DescriptionListGroup>
                )}
                {server.transport !== 'stdio' && (
                  <DescriptionListGroup>
                    <DescriptionListTerm>URL</DescriptionListTerm>
                    <DescriptionListDescription><code>{server.config.url}</code></DescriptionListDescription>
                  </DescriptionListGroup>
                )}
              </DescriptionList>
              <Button
                variant={ButtonVariant.secondary}
                onClick={handleRestart}
                isDisabled={restarting}
                style={{ marginTop: '1rem' }}
              >
                {restarting ? 'Restarting…' : 'Restart (reconcile)'}
              </Button>
            </CardBody>
          </Card>

          <Card style={{ marginTop: '1rem' }}>
            <CardTitle>Remote tools</CardTitle>
            <CardBody>
              {remoteTools === null ? (
                <span style={{ color: 'var(--pf-v5-global--Color--200)' }}>
                  Server not running — introspection unavailable.
                </span>
              ) : remoteTools.length === 0 ? (
                <span>No remote tools reported.</span>
              ) : (
                <List>
                  {remoteTools.map((t) => (
                    <ListItem key={t.name}>
                      <Button
                        variant="link"
                        isInline
                        onClick={() => navigate(`/tools/${encodeURIComponent(`${name}__${t.name}`)}`)}
                      >
                        <code>{name}__{t.name}</code>
                      </Button>
                      {t.description && <span> — {t.description}</span>}
                    </ListItem>
                  ))}
                </List>
              )}
            </CardBody>
          </Card>

          <Card style={{ marginTop: '1rem' }}>
            <CardTitle>Dependents (will break if this server is removed)</CardTitle>
            <CardBody>
              {dependents.length === 0 ? (
                <span>None.</span>
              ) : (
                <List>
                  {dependents.map((d) => (
                    <ListItem key={d}>
                      <Button variant="link" isInline onClick={() => navigate(`/tools/${encodeURIComponent(d)}`)}>
                        {d}
                      </Button>
                    </ListItem>
                  ))}
                </List>
              )}
            </CardBody>
          </Card>
        </>
      )}
    </PageSection>
  );
}
