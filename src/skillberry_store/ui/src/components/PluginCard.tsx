// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import {
  Card,
  CardTitle,
  CardBody,
  CardFooter,
  Text,
  Label,
  Button,
  Flex,
  FlexItem,
  Tooltip,
} from '@patternfly/react-core';
import { CheckCircleIcon, ExclamationCircleIcon, InfoCircleIcon } from '@patternfly/react-icons';
import type { Plugin } from '@/types';

interface PluginCardProps {
  plugin: Plugin;
  onActionClick?: (action: any) => void;
}

export function PluginCard({ plugin, onActionClick }: PluginCardProps) {
  const getStatusIcon = () => {
    if (plugin.enabled) {
      return <CheckCircleIcon style={{ color: '#3E8635' }} />;
    }
    return <ExclamationCircleIcon style={{ color: '#C9190B' }} />;
  };

  const getStatusLabel = () => {
    return plugin.enabled ? 'Enabled' : 'Disabled';
  };

  return (
    <Card
      isCompact
      style={{
        borderLeft: `4px solid ${plugin.ui_config?.color || '#0066CC'}`,
      }}
    >
      <CardTitle>
        <Flex alignItems={{ default: 'alignItemsCenter' }}>
          <FlexItem>
            <Text component="h3">{plugin.name}</Text>
          </FlexItem>
          <FlexItem align={{ default: 'alignRight' }}>
            <Tooltip content={plugin.status}>
              <Label icon={getStatusIcon()}>{getStatusLabel()}</Label>
            </Tooltip>
          </FlexItem>
        </Flex>
      </CardTitle>
      <CardBody>
        <Text component="p" style={{ marginBottom: '0.5rem' }}>
          {plugin.description}
        </Text>
        {!plugin.enabled && plugin.status && (
          <Flex
            alignItems={{ default: 'alignItemsCenter' }}
            spaceItems={{ default: 'spaceItemsSm' }}
            style={{
              marginTop: '0.5rem',
              padding: '0.5rem',
              backgroundColor: '#FFF4E5',
              borderRadius: '4px',
              border: '1px solid #F0AB00',
            }}
          >
            <FlexItem>
              <InfoCircleIcon style={{ color: '#F0AB00' }} />
            </FlexItem>
            <FlexItem>
              <Text component="small" style={{ color: '#795600' }}>
                {plugin.status}
              </Text>
            </FlexItem>
          </Flex>
        )}
        <Flex spaceItems={{ default: 'spaceItemsSm' }}>
          <FlexItem>
            <Label color="blue">{plugin.plugin_type}</Label>
          </FlexItem>
          <FlexItem>
            <Label color="grey">v{plugin.version}</Label>
          </FlexItem>
          {plugin.author && (
            <FlexItem>
              <Label color="grey">{plugin.author}</Label>
            </FlexItem>
          )}
        </Flex>
      </CardBody>
      {plugin.enabled && plugin.has_ui && plugin.ui_config?.actions && (
        <CardFooter>
          <Flex spaceItems={{ default: 'spaceItemsSm' }}>
            {plugin.ui_config.actions.map((action, index) => (
              <FlexItem key={index}>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onActionClick?.(action)}
                  isDisabled={!plugin.enabled}
                >
                  {action.label}
                </Button>
              </FlexItem>
            ))}
          </Flex>
        </CardFooter>
      )}
    </Card>
  );
}

// Made with Bob
