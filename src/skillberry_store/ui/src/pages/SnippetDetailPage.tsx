// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTagColor } from '../utils/tagColors';
import {
  PageSection,
  Title,
  Breadcrumb,
  BreadcrumbItem,
  Card,
  CardBody,
  CardTitle,
  CodeBlock,
  CodeBlockCode,
  Spinner,
  Alert,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Label,
  Text,
  Button,
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  FormSelect,
  FormSelectOption,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import { EditIcon, TrashIcon } from '@patternfly/react-icons';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { snippetsApi } from '@/services/api';
import type { Snippet } from '@/types';

export function SnippetDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [editedSnippet, setEditedSnippet] = useState({
    name: '',
    version: '',
    description: '',
    state: 'approved' as 'unknown' | 'any' | 'new' | 'checked' | 'approved',
    tags: [] as string[],
    content: '',
    content_type: 'text/plain',
    extra: {} as Record<string, any>,
  });
  const [tagInput, setTagInput] = useState('');
  const [extraInput, setExtraInput] = useState('{}');
  const [editError, setEditError] = useState('');

  const { data: snippet, isLoading, error } = useQuery({
    queryKey: ['snippets', name],
    queryFn: () => snippetsApi.get(name!),
    enabled: !!name,
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (updatedSnippet: Snippet) =>
      snippetsApi.update(name!, updatedSnippet),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snippets', name] });
      queryClient.invalidateQueries({ queryKey: ['snippets'] });
      setIsEditModalOpen(false);
      setEditError('');
    },
    onError: (error: any) => {
      setEditError(error.message || 'Failed to update snippet');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => snippetsApi.delete(name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snippets'] });
      navigate('/snippets');
    },
  });

  const handleEditClick = () => {
    if (snippet) {
      setEditedSnippet({
        name: snippet.name,
        version: snippet.version || '',
        description: snippet.description,
        state: snippet.state || 'approved',
        tags: snippet.tags || [],
        content: snippet.content,
        content_type: snippet.content_type || 'text/plain',
        extra: snippet.extra || {},
      });
      setExtraInput(JSON.stringify(snippet.extra || {}, null, 2));
      setIsEditModalOpen(true);
    }
  };

  const handleUpdateSnippet = () => {
    if (!editedSnippet.name || !editedSnippet.description || !editedSnippet.content) {
      setEditError('Please fill in all required fields');
      return;
    }
    
    // Parse extra field
    let parsedExtra = {};
    try {
      parsedExtra = JSON.parse(extraInput);
      if (typeof parsedExtra !== 'object' || Array.isArray(parsedExtra)) {
        setEditError('Additional Information must be a valid JSON object');
        return;
      }
    } catch (e) {
      setEditError('Additional Information must be valid JSON');
      return;
    }
    
    updateMutation.mutate({ ...snippet!, ...editedSnippet, extra: Object.keys(parsedExtra).length > 0 ? parsedExtra : undefined });
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !editedSnippet.tags.includes(tagInput.trim())) {
      setEditedSnippet({
        ...editedSnippet,
        tags: [...editedSnippet.tags, tagInput.trim()],
      });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedSnippet({
      ...editedSnippet,
      tags: editedSnippet.tags.filter(tag => tag !== tagToRemove),
    });
  };

  if (isLoading) {
    return (
      <PageSection>
        <div className="loading-container">
          <Spinner size="xl" />
        </div>
      </PageSection>
    );
  }

  if (error || !snippet) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading snippet">
          {(error as Error)?.message || 'Snippet not found'}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Breadcrumb>
          <BreadcrumbItem to="/snippets" onClick={(e) => { e.preventDefault(); navigate('/snippets'); }}>
            Snippets
          </BreadcrumbItem>
          <BreadcrumbItem isActive>{snippet.name}</BreadcrumbItem>
        </Breadcrumb>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
          <Title headingLevel="h1" size="2xl">
            {snippet.name}
          </Title>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button variant="secondary" icon={<EditIcon />} onClick={handleEditClick}>
              Edit
            </Button>
            <Button variant="danger" icon={<TrashIcon />} onClick={() => setIsDeleteModalOpen(true)}>
              Delete
            </Button>
          </div>
        </div>
      </PageSection>

      <PageSection>
        <Card>
          <CardTitle>Snippet Information</CardTitle>
          <CardBody>
            <DescriptionList isHorizontal>
              <DescriptionListGroup>
                <DescriptionListTerm>Name</DescriptionListTerm>
                <DescriptionListDescription>{snippet.name}</DescriptionListDescription>
              </DescriptionListGroup>
              
              <DescriptionListGroup>
                <DescriptionListTerm>Description</DescriptionListTerm>
                <DescriptionListDescription>
                  {snippet.description || 'No description'}
                </DescriptionListDescription>
              </DescriptionListGroup>

              {snippet.version && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Version</DescriptionListTerm>
                  <DescriptionListDescription>{snippet.version}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {snippet.state && (
                <DescriptionListGroup>
                  <DescriptionListTerm>State</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Label color={
                      snippet.state === 'approved' ? 'green' :
                      snippet.state === 'checked' ? 'blue' :
                      snippet.state === 'new' ? 'cyan' : 'orange'
                    }>
                      {snippet.state}
                    </Label>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {snippet.content_type && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Content Type</DescriptionListTerm>
                  <DescriptionListDescription>{snippet.content_type}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {snippet.tags && snippet.tags.length > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Tags</DescriptionListTerm>
                  <DescriptionListDescription>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {snippet.tags.map((tag) => (
                        <Label key={tag} color={getTagColor(tag)}>{tag}</Label>
                      ))}
                    </div>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {snippet.author && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Author</DescriptionListTerm>
                  <DescriptionListDescription>{snippet.author}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {snippet.created_at && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Created</DescriptionListTerm>
                  <DescriptionListDescription>
                    {new Date(snippet.created_at).toLocaleString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {snippet.modified_at && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Last Modified</DescriptionListTerm>
                  <DescriptionListDescription>
                    {new Date(snippet.modified_at).toLocaleString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              <DescriptionListGroup>
                <DescriptionListTerm>UUID</DescriptionListTerm>
                <DescriptionListDescription>
                  <Text component="small" style={{ fontFamily: 'monospace' }}>
                    {snippet.uuid}
                  </Text>
                </DescriptionListDescription>
              </DescriptionListGroup>

              {snippet.extra && Object.keys(snippet.extra).length > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Additional Information</DescriptionListTerm>
                  <DescriptionListDescription>
                    <CodeBlock>
                      <CodeBlockCode style={{
                        fontSize: '14px',
                        lineHeight: '1.6',
                        padding: '1rem',
                        backgroundColor: '#f5f5f5',
                        borderRadius: '4px',
                        display: 'block',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {JSON.stringify(snippet.extra, null, 2)}
                      </CodeBlockCode>
                    </CodeBlock>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
            </DescriptionList>
          </CardBody>
        </Card>

        <Card style={{ marginTop: '1rem' }}>
          <CardTitle>Content</CardTitle>
          <CardBody>
            <div style={{
              maxHeight: '70vh',
              overflow: 'auto',
              border: '1px solid #3d3d3d',
              borderRadius: '6px'
            }}>
              <SyntaxHighlighter
                language={
                  snippet.content_type === 'text/x-python' ? 'python' :
                  snippet.content_type === 'text/javascript' ? 'javascript' :
                  snippet.content_type === 'text/x-java' ? 'java' :
                  snippet.content_type === 'text/x-go' ? 'go' :
                  snippet.content_type === 'text/x-sh' ? 'bash' :
                  snippet.content_type === 'text/x-yaml' ? 'yaml' :
                  snippet.content_type === 'application/json' ? 'json' :
                  snippet.content_type === 'text/html' ? 'html' :
                  snippet.content_type === 'text/css' ? 'css' :
                  'text'
                }
                style={vscDarkPlus}
                showLineNumbers={true}
                wrapLines={false}
                customStyle={{
                  margin: 0,
                  fontSize: '15px',
                  lineHeight: '1.6',
                  minHeight: '100%',
                }}
              >
                {snippet.content}
              </SyntaxHighlighter>
            </div>
          </CardBody>
        </Card>
      </PageSection>

      {/* Edit Modal */}
      <Modal
        variant={ModalVariant.large}
        title="Edit Snippet"
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditError('');
          setTagInput('');
        }}
        actions={[
          <Button
            key="save"
            variant="primary"
            onClick={handleUpdateSnippet}
            isLoading={updateMutation.isPending}
          >
            Save Changes
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsEditModalOpen(false);
              setEditError('');
              setTagInput('');
            }}
          >
            Cancel
          </Button>,
        ]}
      >
        {editError && (
          <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>
            {editError}
          </Alert>
        )}
        <Form>
          <FormGroup label="Name" isRequired fieldId="snippet-name">
            <TextInput
              isRequired
              type="text"
              id="snippet-name"
              value={editedSnippet.name}
              onChange={(_, value) => setEditedSnippet({ ...editedSnippet, name: value })}
            />
          </FormGroup>
          <FormGroup label="Version" fieldId="snippet-version">
            <TextInput
              type="text"
              id="snippet-version"
              value={editedSnippet.version}
              onChange={(_, value) => setEditedSnippet({ ...editedSnippet, version: value })}
              placeholder="e.g., 1.0.0"
            />
          </FormGroup>
          <FormGroup label="Description" isRequired fieldId="snippet-description">
            <TextArea
              isRequired
              id="snippet-description"
              value={editedSnippet.description}
              onChange={(_, value) => setEditedSnippet({ ...editedSnippet, description: value })}
              rows={2}
            />
          </FormGroup>
          <FormGroup label="State" isRequired fieldId="snippet-state">
            <FormSelect
              value={editedSnippet.state}
              onChange={(_, value) => setEditedSnippet({ ...editedSnippet, state: value as 'unknown' | 'any' | 'new' | 'checked' | 'approved' })}
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
            {editedSnippet.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {editedSnippet.tags.map((tag) => (
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
              value={editedSnippet.content}
              onChange={(_, value) => setEditedSnippet({ ...editedSnippet, content: value })}
              rows={10}
              placeholder="Enter your code snippet here..."
            />
          </FormGroup>
          <FormGroup label="Content Type" isRequired fieldId="snippet-content-type">
            <FormSelect
              value={editedSnippet.content_type}
              onChange={(_, value) => setEditedSnippet({ ...editedSnippet, content_type: value })}
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
          <FormGroup label="Additional Information (JSON)" fieldId="snippet-extra">
            <TextArea
              id="snippet-extra"
              value={extraInput}
              onChange={(_, value) => setExtraInput(value)}
              rows={5}
              placeholder='{"key": "value"}'
            />
            <Text component="small" style={{ color: '#6a6e73', marginTop: '0.25rem', display: 'block' }}>
              Optional key-value pairs for additional flexible information (must be valid JSON object)
            </Text>
          </FormGroup>
        </Form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete Snippet"
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        actions={[
          <Button
            key="delete"
            variant="danger"
            onClick={() => deleteMutation.mutate()}
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
          Are you sure you want to delete the snippet "{snippet?.name}"? This action cannot be undone.
        </Text>
      </Modal>
    </>
  );
}