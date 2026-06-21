// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Modal,
  ModalVariant,
  Button,
  Text,
  TextList,
  TextListItem,
} from '@patternfly/react-core';
import { pluginsApi } from '@/services/api';
import type { Plugin, PluginNotificationsConfig, PluginNotificationAction } from '@/types';

export function PluginNotifications() {
  const { data: plugins = [] } = useQuery({
    queryKey: ['plugins'],
    queryFn: pluginsApi.list,
    staleTime: 30_000,
  });

  const pluginsWithNotifications = plugins.filter(
    (p): p is Plugin & { ui_config: { notifications: PluginNotificationsConfig } } =>
      p.enabled && !!p.ui_config?.notifications
  );

  return (
    <>
      {pluginsWithNotifications.map((plugin) => (
        <PluginNotificationPoller
          key={plugin.slug}
          plugin={plugin}
          notificationsConfig={plugin.ui_config.notifications}
        />
      ))}
    </>
  );
}

interface PluginNotificationPollerProps {
  plugin: Plugin;
  notificationsConfig: PluginNotificationsConfig;
}

function PluginNotificationPoller({
  plugin,
  notificationsConfig,
}: PluginNotificationPollerProps) {
  const queryClient = useQueryClient();
  const queryKey = ['plugin-notifications', plugin.slug];

  const { data: items = [] } = useQuery<Record<string, unknown>[]>({
    queryKey,
    queryFn: async () => {
      const response = await fetch(notificationsConfig.poll_endpoint);
      if (!response.ok) return [];
      return response.json();
    },
    refetchInterval: 5_000,
  });

  const currentItem = items[0] as Record<string, unknown> | undefined;

  const handleAction = async (action: PluginNotificationAction, itemUuid: string) => {
    const endpoint = action.endpoint.replace('{uuid}', itemUuid);
    await fetch(endpoint, { method: action.method });
    queryClient.invalidateQueries({ queryKey });
  };

  if (!currentItem) return null;

  const { title_field, body_fields, actions } = notificationsConfig.item_schema;
  const title = String(currentItem[title_field] ?? '');
  const uuid = String(currentItem['uuid'] ?? '');

  return (
    <Modal
      variant={ModalVariant.small}
      title={`${plugin.name}: ${title}`}
      isOpen={true}
      onClose={() => queryClient.invalidateQueries({ queryKey })}
      actions={actions.map((action) => (
        <Button
          key={action.label}
          variant={action.variant as 'primary' | 'secondary' | 'danger'}
          onClick={() => handleAction(action, uuid)}
        >
          {action.label}
        </Button>
      ))}
    >
      {body_fields.map((field) => (
        <div key={field}>{renderFieldValue(currentItem[field])}</div>
      ))}
    </Modal>
  );
}

function renderFieldValue(value: unknown): React.ReactNode {
  if (Array.isArray(value)) {
    return (
      <TextList>
        {value.map((item, i) => (
          <TextListItem key={i}>
            {typeof item === 'object' && item !== null
              ? Object.values(item as Record<string, unknown>).join(' — ')
              : String(item)}
          </TextListItem>
        ))}
      </TextList>
    );
  }
  return <Text>{String(value ?? '')}</Text>;
}
