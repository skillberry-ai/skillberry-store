// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  PageSection,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Button,
  Card,
  CardBody,
  Gallery,
  GalleryItem,
  Text,
  Label,
  Spinner,
  EmptyState,
  EmptyStateIcon,
  EmptyStateBody,
  Alert,
} from '@patternfly/react-core';
import { PlusIcon, ServerIcon } from '@patternfly/react-icons';
import { vmcpApi } from '@/services/api';

export function VMCPServersPage() {
  const navigate = useNavigate();

  const { data: servers, isLoading, error } = useQuery({
    queryKey: ['vmcp-servers'],
    queryFn: vmcpApi.list,
  });

  if (isLoading) {
    return (
      <PageSection>
        <div className="loading-container">
          <Spinner size="xl" />
        </div>
      </PageSection>
    );
  }

  if (error) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading VMCP servers">
          {(error as Error).message}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Title headingLevel="h1" size="2xl">
          VMCP Servers
        </Title>
        <Text>Create and manage virtual MCP servers for tool subsets</Text>
      </PageSection>

      <PageSection>
        <Toolbar>
          <ToolbarContent>
            <ToolbarItem>
              <Button variant="primary" icon={<PlusIcon />}>
                Create VMCP Server
              </Button>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>

        {!servers || servers.length === 0 ? (
          <EmptyState>
            <EmptyStateIcon icon={ServerIcon} />
            <Title headingLevel="h4" size="lg">
              No VMCP servers yet
            </Title>
            <EmptyStateBody>
              Create your first VMCP server to get started
            </EmptyStateBody>
            <Button variant="primary">
              Create VMCP Server
            </Button>
          </EmptyState>
        ) : (
          <Gallery hasGutter minWidths={{ default: '100%', md: '50%', xl: '33%' }}>
            {servers.map((server) => (
              <GalleryItem key={server.name}>
                <Card isClickable onClick={() => navigate(`/vmcp-servers/${server.name}`)}>
                  <CardBody>
                    <Title headingLevel="h3" size="lg">
                      {server.name}
                    </Title>
                    <Text className="text-muted text-small">
                      {server.description || 'No description'}
                    </Text>
                    <div style={{ marginTop: '0.5rem' }}>
                      <Label color="orange">Port: {server.port}</Label>
                      <Label color="blue" style={{ marginLeft: '0.25rem' }}>
                        {server.tools.length} tools
                      </Label>
                      {server.status && (
                        <Label
                          color={server.status === 'running' ? 'green' : 'red'}
                          style={{ marginLeft: '0.25rem' }}
                        >
                          {server.status}
                        </Label>
                      )}
                    </div>
                  </CardBody>
                </Card>
              </GalleryItem>
            ))}
          </Gallery>
        )}
      </PageSection>
    </>
  );
}