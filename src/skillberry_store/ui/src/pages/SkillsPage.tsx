// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PageSection,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Button,
  SearchInput,
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
  Modal,
  ModalVariant,
} from '@patternfly/react-core';
import { PlusIcon, CodeIcon, SearchIcon } from '@patternfly/react-icons';
import { skillsApi } from '@/services/api';

export function SkillsPage() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const { data: skills, isLoading, error } = useQuery({
    queryKey: ['skills'],
    queryFn: skillsApi.list,
  });

  const { data: searchResults } = useQuery({
    queryKey: ['skills', 'search', searchTerm],
    queryFn: () => skillsApi.search(searchTerm, 10, 1),
    enabled: searchTerm.length > 0,
  });

  const filteredSkills = searchTerm && searchResults
    ? skills?.filter((skill) =>
        searchResults.some((result) => result.name === skill.name)
      )
    : skills;

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
        <Alert variant="danger" title="Error loading skills">
          {(error as Error).message}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Title headingLevel="h1" size="2xl">
          Skills
        </Title>
        <Text>Organize collections of tools and snippets into reusable skills</Text>
      </PageSection>

      <PageSection>
        <Toolbar>
          <ToolbarContent>
            <ToolbarItem variant="search-filter">
              <SearchInput
                placeholder="Search skills..."
                value={searchTerm}
                onChange={(_, value) => setSearchTerm(value)}
                onClear={() => setSearchTerm('')}
              />
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="primary"
                icon={<PlusIcon />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                Create Skill
              </Button>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>

        {!filteredSkills || filteredSkills.length === 0 ? (
          <EmptyState>
            <EmptyStateIcon icon={searchTerm ? SearchIcon : CodeIcon} />
            <Title headingLevel="h4" size="lg">
              {searchTerm ? 'No skills found' : 'No skills yet'}
            </Title>
            <EmptyStateBody>
              {searchTerm
                ? 'Try adjusting your search criteria'
                : 'Create your first skill to get started'}
            </EmptyStateBody>
          </EmptyState>
        ) : (
          <Gallery hasGutter minWidths={{ default: '100%', md: '50%', xl: '33%' }}>
            {filteredSkills.map((skill) => (
              <GalleryItem key={skill.uuid}>
                <Card isClickable onClick={() => navigate(`/skills/${skill.name}`)}>
                  <CardBody>
                    <Title headingLevel="h3" size="lg">
                      {skill.name}
                    </Title>
                    <Text className="text-muted text-small">
                      {skill.description || 'No description'}
                    </Text>
                    {skill.tags && skill.tags.length > 0 && (
                      <div style={{ marginTop: '0.5rem' }}>
                        {skill.tags.map((tag) => (
                          <Label key={tag} color="green" style={{ marginRight: '0.25rem' }}>
                            {tag}
                          </Label>
                        ))}
                      </div>
                    )}
                  </CardBody>
                </Card>
              </GalleryItem>
            ))}
          </Gallery>
        )}
      </PageSection>

      <Modal
        variant={ModalVariant.small}
        title="Create Skill"
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      >
        <Alert variant="info" isInline title="Feature Coming Soon">
          The skill creation interface is under development. Please use the API to create skills for now.
        </Alert>
      </Modal>
    </>
  );
}