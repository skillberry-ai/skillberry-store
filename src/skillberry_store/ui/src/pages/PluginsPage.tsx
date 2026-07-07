// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Badge,
  Button,
  ButtonVariant,
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  Gallery,
  Label,
  PageSection,
  SearchInput,
  Spinner,
  Split,
  SplitItem,
  Stack,
  StackItem,
  Text,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  ToggleGroup,
  ToggleGroupItem,
} from '@patternfly/react-core';
import { CubeIcon, PlusIcon, ThIcon, ListIcon } from '@patternfly/react-icons';
import { pluginsApi } from '@/services/api';
import { PluginInstallDialog } from '@/components/PluginInstallDialog';
import type { Plugin, PluginState } from '@/types';

type ViewMode = 'cards' | 'list';

const STATE_BADGE_VARIANT: Record<PluginState, 'green' | 'blue' | 'orange' | 'grey' | 'red'> = {
  running: 'green',
  installed: 'blue',
  starting: 'orange',
  stopping: 'orange',
  error: 'red',
  not_installed: 'grey',
};

function PluginRow({
  plugin,
  onStart,
  onStop,
  onRestart,
  onUninstall,
}: {
  plugin: Plugin;
  onStart: (slug: string) => void;
  onStop: (slug: string) => void;
  onRestart: (slug: string) => void;
  onUninstall: (slug: string) => void;
}) {
  const state = (plugin.state ?? 'installed') as PluginState;
  const isRunning = state === 'running';
  const isInstalled = state === 'installed' || state === 'error';
  const busy = state === 'starting' || state === 'stopping';
  const manifest = plugin.manifest ?? {};
  const name = manifest.name || plugin.name || plugin.slug;

  return (
    <Stack hasGutter style={{ padding: '1rem', border: '1px solid #d2d2d2', borderRadius: 4 }}>
      <StackItem>
        <Split hasGutter>
          <SplitItem isFilled>
            <Title headingLevel="h3" size="lg">
              {name} <Label color={STATE_BADGE_VARIANT[state]}>{state}</Label>
            </Title>
            <Text component="small">{plugin.slug} · v{manifest.version || plugin.version || '?'}</Text>
          </SplitItem>
          <SplitItem>
            <Button
              variant={ButtonVariant.secondary}
              isDisabled={isRunning || busy}
              onClick={() => onStart(plugin.slug)}
            >
              Start
            </Button>{' '}
            <Button
              variant={ButtonVariant.secondary}
              isDisabled={!isRunning || busy}
              onClick={() => onStop(plugin.slug)}
            >
              Stop
            </Button>{' '}
            <Button
              variant={ButtonVariant.secondary}
              isDisabled={busy}
              onClick={() => onRestart(plugin.slug)}
            >
              Restart
            </Button>{' '}
            <Button
              variant={ButtonVariant.danger}
              isDisabled={busy}
              onClick={() => onUninstall(plugin.slug)}
            >
              Uninstall
            </Button>
          </SplitItem>
        </Split>
      </StackItem>
      {manifest.description && (
        <StackItem>
          <Text>{manifest.description}</Text>
        </StackItem>
      )}
      {plugin.missing_env && plugin.missing_env.length > 0 && (
        <StackItem>
          <Alert variant="warning" title="Missing required environment variables" isInline>
            <p>The following env vars must be set before this plugin can start:</p>
            <ul>
              {plugin.missing_env.map((n) => (
                <li key={n}><code>{n}</code></li>
              ))}
            </ul>
          </Alert>
        </StackItem>
      )}
      {state === 'error' && plugin.error && (
        <StackItem>
          <Alert variant="danger" title="Plugin error" isInline>
            {plugin.error}
          </Alert>
        </StackItem>
      )}
    </Stack>
  );
}

export function PluginsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [view, setView] = useState<ViewMode>('cards');
  const [installOpen, setInstallOpen] = useState(false);

  const { data: plugins, isLoading, error } = useQuery({
    queryKey: ['plugins'],
    queryFn: pluginsApi.list,
    refetchInterval: 4000,
  });

  const startMutation = useMutation({
    mutationFn: (slug: string) => pluginsApi.start(slug),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['plugins'] }),
  });
  const stopMutation = useMutation({
    mutationFn: (slug: string) => pluginsApi.stop(slug),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['plugins'] }),
  });
  const restartMutation = useMutation({
    mutationFn: (slug: string) => pluginsApi.restart(slug),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['plugins'] }),
  });
  const uninstallMutation = useMutation({
    mutationFn: (slug: string) => pluginsApi.uninstall(slug),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['plugins'] }),
  });

  const filtered = useMemo(() => {
    const list = plugins ?? [];
    if (!search) return list;
    const q = search.toLowerCase();
    return list.filter((p) => {
      const name = p.manifest?.name || p.name || '';
      return (
        (p.slug || '').toLowerCase().includes(q) ||
        name.toLowerCase().includes(q) ||
        (p.manifest?.description || p.description || '').toLowerCase().includes(q)
      );
    });
  }, [plugins, search]);

  if (isLoading) {
    return (
      <PageSection>
        <Spinner size="lg" />
      </PageSection>
    );
  }

  if (error) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading plugins">
          {(error as Error).message}
        </Alert>
      </PageSection>
    );
  }

  return (
    <PageSection>
      <Title headingLevel="h1" size="2xl" style={{ marginBottom: '1rem' }}>
        Plugins
      </Title>
      <Text component="p" style={{ marginBottom: '1rem' }}>
        Extend Skillberry Store with plugins that add new capabilities for creating, evaluating, and optimizing content.
      </Text>

      <Toolbar>
        <ToolbarContent>
          <ToolbarItem>
            <SearchInput
              placeholder="Search plugins…"
              value={search}
              onChange={(_e, v) => setSearch(v)}
              onClear={() => setSearch('')}
            />
          </ToolbarItem>
          <ToolbarItem>
            <ToggleGroup>
              <ToggleGroupItem
                icon={<ThIcon />}
                aria-label="Cards"
                isSelected={view === 'cards'}
                onChange={() => setView('cards')}
              />
              <ToggleGroupItem
                icon={<ListIcon />}
                aria-label="List"
                isSelected={view === 'list'}
                onChange={() => setView('list')}
              />
            </ToggleGroup>
          </ToolbarItem>
          <ToolbarItem alignment={{ default: 'alignRight' }}>
            <Button variant={ButtonVariant.primary} icon={<PlusIcon />} onClick={() => setInstallOpen(true)}>
              Install plugin…
            </Button>
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>

      {(!filtered || filtered.length === 0) && (
        <EmptyState>
          <EmptyStateIcon icon={CubeIcon} />
          <Title headingLevel="h4" size="lg">No plugins installed</Title>
          <EmptyStateBody>Click “Install plugin…” to get started.</EmptyStateBody>
        </EmptyState>
      )}

      {filtered.length > 0 && view === 'cards' && (
        <Gallery hasGutter minWidths={{ default: '100%', md: '450px' }}>
          {filtered.map((p) => (
            <PluginRow
              key={p.slug}
              plugin={p}
              onStart={(s) => startMutation.mutate(s)}
              onStop={(s) => stopMutation.mutate(s)}
              onRestart={(s) => restartMutation.mutate(s)}
              onUninstall={(s) => uninstallMutation.mutate(s)}
            />
          ))}
        </Gallery>
      )}

      {filtered.length > 0 && view === 'list' && (
        <Stack hasGutter>
          {filtered.map((p) => (
            <StackItem key={p.slug}>
              <PluginRow
                plugin={p}
                onStart={(s) => startMutation.mutate(s)}
                onStop={(s) => stopMutation.mutate(s)}
                onRestart={(s) => restartMutation.mutate(s)}
                onUninstall={(s) => uninstallMutation.mutate(s)}
              />
            </StackItem>
          ))}
        </Stack>
      )}

      <PluginInstallDialog isOpen={installOpen} onClose={() => setInstallOpen(false)} />
    </PageSection>
  );
}
