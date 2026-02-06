// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  PageSection,
  Title,
  Breadcrumb,
  BreadcrumbItem,
  Card,
  CardBody,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Spinner,
  Alert,
  Label,
} from '@patternfly/react-core';
import { vmcpApi } from '@/services/api';

export function VMCPServerDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();

  const { data: server, isLoading, error } = useQuery({
    queryKey: ['vmcp-servers', name],
    queryFn: () => vmcpApi.get(name!),
    enabled: !!name,
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

  if (error || !server) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading Virtual MCP server">
          {(error as Error)?.message || 'Server not found'}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Breadcrumb>
          <BreadcrumbItem to="/vmcp-servers" onClick={(e) => { e.preventDefault(); navigate('/vmcp-servers'); }}>
            Virtual MCP Servers
          </BreadcrumbItem>
          <BreadcrumbItem isActive>{server.name}</BreadcrumbItem>
        </Breadcrumb>
        <Title headingLevel="h1" size="2xl" style={{ marginTop: '1rem' }}>
          {server.name}
        </Title>
      </PageSection>

      <PageSection>
        <Card>
          <CardBody>
            <DescriptionList>
              <DescriptionListGroup>
                <DescriptionListTerm>Description</DescriptionListTerm>
                <DescriptionListDescription>
                  {server.description || 'No description'}
                </DescriptionListDescription>
              </DescriptionListGroup>
              <DescriptionListGroup>
                <DescriptionListTerm>Port</DescriptionListTerm>
                <DescriptionListDescription>{server.port}</DescriptionListDescription>
              </DescriptionListGroup>
              <DescriptionListGroup>
                <DescriptionListTerm>Tools</DescriptionListTerm>
                <DescriptionListDescription>
                  {server.tools.map((tool) => (
                    <Label key={tool} color="blue" style={{ marginRight: '0.25rem' }}>
                      {tool}
                    </Label>
                  ))}
                </DescriptionListDescription>
              </DescriptionListGroup>
              {server.status && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Status</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Label color={server.status === 'running' ? 'green' : 'red'}>
                      {server.status}
                    </Label>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
            </DescriptionList>
          </CardBody>
        </Card>
      </PageSection>
    </>
  );
}