// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PageSection,
  Title,
  Text,
  Spinner,
  EmptyState,
  EmptyStateIcon,
  EmptyStateBody,
  Gallery,
  Alert,
} from '@patternfly/react-core';
import { CubeIcon } from '@patternfly/react-icons';
import { pluginsApi } from '@/services/api';
import { PluginCard } from '@/components/PluginCard';
import { PluginActionForm } from '@/components/PluginActionForm';
import { SkillsShImporter } from '@/components/SkillsShImporter';
import type { Plugin, PluginAction } from '@/types';

export function PluginsPage() {
  const [selectedAction, setSelectedAction] = useState<{
    action: PluginAction;
    pluginName: string;
  } | null>(null);
  // Custom component modals — keyed by plugin slug
  const [customModal, setCustomModal] = useState<{ slug: string; component: string } | null>(null);

  // Fetch plugins
  const { data: plugins, isLoading, error } = useQuery({
    queryKey: ['plugins'],
    queryFn: pluginsApi.list,
  });

  const queryClient = useQueryClient();

  const toggleEnabledMutation = useMutation({
    mutationFn: ({ slug, enabled }: { slug: string; enabled: boolean }) =>
      pluginsApi.setEnabled(slug, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
    },
  });

  const handleToggleEnabled = (plugin: Plugin, enabled: boolean) => {
    toggleEnabledMutation.mutate({ slug: plugin.slug, enabled });
  };

  // Execute plugin action mutation
  const executeActionMutation = useMutation({
    mutationFn: async ({ pluginName, action, params }: {
      pluginName: string;
      action: string;
      params: Record<string, any>;
    }) => {
      // Extract the action name from the endpoint
      const actionName = action.split('/').pop() || action;
      return pluginsApi.executeAction(pluginName, actionName, params);
    },
  });

  const handleActionClick = (plugin: Plugin, action: PluginAction) => {
    // If the plugin declared a custom_component, open it instead of the generic form
    const custom = plugin.ui_config?.custom_component as string | undefined;
    if (custom) {
      setCustomModal({ slug: plugin.slug, component: custom });
      return;
    }
    setSelectedAction({
      action,
      pluginName: plugin.slug,
    });
  };

  const handleActionSubmit = async (params: Record<string, any>) => {
    if (!selectedAction) {
      throw new Error('No action selected');
    }

    const actionName = selectedAction.action.endpoint.split('/').pop() || '';
    return executeActionMutation.mutateAsync({
      pluginName: selectedAction.pluginName,
      action: actionName,
      params,
    });
  };

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

  if (!plugins || plugins.length === 0) {
    return (
      <PageSection>
        <EmptyState>
          <EmptyStateIcon icon={CubeIcon} />
          <Title headingLevel="h4" size="lg">
            No plugins found
          </Title>
          <EmptyStateBody>
            No plugins are currently installed. Install plugins to extend Skillberry Store functionality.
          </EmptyStateBody>
        </EmptyState>
      </PageSection>
    );
  }

  return (
    <PageSection>
      <Title headingLevel="h1" size="2xl" style={{ marginBottom: '1rem' }}>
        Plugins
      </Title>
      <Text component="p" style={{ marginBottom: '2rem' }}>
        Extend Skillberry Store with plugins that add new capabilities for creating, evaluating, and optimizing content.
      </Text>

      <Gallery hasGutter minWidths={{ default: '100%', md: '350px' }}>
        {plugins.map((plugin) => (
          <PluginCard
            key={plugin.name}
            plugin={plugin}
            onActionClick={(action) => handleActionClick(plugin, action)}
            onToggleEnabled={handleToggleEnabled}
          />
        ))}
      </Gallery>

      {selectedAction && (
        <PluginActionForm
          action={selectedAction.action}
          pluginName={selectedAction.pluginName}
          isOpen={true}
          onClose={() => setSelectedAction(null)}
          onSubmit={handleActionSubmit}
        />
      )}

      {customModal?.component === 'SkillsShImporter' && (() => {
        const plugin = plugins?.find((p) => p.slug === customModal.slug);
        return plugin ? (
          <SkillsShImporter
            plugin={plugin}
            isOpen={true}
            onClose={() => setCustomModal(null)}
          />
        ) : null;
      })()}
    </PageSection>
  );
}

// Made with Bob
