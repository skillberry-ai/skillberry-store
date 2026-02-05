// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useMemo } from 'react';
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
  Text,
  Spinner,
  EmptyState,
  EmptyStateIcon,
  EmptyStateBody,
  Alert,
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  FormSelect,
  FormSelectOption,
  Label,
} from '@patternfly/react-core';
import { Table, Thead, Tr, Th, Tbody, Td, ThProps } from '@patternfly/react-table';
import { PlusIcon, FileCodeIcon, SearchIcon, TrashIcon } from '@patternfly/react-icons';
import { snippetsApi } from '@/services/api';
import type { Snippet } from '@/types';

type SortableColumn = 'name' | 'description' | 'state' | 'content_type' | 'version';

export function SnippetsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newSnippet, setNewSnippet] = useState({
    name: '',
    version: '',
    description: '',
    state: 'approved' as 'unknown' | 'any' | 'new' | 'checked' | 'approved',
    tags: [] as string[],
    content: '',
    content_type: 'text/plain',
  });
  const [tagInput, setTagInput] = useState('');
  const [createError, setCreateError] = useState('');
  const [selectedSnippets, setSelectedSnippets] = useState<string[]>([]);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [activeSortIndex, setActiveSortIndex] = useState<number | null>(null);
  const [activeSortDirection, setActiveSortDirection] = useState<'asc' | 'desc'>('asc');

  const { data: snippets, isLoading, error } = useQuery({
    queryKey: ['snippets'],
    queryFn: snippetsApi.list,
  });

  const { data: searchResults } = useQuery({
    queryKey: ['snippets', 'search', searchTerm],
    queryFn: () => snippetsApi.search(searchTerm, 10, 1),
    enabled: searchTerm.length > 0,
  });

  // Create snippet mutation
  const createMutation = useMutation({
    mutationFn: (snippet: Omit<Snippet, 'uuid'>) =>
      snippetsApi.create(snippet),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snippets'] });
      setIsCreateModalOpen(false);
      setNewSnippet({
        name: '',
        version: '',
        description: '',
        state: 'approved',
        tags: [],
        content: '',
        content_type: 'text/plain',
      });
      setTagInput('');
      setCreateError('');
    },
    onError: (error: any) => {
      setCreateError(error.message || 'Failed to create snippet');
    },
  });

  // Delete snippets mutation
  const deleteMutation = useMutation({
    mutationFn: async (names: string[]) => {
      await Promise.all(names.map(name => snippetsApi.delete(name)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snippets'] });
      setSelectedSnippets([]);
      setIsDeleteModalOpen(false);
    },
  });

  const handleCreateSnippet = () => {
    if (!newSnippet.name || !newSnippet.description || !newSnippet.content) {
      setCreateError('Please fill in all required fields');
      return;
    }
    console.log('Creating snippet with data:', newSnippet);
    createMutation.mutate(newSnippet);
  };

  const handleAddTag = () => {
    console.log('handleAddTag called, tagInput:', tagInput);
    console.log('Current tags:', newSnippet.tags);
    if (tagInput.trim() && !newSnippet.tags.includes(tagInput.trim())) {
      const updatedTags = [...newSnippet.tags, tagInput.trim()];
      console.log('Adding tag, new tags array:', updatedTags);
      setNewSnippet({
        ...newSnippet,
        tags: updatedTags,
      });
      setTagInput('');
    } else {
      console.log('Tag not added - either empty or duplicate');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setNewSnippet({
      ...newSnippet,
      tags: newSnippet.tags.filter(tag => tag !== tagToRemove),
    });
  };

  const handleSelectSnippet = (snippetName: string, isSelected: boolean) => {
    setSelectedSnippets(prev =>
      isSelected
        ? [...prev, snippetName]
        : prev.filter(name => name !== snippetName)
    );
  };

  const handleSelectAll = (isSelected: boolean) => {
    setSelectedSnippets(
      isSelected ? (filteredSnippets?.map(s => s.name) || []) : []
    );
  };

  const handleDeleteSelected = () => {
    deleteMutation.mutate(selectedSnippets);
  };

  const getSortableRowValues = (snippet: Snippet): (string | number)[] => {
    return [
      snippet.name,
      snippet.description || '',
      snippet.state || '',
      snippet.content_type || '',
      snippet.version || '',
    ];
  };

  const filteredSnippets = useMemo(() => {
    let filtered = searchTerm && searchResults
      ? snippets?.filter((snippet) =>
          searchResults.some((result) => result.name === snippet.name)
        )
      : snippets;

    if (filtered && activeSortIndex !== null) {
      filtered = [...filtered].sort((a, b) => {
        const aValue = getSortableRowValues(a)[activeSortIndex];
        const bValue = getSortableRowValues(b)[activeSortIndex];
        
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          const comparison = aValue.localeCompare(bValue);
          return activeSortDirection === 'asc' ? comparison : -comparison;
        }
        
        return 0;
      });
    }

    return filtered;
  }, [snippets, searchResults, searchTerm, activeSortIndex, activeSortDirection]);

  const getSortParams = (columnIndex: number): ThProps['sort'] => ({
    sortBy: {
      index: activeSortIndex ?? 0,
      direction: activeSortDirection,
    },
    onSort: (_event, index, direction) => {
      setActiveSortIndex(index);
      setActiveSortDirection(direction);
    },
    columnIndex,
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
        <Alert variant="danger" title="Error loading snippets">
          {(error as Error).message}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Title headingLevel="h1" size="2xl">
          Snippets
        </Title>
        <Text>Store and manage code snippets for quick reference and reuse</Text>
      </PageSection>

      <PageSection>
        <Toolbar>
          <ToolbarContent>
            <ToolbarItem variant="search-filter">
              <SearchInput
                placeholder="Search snippets..."
                value={searchTerm}
                onChange={(_, value) => setSearchTerm(value)}
                onClear={() => setSearchTerm('')}
              />
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="danger"
                icon={<TrashIcon />}
                onClick={() => setIsDeleteModalOpen(true)}
                isDisabled={selectedSnippets.length === 0}
              >
                Delete ({selectedSnippets.length})
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="primary"
                icon={<PlusIcon />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                Create Snippet
              </Button>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>

        {!filteredSnippets || filteredSnippets.length === 0 ? (
          <EmptyState>
            <EmptyStateIcon icon={searchTerm ? SearchIcon : FileCodeIcon} />
            <Title headingLevel="h4" size="lg">
              {searchTerm ? 'No snippets found' : 'No snippets yet'}
            </Title>
            <EmptyStateBody>
              {searchTerm
                ? 'Try adjusting your search criteria'
                : 'Create your first snippet to get started'}
            </EmptyStateBody>
            {!searchTerm && (
              <Button
                variant="primary"
                icon={<PlusIcon />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                Create Snippet
              </Button>
            )}
          </EmptyState>
        ) : (
          <Table aria-label="Snippets table" variant="compact">
            <Thead>
              <Tr>
                <Th
                  select={{
                    onSelect: (_event, isSelected) => handleSelectAll(isSelected),
                    isSelected: selectedSnippets.length === filteredSnippets.length && filteredSnippets.length > 0,
                  }}
                />
                <Th sort={getSortParams(0)}>Name</Th>
                <Th sort={getSortParams(1)}>Description</Th>
                <Th sort={getSortParams(2)}>State</Th>
                <Th>Tags</Th>
                <Th sort={getSortParams(3)}>Content Type</Th>
                <Th sort={getSortParams(4)}>Version</Th>
              </Tr>
            </Thead>
            <Tbody>
              {filteredSnippets.map((snippet, index) => (
                <Tr key={snippet.uuid}>
                  <Td
                    select={{
                      rowIndex: index,
                      onSelect: (_event, isSelected) => handleSelectSnippet(snippet.name, isSelected),
                      isSelected: selectedSnippets.includes(snippet.name),
                    }}
                  />
                  <Td
                    dataLabel="Name"
                    onClick={() => navigate(`/snippets/${snippet.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.name}
                  </Td>
                  <Td
                    dataLabel="Description"
                    onClick={() => navigate(`/snippets/${snippet.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.description || 'No description'}
                  </Td>
                  <Td
                    dataLabel="State"
                    onClick={() => navigate(`/snippets/${snippet.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.state || '-'}
                  </Td>
                  <Td
                    dataLabel="Tags"
                    onClick={() => navigate(`/snippets/${snippet.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.tags && snippet.tags.length > 0 ? (
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        {snippet.tags.map((tag) => (
                          <Label key={tag} color="purple" isCompact>
                            {tag}
                          </Label>
                        ))}
                      </div>
                    ) : (
                      '-'
                    )}
                  </Td>
                  <Td
                    dataLabel="Content Type"
                    onClick={() => navigate(`/snippets/${snippet.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.content_type || '-'}
                  </Td>
                  <Td
                    dataLabel="Version"
                    onClick={() => navigate(`/snippets/${snippet.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.version || '-'}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </PageSection>

      {/* Create Snippet Modal */}
      <Modal
        variant={ModalVariant.medium}
        title="Create New Snippet"
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setNewSnippet({
            name: '',
            version: '',
            description: '',
            state: 'approved',
            tags: [],
            content: '',
            content_type: 'text/plain',
          });
          setTagInput('');
          setCreateError('');
        }}
        actions={[
          <Button
            key="create"
            variant="primary"
            onClick={handleCreateSnippet}
            isLoading={createMutation.isPending}
          >
            Create
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsCreateModalOpen(false);
              setNewSnippet({
                name: '',
                version: '',
                description: '',
                state: 'approved',
                tags: [],
                content: '',
                content_type: 'text/plain',
              });
              setTagInput('');
              setCreateError('');
            }}
          >
            Cancel
          </Button>,
        ]}
      >
        {createError && (
          <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>
            {createError}
          </Alert>
        )}
        <Form>
          <FormGroup label="Name" isRequired fieldId="snippet-name">
            <TextInput
              isRequired
              type="text"
              id="snippet-name"
              value={newSnippet.name}
              onChange={(_, value) => setNewSnippet({ ...newSnippet, name: value })}
            />
          </FormGroup>
          <FormGroup label="Version" fieldId="snippet-version">
            <TextInput
              type="text"
              id="snippet-version"
              value={newSnippet.version}
              onChange={(_, value) => setNewSnippet({ ...newSnippet, version: value })}
              placeholder="e.g., 1.0.0"
            />
          </FormGroup>
          <FormGroup label="Description" isRequired fieldId="snippet-description">
            <TextArea
              isRequired
              id="snippet-description"
              value={newSnippet.description}
              onChange={(_, value) => setNewSnippet({ ...newSnippet, description: value })}
              rows={2}
            />
          </FormGroup>
          <FormGroup label="State" isRequired fieldId="snippet-state">
            <FormSelect
              value={newSnippet.state}
              onChange={(_, value) => setNewSnippet({ ...newSnippet, state: value as 'unknown' | 'any' | 'new' | 'checked' | 'approved' })}
              id="snippet-state"
            >
              <FormSelectOption value="unknown" label="Unknown" />
              <FormSelectOption value="any" label="Any" />
              <FormSelectOption value="new" label="New" />
              <FormSelectOption value="checked" label="Checked" />
              <FormSelectOption value="approved" label="Approved" />
            </FormSelect>
          </FormGroup>
          <FormGroup label="Tags" fieldId="snippet-tags">
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <TextInput
                type="text"
                id="snippet-tags"
                value={tagInput}
                onChange={(_, value) => setTagInput(value)}
                placeholder="Add a tag"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
              />
              <Button variant="secondary" onClick={handleAddTag}>
                Add
              </Button>
            </div>
            {newSnippet.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {newSnippet.tags.map((tag) => (
                  <Button
                    key={tag}
                    variant="plain"
                    onClick={() => handleRemoveTag(tag)}
                    style={{
                      padding: '0.25rem 0.5rem',
                      backgroundColor: '#f0f0f0',
                      border: '1px solid #d2d2d2',
                      borderRadius: '3px',
                    }}
                  >
                    {tag} ✕
                  </Button>
                ))}
              </div>
            )}
          </FormGroup>
          <FormGroup label="Content" isRequired fieldId="snippet-content">
            <TextArea
              isRequired
              id="snippet-content"
              value={newSnippet.content}
              onChange={(_, value) => setNewSnippet({ ...newSnippet, content: value })}
              rows={10}
              placeholder="Enter your code snippet here..."
            />
          </FormGroup>
          <FormGroup label="Content Type" isRequired fieldId="snippet-content-type">
            <FormSelect
              value={newSnippet.content_type}
              onChange={(_, value) => setNewSnippet({ ...newSnippet, content_type: value })}
              id="snippet-content-type"
            >
              <FormSelectOption value="text/plain" label="Plain Text" />
              <FormSelectOption value="text/x-python" label="Python" />
              <FormSelectOption value="text/javascript" label="JavaScript" />
              <FormSelectOption value="text/x-java" label="Java" />
              <FormSelectOption value="text/x-go" label="Go" />
              <FormSelectOption value="text/x-sh" label="Shell Script" />
              <FormSelectOption value="text/x-yaml" label="YAML" />
              <FormSelectOption value="application/json" label="JSON" />
              <FormSelectOption value="text/html" label="HTML" />
              <FormSelectOption value="text/css" label="CSS" />
            </FormSelect>
          </FormGroup>
        </Form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete Snippets"
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        actions={[
          <Button
            key="delete"
            variant="danger"
            onClick={handleDeleteSelected}
            isLoading={deleteMutation.isPending}
          >
            Delete
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsDeleteModalOpen(false)}
          >
            Cancel
          </Button>,
        ]}
      >
        <Text>
          Are you sure you want to delete {selectedSnippets.length} snippet{selectedSnippets.length > 1 ? 's' : ''}?
          This action cannot be undone.
        </Text>
        <ul style={{ marginTop: '1rem' }}>
          {selectedSnippets.map(name => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      </Modal>
    </>
  );
}