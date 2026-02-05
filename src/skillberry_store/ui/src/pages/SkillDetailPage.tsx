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
import { skillsApi } from '@/services/api';

export function SkillDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();

  const { data: skill, isLoading, error } = useQuery({
    queryKey: ['skills', name],
    queryFn: () => skillsApi.get(name!),
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

  if (error || !skill) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading skill">
          {(error as Error)?.message || 'Skill not found'}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Breadcrumb>
          <BreadcrumbItem to="/skills" onClick={(e) => { e.preventDefault(); navigate('/skills'); }}>
            Skills
          </BreadcrumbItem>
          <BreadcrumbItem isActive>{skill.name}</BreadcrumbItem>
        </Breadcrumb>
        <Title headingLevel="h1" size="2xl" style={{ marginTop: '1rem' }}>
          {skill.name}
        </Title>
      </PageSection>

      <PageSection>
        <Card>
          <CardBody>
            <DescriptionList>
              <DescriptionListGroup>
                <DescriptionListTerm>UUID</DescriptionListTerm>
                <DescriptionListDescription>{skill.uuid}</DescriptionListDescription>
              </DescriptionListGroup>
              <DescriptionListGroup>
                <DescriptionListTerm>Description</DescriptionListTerm>
                <DescriptionListDescription>
                  {skill.description || 'No description'}
                </DescriptionListDescription>
              </DescriptionListGroup>
              {skill.tags && skill.tags.length > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Tags</DescriptionListTerm>
                  <DescriptionListDescription>
                    {skill.tags.map((tag) => (
                      <Label key={tag} color="green" style={{ marginRight: '0.25rem' }}>
                        {tag}
                      </Label>
                    ))}
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