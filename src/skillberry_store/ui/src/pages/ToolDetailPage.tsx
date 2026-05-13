// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTagColor } from '../utils/tagColors';
import {
  PageSection,
  Title,
  Button,
  Card,
  CardBody,
  CardTitle,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Spinner,
  Alert,
  Breadcrumb,
  BreadcrumbItem,
  Label,
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  CodeBlock,
  CodeBlockCode,
  Tabs,
  Tab,
  TabTitleText,
  Text,
  FormSelect,
  FormSelectOption,
} from '@patternfly/react-core';
import { PlayIcon, TrashIcon, EditIcon } from '@patternfly/react-icons';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { toolsApi } from '@/services/api';
import type { ExecutionResult, Tool } from '@/types';

export function ToolDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTabKey, setActiveTabKey] = useState(0);
  const [isExecuteModalOpen, setIsExecuteModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [executionParams, setExecutionParams] = useState('{}');
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [editedTool, setEditedTool] = useState({
    name: '',
    description: '',
    version: '',
    state: 'approved' as 'unknown' | 'any' | 'new' | 'checked' | 'approved',
    tags: [] as string[],
    module_name: '',
    programming_language: 'python',
    packaging_format: 'code',
    extra: {} as Record<string, any>,
  });
  const [tagInput, setTagInput] = useState('');
  const [extraInput, setExtraInput] = useState('{}');
  const [editError, setEditError] = useState('');

  // Fetch tool details
  const { data: tool, isLoading, error } = useQuery({
    queryKey: ['tools', name],
    queryFn: () => toolsApi.get(name!),
    enabled: !!name,
  });

  // Fetch module code
  const { data: moduleCode, isLoading: isModuleLoading, error: moduleError } = useQuery({
    queryKey: ['tools', name, 'module'],
    queryFn: () => toolsApi.getModule(name!),
    enabled: !!name && !!tool?.module_name,
  });

  // Execute tool mutation
  const executeMutation = useMutation({
    mutationFn: (params: Record<string, any>) => toolsApi.execute(name!, params),
    onSuccess: (result) => {
      setExecutionResult(result);
    },
    onError: (error: any) => {
      setExecutionResult({
        error: error.message || 'An error occurred during execution',
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (updatedTool: Tool) =>
      toolsApi.update(name!, updatedTool),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools', name] });
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      setIsEditModalOpen(false);
      setEditError('');
    },
    onError: (error: any) => {
      setEditError(error.message || 'Failed to update tool');
    },
  });

  // Delete tool mutation
  const deleteMutation = useMutation({
    mutationFn: () => toolsApi.delete(name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      navigate('/tools');
    },
  });

  const handleExecute = () => {
    try {
      const params = JSON.parse(executionParams);
      executeMutation.mutate(params);
    } catch (e) {
      setExecutionResult({
        error: 'Invalid JSON parameters',
      });
    }
  };

  const handleEditClick = () => {
    if (tool) {
      setEditedTool({
        name: tool.name,
        description: tool.description,
        version: tool.version || '',
        state: tool.state || 'approved',
        tags: tool.tags || [],
        module_name: tool.module_name || '',
        programming_language: tool.programming_language || 'python',
        packaging_format: tool.packaging_format || 'code',
        extra: tool.extra || {},
      });
      setExtraInput(JSON.stringify(tool.extra || {}, null, 2));
      setIsEditModalOpen(true);
    }
  };

  const handleUpdateTool = () => {
    if (!editedTool.name || !editedTool.description) {
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
    
    updateMutation.mutate({ ...tool!, ...editedTool, extra: Object.keys(parsedExtra).length > 0 ? parsedExtra : undefined });
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !editedTool.tags.includes(tagInput.trim())) {
      setEditedTool({
        ...editedTool,
        tags: [...editedTool.tags, tagInput.trim()],
      });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedTool({
      ...editedTool,
      tags: editedTool.tags.filter(tag => tag !== tagToRemove),
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

  if (error || !tool) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading tool">
          {(error as Error)?.message || 'Tool not found'}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Breadcrumb>
          <BreadcrumbItem to="/tools" onClick={(e) => { e.preventDefault(); navigate('/tools'); }}>
            Tools
          </BreadcrumbItem>
          <BreadcrumbItem isActive>{tool.name}</BreadcrumbItem>
        </Breadcrumb>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
          <Title headingLevel="h1" size="2xl">
            {tool.name}
          </Title>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button
              variant="primary"
              icon={<PlayIcon />}
              onClick={() => setIsExecuteModalOpen(true)}
            >
              Execute
            </Button>
            <Button
              variant="secondary"
              icon={<EditIcon />}
              onClick={handleEditClick}
            >
              Edit
            </Button>
            <Button
              variant="danger"
              icon={<TrashIcon />}
              onClick={() => setIsDeleteModalOpen(true)}
            >
              Delete
            </Button>
          </div>
        </div>
      </PageSection>

      <PageSection>
        <Tabs activeKey={activeTabKey} onSelect={(_, tabIndex) => setActiveTabKey(tabIndex as number)}>
          <Tab eventKey={0} title={<TabTitleText>Details</TabTitleText>}>
            <Card>
              <CardTitle>Tool Information</CardTitle>
              <CardBody>
                <DescriptionList isHorizontal>
                  <DescriptionListGroup>
                    <DescriptionListTerm>Name</DescriptionListTerm>
                    <DescriptionListDescription>{tool.name}</DescriptionListDescription>
                  </DescriptionListGroup>
                  
                  <DescriptionListGroup>
                    <DescriptionListTerm>Description</DescriptionListTerm>
                    <DescriptionListDescription>
                      {tool.description || 'No description'}
                    </DescriptionListDescription>
                  </DescriptionListGroup>

                  {tool.version && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Version</DescriptionListTerm>
                      <DescriptionListDescription>{tool.version}</DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.state && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>State</DescriptionListTerm>
                      <DescriptionListDescription>
                        <Label color={
                          tool.state === 'approved' ? 'green' :
                          tool.state === 'checked' ? 'blue' :
                          tool.state === 'new' ? 'cyan' : 'orange'
                        }>
                          {tool.state}
                        </Label>
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.tags && tool.tags.length > 0 && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Tags</DescriptionListTerm>
                      <DescriptionListDescription>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          {tool.tags.map((tag) => (
                            <Label key={tag} color={getTagColor(tag)}>{tag}</Label>
                          ))}
                        </div>
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.module_name && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Module Name</DescriptionListTerm>
                      <DescriptionListDescription>{tool.module_name}</DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.programming_language && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Programming Language</DescriptionListTerm>
                      <DescriptionListDescription>{tool.programming_language}</DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.packaging_format && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Packaging Format</DescriptionListTerm>
                      <DescriptionListDescription>{tool.packaging_format}</DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.dependencies && tool.dependencies.length > 0 && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Dependencies</DescriptionListTerm>
                      <DescriptionListDescription>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          {tool.dependencies.map((dep) => (
                            <Label key={dep} color="blue">{dep}</Label>
                          ))}
                        </div>
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.params && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Parameters</DescriptionListTerm>
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
                            {JSON.stringify(tool.params, null, 2)}
                          </CodeBlockCode>
                        </CodeBlock>
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.returns && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Returns</DescriptionListTerm>
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
                            {JSON.stringify(tool.returns, null, 2)}
                          </CodeBlockCode>
                        </CodeBlock>
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.author && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Author</DescriptionListTerm>
                      <DescriptionListDescription>{tool.author}</DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.created_at && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Created</DescriptionListTerm>
                      <DescriptionListDescription>
                        {new Date(tool.created_at).toLocaleString()}
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  {tool.modified_at && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Last Modified</DescriptionListTerm>
                      <DescriptionListDescription>
                        {new Date(tool.modified_at).toLocaleString()}
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}

                  <DescriptionListGroup>
                    <DescriptionListTerm>UUID</DescriptionListTerm>
                    <DescriptionListDescription>
                      <Text component="small" style={{ fontFamily: 'monospace' }}>
                        {tool.uuid}
                      </Text>
                    </DescriptionListDescription>
                  </DescriptionListGroup>

                  {tool.extra && Object.keys(tool.extra).length > 0 && (
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
                            {JSON.stringify(tool.extra, null, 2)}
                          </CodeBlockCode>
                        </CodeBlock>
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}
                </DescriptionList>
              </CardBody>
            </Card>
          </Tab>

          {tool.module_name ? (
            <Tab eventKey={1} title={<TabTitleText>Source Code</TabTitleText>}>
              <Card>
                <CardTitle>Module Code ({tool.module_name})</CardTitle>
                <CardBody>
                  {isModuleLoading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
                      <Spinner size="lg" />
                    </div>
                  ) : moduleError ? (
                    <Alert variant="danger" title="Error loading module code">
                      {(moduleError as Error).message}
                    </Alert>
                  ) : moduleCode ? (
                    <div style={{
                      maxHeight: '70vh',
                      overflow: 'auto',
                      border: '1px solid #3d3d3d',
                      borderRadius: '6px'
                    }}>
                      <SyntaxHighlighter
                        language="python"
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
                        {moduleCode}
                      </SyntaxHighlighter>
                    </div>
                  ) : (
                    <Text>No module code available</Text>
                  )}
                </CardBody>
              </Card>
            </Tab>
          ) : null}
        </Tabs>
      </PageSection>

      {/* Execute Modal */}
      <Modal
        variant={ModalVariant.large}
        title={`Execute ${tool.name}`}
        isOpen={isExecuteModalOpen}
        onClose={() => {
          setIsExecuteModalOpen(false);
          setExecutionResult(null);
          setExecutionParams('{}');
        }}
        actions={[
          <Button
            key="execute"
            variant="primary"
            onClick={handleExecute}
            isLoading={executeMutation.isPending}
          >
            Execute
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsExecuteModalOpen(false);
              setExecutionResult(null);
              setExecutionParams('{}');
            }}
          >
            Close
          </Button>,
        ]}
      >
        <Form>
          <FormGroup label="Parameters (JSON)" fieldId="execution-params">
            <TextInput
              type="text"
              id="execution-params"
              value={executionParams}
              onChange={(_, value) => setExecutionParams(value)}
              placeholder='{"param1": "value1"}'
            />
          </FormGroup>
        </Form>

        {executionResult && (
          <div style={{ marginTop: '1rem' }}>
            {executionResult.error ? (
              <Alert variant="danger" title="Execution Failed" isInline>
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', color: '#151515' }}>
                    Error Details:
                  </div>
                  <div style={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontFamily: 'monospace',
                    color: '#151515',
                    backgroundColor: '#fff5f5',
                    padding: '0.75rem',
                    fontSize: '14px',
                    borderRadius: '4px',
                    border: '1px solid #c9190b'
                  }}>
                    {executionResult.error}
                  </div>
                </div>
                {executionResult.stderr && (
                  <div style={{ marginTop: '1rem' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', color: '#151515' }}>
                      Standard Error Output:
                    </div>
                    <div style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      fontFamily: 'monospace',
                      color: '#c9190b',
                      backgroundColor: '#fff5f5',
                      padding: '0.75rem',
                      fontSize: '13px',
                      borderRadius: '4px',
                      border: '1px solid #c9190b'
                    }}>
                      {executionResult.stderr}
                    </div>
                  </div>
                )}
                {executionResult.stdout && (
                  <div style={{ marginTop: '1rem' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', color: '#151515' }}>
                      Standard Output (before failure):
                    </div>
                    <div style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      fontFamily: 'monospace',
                      color: '#151515',
                      backgroundColor: '#f5f5f5',
                      padding: '0.75rem',
                      fontSize: '13px',
                      borderRadius: '4px',
                      border: '1px solid #d2d2d2'
                    }}>
                      {executionResult.stdout}
                    </div>
                  </div>
                )}
                <div style={{ marginTop: '1rem', padding: '0.75rem', backgroundColor: '#f0f0f0', borderRadius: '4px' }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', color: '#151515' }}>
                    Troubleshooting Tips:
                  </div>
                  <ul style={{ margin: '0', paddingLeft: '1.5rem', color: '#151515' }}>
                    <li>Verify that all required parameters are provided with correct types</li>
                    <li>Check if the tool has any missing dependencies</li>
                    <li>Review the tool's source code for any syntax or logic errors</li>
                    <li>Ensure the execution environment has necessary permissions</li>
                  </ul>
                </div>
              </Alert>
            ) : (
              <Alert variant="success" title="Execution Result" isInline>
                <div style={{
                  fontSize: '14px',
                  lineHeight: '1.6',
                  padding: '1rem',
                  backgroundColor: '#ffffff',
                  color: '#151515',
                  borderRadius: '4px',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  border: '1px solid #d2d2d2',
                  fontFamily: 'monospace'
                }}>
                  {JSON.stringify(executionResult, null, 2)}
                </div>
                {executionResult.stdout && (
                  <div style={{ marginTop: '1rem' }}>
                    <div style={{ color: '#151515', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                      Standard Output:
                    </div>
                    <div style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      padding: '0.5rem',
                      backgroundColor: '#f5f5f5',
                      borderRadius: '4px',
                      fontFamily: 'monospace',
                      fontSize: '13px',
                      color: '#151515'
                    }}>
                      {executionResult.stdout}
                    </div>
                  </div>
                )}
                {executionResult.stderr && (
                  <div style={{ marginTop: '1rem' }}>
                    <div style={{ color: '#151515', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                      Standard Error:
                    </div>
                    <div style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      padding: '0.5rem',
                      backgroundColor: '#fff5f5',
                      borderRadius: '4px',
                      fontFamily: 'monospace',
                      fontSize: '13px',
                      color: '#c9190b'
                    }}>
                      {executionResult.stderr}
                    </div>
                  </div>
                )}
                {executionResult.execution_time && (
                  <div style={{ marginTop: '1rem', fontSize: '13px', color: '#6a6e73' }}>
                    Execution time: {executionResult.execution_time.toFixed(3)}s
                  </div>
                )}
              </Alert>
            )}
          </div>
        )}
      </Modal>

      {/* Edit Modal */}
      <Modal
        variant={ModalVariant.large}
        title="Edit Tool"
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
            onClick={handleUpdateTool}
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
          <FormGroup label="Name" isRequired fieldId="tool-name">
            <TextInput
              isRequired
              type="text"
              id="tool-name"
              value={editedTool.name}
              onChange={(_, value) => setEditedTool({ ...editedTool, name: value })}
            />
          </FormGroup>
          <FormGroup label="Description" isRequired fieldId="tool-description">
            <TextArea
              isRequired
              id="tool-description"
              value={editedTool.description}
              onChange={(_, value) => setEditedTool({ ...editedTool, description: value })}
              rows={3}
            />
          </FormGroup>
          <FormGroup label="Version" fieldId="tool-version">
            <TextInput
              type="text"
              id="tool-version"
              value={editedTool.version}
              onChange={(_, value) => setEditedTool({ ...editedTool, version: value })}
              placeholder="e.g., 1.0.0"
            />
          </FormGroup>
          <FormGroup label="State" isRequired fieldId="tool-state">
            <FormSelect
              value={editedTool.state}
              onChange={(_, value) => setEditedTool({ ...editedTool, state: value as 'unknown' | 'any' | 'new' | 'checked' | 'approved' })}
              id="tool-state"
            >
              <FormSelectOption value="unknown" label="Unknown" />
              <FormSelectOption value="any" label="Any" />
              <FormSelectOption value="new" label="New" />
              <FormSelectOption value="checked" label="Checked" />
              <FormSelectOption value="approved" label="Approved" />
            </FormSelect>
          </FormGroup>
          <FormGroup label="Tags" fieldId="tool-tags">
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <TextInput
                type="text"
                id="tool-tags"
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
            {editedTool.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {editedTool.tags.map((tag) => (
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
          <FormGroup label="Module Name" fieldId="tool-module-name">
            <TextInput
              type="text"
              id="tool-module-name"
              value={editedTool.module_name}
              readOnly
              isDisabled
            />
            <Text component="small" style={{ color: '#6a6e73', marginTop: '0.25rem', display: 'block' }}>
              Module name is set from the uploaded file and cannot be changed
            </Text>
          </FormGroup>
          <FormGroup label="Programming Language" fieldId="tool-programming-language">
            <TextInput
              type="text"
              id="tool-programming-language"
              value={editedTool.programming_language}
              onChange={(_, value) => setEditedTool({ ...editedTool, programming_language: value })}
              placeholder="e.g., python, javascript"
            />
          </FormGroup>
          <FormGroup label="Packaging Format" fieldId="tool-packaging-format">
            <TextInput
              type="text"
              id="tool-packaging-format"
              value={editedTool.packaging_format}
              onChange={(_, value) => setEditedTool({ ...editedTool, packaging_format: value })}
              placeholder="e.g., code, json"
            />
          </FormGroup>
          <FormGroup label="Additional Information (JSON)" fieldId="tool-extra">
            <TextArea
              id="tool-extra"
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
        title="Delete Tool"
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
          Are you sure you want to delete the tool "{tool.name}"? This action cannot be undone.
        </Text>
      </Modal>
    </>
  );
}
