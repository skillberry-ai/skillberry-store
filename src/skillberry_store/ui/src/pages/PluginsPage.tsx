// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PageSection,
  Title,
  Card,
  CardBody,
  Switch,
  Spinner,
  Alert,
  Button,
} from '@patternfly/react-core';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from '@patternfly/react-table';
import { pluginsApi, type PluginInfo } from '@/services/api';
import { applyPluginsListFromBackend } from '@/plugins/registry';

export function PluginsPage() {
  const navigate = useNavigate();
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [restartPending, setRestartPending] = useState(false);

  const refresh = async () => {
    try {
      const items = await pluginsApi.list();
      setPlugins(items);
      applyPluginsListFromBackend(items);
    } catch (err: any) {
      setError(err.message || 'Failed to load plugins');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const toggle = async (plugin: PluginInfo) => {
    setPendingId(plugin.id);
    setError(null);
    try {
      const resp = plugin.enabled
        ? await pluginsApi.disable(plugin.id)
        : await pluginsApi.enable(plugin.id);
      if (resp.restart_required) {
        setRestartPending(true);
      }
      await refresh();
    } catch (err: any) {
      setError(err.message || 'Failed to toggle plugin');
    } finally {
      setPendingId(null);
    }
  };

  return (
    <>
      <PageSection>
        <Title headingLevel="h1" size="2xl">Plugins</Title>
        <div style={{ marginTop: '0.5rem', fontSize: '0.925rem', color: '#6a6e73' }}>
          Optional add-ons that extend the Skillberry Store. Enabling or disabling a plugin
          applies immediately unless the plugin declares that a restart is required.
        </div>
      </PageSection>

      <PageSection>
        {restartPending && (
          <Alert
            variant="warning"
            title="Restart required"
            isInline
            style={{ marginBottom: '1rem' }}
          >
            One or more plugins require a store restart for the change to take effect.
          </Alert>
        )}
        {error && (
          <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>
            {error}
          </Alert>
        )}
        <Card>
          <CardBody>
            {isLoading ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}>
                <Spinner size="lg" />
              </div>
            ) : plugins.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#6a6e73' }}>
                No plugins installed.
              </div>
            ) : (
              <Table aria-label="Plugins" variant="compact">
                <Thead>
                  <Tr>
                    <Th>Name</Th>
                    <Th>Description</Th>
                    <Th>Status</Th>
                    <Th>Enabled</Th>
                    <Th>Open</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {plugins.map((p) => {
                    const primaryPath = p.ui_manifest?.nav_items?.[0]?.path;
                    return (
                      <Tr key={p.id}>
                        <Td>
                          <strong>{p.name}</strong>
                          {p.requires_restart && (
                            <div style={{ fontSize: '0.75rem', color: '#6a6e73' }}>
                              Requires restart on toggle
                            </div>
                          )}
                        </Td>
                        <Td>{p.description}</Td>
                        <Td>{p.enabled ? 'Enabled' : 'Disabled'}</Td>
                        <Td>
                          <Switch
                            id={`plugin-toggle-${p.id}`}
                            aria-label={`Toggle ${p.name}`}
                            isChecked={p.enabled}
                            isDisabled={pendingId === p.id}
                            onChange={() => toggle(p)}
                          />
                        </Td>
                        <Td>
                          {p.enabled && primaryPath ? (
                            <Button variant="link" isInline onClick={() => navigate(primaryPath)}>
                              Open
                            </Button>
                          ) : null}
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
            )}
          </CardBody>
        </Card>
      </PageSection>
    </>
  );
}
