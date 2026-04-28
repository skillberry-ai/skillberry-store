// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTagColor } from '../utils/tagColors';
import { useMCPClient } from '../hooks/useMCPClient';
import {
  PageSection,
  Title,
  Breadcrumb,
  BreadcrumbItem,
  Card,
  CardBody,
  CardTitle,
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
  Select,
  SelectOption,
  SelectList,
  MenuToggle,
  MenuToggleElement,
  ExpandableSection,
  CodeBlock,
  CodeBlockCode,
  ClipboardCopy,
  ClipboardCopyVariant,
} from '@patternfly/react-core';
import { EditIcon, TrashIcon, ConnectedIcon, DisconnectedIcon } from '@patternfly/react-icons';
import { vmcpApi, skillsApi } from '@/services/api';
import type { VMCPServer } from '@/types';

export function VMCPServerDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [editedServer, setEditedServer] = useState({
    name: '',
    version: '',
    description: '',
    state: 'approved' as 'unknown' | 'any' | 'new' | 'checked' | 'approved',
    tags: [] as string[],
    port: undefined as number | undefined,
    skill_uuid: '',
    extra: {} as Record<string, any>,
  });
  const [tagInput, setTagInput] = useState('');
  const [extraInput, setExtraInput] = useState('{}');
  const [editError, setEditError] = useState('');
  
  // Skill selection state
  const [isSkillSelectOpen, setIsSkillSelectOpen] = useState(false);
  const [skillSearchTerm, setSkillSearchTerm] = useState('');
  
  // Prompt content state
  const [promptContents, setPromptContents] = useState<Record<string, any>>({});
  const [loadingPrompts, setLoadingPrompts] = useState<Record<string, boolean>>({});

  const { data: server, isLoading, error } = useQuery({
    queryKey: ['vmcp-servers', name],
    queryFn: () => vmcpApi.get(name!),
    enabled: !!name,
  });

  // MCP Client connection
  const mcpClient = useMCPClient(server?.port, server?.name || '');

  // Fetch all skills for the dropdown
  const { data: allSkills } = useQuery({
    queryKey: ['skills'],
    queryFn: skillsApi.list,
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (updatedServer: Omit<VMCPServer, 'uuid' | 'runtime' | 'running'>) =>
      vmcpApi.update(name!, updatedServer),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vmcp-servers', name] });
      queryClient.invalidateQueries({ queryKey: ['vmcp-servers'] });
      setIsEditModalOpen(false);
      setEditError('');
    },
    onError: (error: any) => {
      setEditError(error.message || 'Failed to update VMCP server');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => vmcpApi.delete(name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vmcp-servers'] });
      navigate('/vmcp-servers');
    },
  });

  // Filter skills based on search term
  const filteredSkills = useMemo(() => {
    if (!allSkills) return [];
    if (!skillSearchTerm) return allSkills;
    const lowerSearch = skillSearchTerm.toLowerCase();
    return allSkills.filter(skill =>
      skill.name.toLowerCase().includes(lowerSearch) ||
      skill.description?.toLowerCase().includes(lowerSearch)
    );
  }, [allSkills, skillSearchTerm]);

  const handleSelectSkill = (_event: any, value: string | number | undefined) => {
    if (typeof value === 'string') {
      const selectedSkill = allSkills?.find(s => s.name === value);
      if (selectedSkill) {
        setEditedServer({
          ...editedServer,
          skill_uuid: selectedSkill.uuid,
        });
        setSkillSearchTerm(selectedSkill.name);
        setIsSkillSelectOpen(false);
      }
    }
  };

  const handleClearSkill = () => {
    setEditedServer({
      ...editedServer,
      skill_uuid: '',
    });
    setSkillSearchTerm('');
  };

  const handleEditClick = () => {
    if (server) {
      setEditedServer({
        name: server.name,
        version: server.version || '',
        description: server.description || '',
        state: server.state || 'approved',
        tags: server.tags || [],
        port: server.port,
        skill_uuid: server.skill_uuid || '',
        extra: server.extra || {},
      });
      setExtraInput(JSON.stringify(server.extra || {}, null, 2));
      // Set the skill search term to the current skill name if available
      if (server.skill_uuid && allSkills) {
        const currentSkill = allSkills.find(s => s.uuid === server.skill_uuid);
        if (currentSkill) {
          setSkillSearchTerm(currentSkill.name);
        }
      }
      setIsEditModalOpen(true);
    }
  };

  const handleUpdateServer = () => {
    if (!editedServer.name || !editedServer.description) {
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
    
    updateMutation.mutate({ ...editedServer, extra: Object.keys(parsedExtra).length > 0 ? parsedExtra : undefined });
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !editedServer.tags.includes(tagInput.trim())) {
      setEditedServer({
        ...editedServer,
        tags: [...editedServer.tags, tagInput.trim()],
      });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedServer({
      ...editedServer,
      tags: editedServer.tags.filter(tag => tag !== tagToRemove),
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
          <Title headingLevel="h1" size="2xl">
            {server.name}
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
          <CardTitle>Server Information</CardTitle>
          <CardBody>
            <DescriptionList isHorizontal>
              <DescriptionListGroup>
                <DescriptionListTerm>Name</DescriptionListTerm>
                <DescriptionListDescription>{server.name}</DescriptionListDescription>
              </DescriptionListGroup>
              
              <DescriptionListGroup>
                <DescriptionListTerm>Description</DescriptionListTerm>
                <DescriptionListDescription>
                  {server.description || 'No description'}
                </DescriptionListDescription>
              </DescriptionListGroup>

              {server.version && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Version</DescriptionListTerm>
                  <DescriptionListDescription>{server.version}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.state && (
                <DescriptionListGroup>
                  <DescriptionListTerm>State</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Label color={
                      server.state === 'approved' ? 'green' :
                      server.state === 'checked' ? 'blue' :
                      server.state === 'new' ? 'cyan' : 'orange'
                    }>
                      {server.state}
                    </Label>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              <DescriptionListGroup>
                <DescriptionListTerm>Status</DescriptionListTerm>
                <DescriptionListDescription>
                  {server.running ? (
                    <Label color="green">Running</Label>
                  ) : (
                    <Label color="red">Stopped</Label>
                  )}
                </DescriptionListDescription>
              </DescriptionListGroup>

              {server.port && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Port</DescriptionListTerm>
                  <DescriptionListDescription>{server.port}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.skill_uuid && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Skill UUID</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Text component="small" style={{ fontFamily: 'monospace' }}>
                      {server.skill_uuid}
                    </Text>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.tags && server.tags.length > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Tags</DescriptionListTerm>
                  <DescriptionListDescription>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {server.tags.map((tag) => (
                        <Label key={tag} color={getTagColor(tag)}>{tag}</Label>
                      ))}
                    </div>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.created_at && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Created</DescriptionListTerm>
                  <DescriptionListDescription>
                    {new Date(server.created_at).toLocaleString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.modified_at && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Last Modified</DescriptionListTerm>
                  <DescriptionListDescription>
                    {new Date(server.modified_at).toLocaleString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              <DescriptionListGroup>
                <DescriptionListTerm>UUID</DescriptionListTerm>
                <DescriptionListDescription>
                  <Text component="small" style={{ fontFamily: 'monospace' }}>
                    {server.uuid}
                  </Text>
                </DescriptionListDescription>
              </DescriptionListGroup>

              {server.extra && Object.keys(server.extra).length > 0 && (
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
                        {JSON.stringify(server.extra, null, 2)}
                      </CodeBlockCode>
                    </CodeBlock>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
            </DescriptionList>
          </CardBody>
        </Card>

        {server.runtime && (
          <Card style={{ marginTop: '1rem' }}>
            <CardTitle>Runtime Information</CardTitle>
            <CardBody>
              <DescriptionList isHorizontal>
                <DescriptionListGroup>
                  <DescriptionListTerm>Runtime Name</DescriptionListTerm>
                  <DescriptionListDescription>{server.runtime.name}</DescriptionListDescription>
                </DescriptionListGroup>

                {server.runtime.description && (
                  <DescriptionListGroup>
                    <DescriptionListTerm>Runtime Description</DescriptionListTerm>
                    <DescriptionListDescription>{server.runtime.description}</DescriptionListDescription>
                  </DescriptionListGroup>
                )}

                {server.runtime.port && (
                  <DescriptionListGroup>
                    <DescriptionListTerm>Runtime Port</DescriptionListTerm>
                    <DescriptionListDescription>{server.runtime.port}</DescriptionListDescription>
                  </DescriptionListGroup>
                )}

                {server.runtime.tools && server.runtime.tools.length > 0 && (
                  <DescriptionListGroup>
                    <DescriptionListTerm>Tools</DescriptionListTerm>
                    <DescriptionListDescription>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {server.runtime.tools.map((tool) => (
                          <Label key={tool} color="blue" isCompact>
                            {tool}
                          </Label>
                        ))}
                      </div>
                    </DescriptionListDescription>
                  </DescriptionListGroup>
                )}
              </DescriptionList>
            </CardBody>
          </Card>
        )}

        {/* MCP Connection Status and Tools/Prompts */}
        <Card style={{ marginTop: '1rem' }}>
          <CardTitle>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              MCP Connection Status
              {mcpClient.isConnected ? (
                <Label color="green" icon={<ConnectedIcon />}>Connected</Label>
              ) : mcpClient.isConnecting ? (
                <Label color="blue"><Spinner size="sm" /> Connecting...</Label>
              ) : (
                <Label color="red" icon={<DisconnectedIcon />}>Disconnected</Label>
              )}
            </div>
          </CardTitle>
          <CardBody>
            {mcpClient.error && (
              <Alert variant="warning" title="Connection Error" isInline style={{ marginBottom: '1rem' }}>
                {mcpClient.error}
              </Alert>
            )}
            
            {mcpClient.isConnected && (
              <>
                <DescriptionList isHorizontal>
                  <DescriptionListGroup>
                    <DescriptionListTerm>Available Tools</DescriptionListTerm>
                    <DescriptionListDescription>
                      <Label color="blue" isCompact>{mcpClient.tools.length}</Label>
                    </DescriptionListDescription>
                  </DescriptionListGroup>
                  <DescriptionListGroup>
                    <DescriptionListTerm>Available Prompts</DescriptionListTerm>
                    <DescriptionListDescription>
                      <Label color="purple" isCompact>{mcpClient.prompts.length}</Label>
                    </DescriptionListDescription>
                  </DescriptionListGroup>
                </DescriptionList>

                {/* Tools Section */}
                {mcpClient.tools.length > 0 && (
                  <div style={{ marginTop: '1.5rem' }}>
                    <Title headingLevel="h3" size="md" style={{ marginBottom: '1rem' }}>
                      Tools
                    </Title>
                    {mcpClient.tools.map((tool, index) => (
                      <ExpandableSection
                        key={tool.name}
                        toggleText={tool.name}
                        style={{ marginBottom: '0.5rem' }}
                      >
                        <Card isCompact>
                          <CardBody>
                            {tool.description && (
                              <Text style={{ marginBottom: '1rem', fontSize: '1rem' }}>
                                {tool.description}
                              </Text>
                            )}
                            {tool.inputSchema && (
                              <>
                                <Text component="h4" style={{ marginBottom: '0.5rem', fontWeight: 'bold' }}>
                                  Input Schema:
                                </Text>
                                <div style={{
                                  backgroundColor: '#f5f5f5',
                                  border: '1px solid #d2d2d2',
                                  borderRadius: '4px',
                                  padding: '0',
                                  overflow: 'auto'
                                }}>
                                  <pre style={{
                                    margin: 0,
                                    padding: '1rem',
                                    fontFamily: 'monospace',
                                    fontSize: '0.875rem',
                                    color: '#151515',
                                    backgroundColor: '#f5f5f5',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word'
                                  } as React.CSSProperties}>
                                    {JSON.stringify(tool.inputSchema, null, 2)}
                                  </pre>
                                </div>
                              </>
                            )}
                          </CardBody>
                        </Card>
                      </ExpandableSection>
                    ))}
                  </div>
                )}

                {/* Prompts Section */}
                {mcpClient.prompts.length > 0 && (
                  <div style={{ marginTop: '1.5rem' }}>
                    <Title headingLevel="h3" size="md" style={{ marginBottom: '1rem' }}>
                      Prompts
                    </Title>
                    {mcpClient.prompts.map((prompt, index) => (
                      <ExpandableSection
                        key={prompt.name}
                        toggleText={prompt.name}
                        style={{ marginBottom: '0.5rem' }}
                        onToggle={async (_, isExpanded) => {
                          if (isExpanded && !promptContents[prompt.name] && !loadingPrompts[prompt.name]) {
                            setLoadingPrompts(prev => ({ ...prev, [prompt.name]: true }));
                            const content = await mcpClient.getPrompt(prompt.name);
                            if (content) {
                              setPromptContents(prev => ({ ...prev, [prompt.name]: content }));
                            }
                            setLoadingPrompts(prev => ({ ...prev, [prompt.name]: false }));
                          }
                        }}
                      >
                        <Card isCompact>
                          <CardBody>
                            {prompt.description && (
                              <Text style={{ marginBottom: '1rem' }}>
                                {prompt.description}
                              </Text>
                            )}
                            
                            {loadingPrompts[prompt.name] && (
                              <div style={{ display: 'flex', justifyContent: 'center', padding: '1rem' }}>
                                <Spinner size="md" />
                              </div>
                            )}
                            
                            {promptContents[prompt.name] && !loadingPrompts[prompt.name] && (
                              <>
                                {promptContents[prompt.name].messages && promptContents[prompt.name].messages.length > 0 && (
                                  <>
                                    <Text component="h4" style={{ marginBottom: '0.5rem', fontWeight: 'bold' }}>
                                      Prompt Content:
                                    </Text>
                                    {promptContents[prompt.name].messages.map((msg: any, msgIndex: number) => (
                                      <div key={msgIndex} style={{ marginBottom: '1rem' }}>
                                        <Label color={msg.role === 'user' ? 'blue' : 'green'} style={{ marginBottom: '0.5rem' }}>
                                          {msg.role}
                                        </Label>
                                        <div style={{
                                          backgroundColor: '#f5f5f5',
                                          border: '1px solid #d2d2d2',
                                          borderRadius: '4px',
                                          padding: '0',
                                          overflow: 'auto'
                                        }}>
                                          <pre style={{
                                            margin: 0,
                                            padding: '1rem',
                                            fontFamily: 'monospace',
                                            fontSize: '0.875rem',
                                            color: '#151515',
                                            backgroundColor: '#f5f5f5',
                                            whiteSpace: 'pre-wrap',
                                            wordBreak: 'break-word'
                                          } as React.CSSProperties}>
                                            {msg.content.text || JSON.stringify(msg.content, null, 2)}
                                          </pre>
                                        </div>
                                      </div>
                                    ))}
                                  </>
                                )}
                              </>
                            )}
                            
                            {prompt.arguments && prompt.arguments.length > 0 && (
                              <>
                                <Text component="h4" style={{ marginBottom: '0.5rem', fontWeight: 'bold', marginTop: '1rem' }}>
                                  Arguments:
                                </Text>
                                <div style={{
                                  backgroundColor: '#f5f5f5',
                                  border: '1px solid #d2d2d2',
                                  borderRadius: '4px',
                                  padding: '0',
                                  overflow: 'auto'
                                }}>
                                  <pre style={{
                                    margin: 0,
                                    padding: '1rem',
                                    fontFamily: 'monospace',
                                    fontSize: '0.875rem',
                                    color: '#151515',
                                    backgroundColor: '#f5f5f5',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word'
                                  } as React.CSSProperties}>
                                    {JSON.stringify(prompt.arguments, null, 2)}
                                  </pre>
                                </div>
                              </>
                            )}
                          </CardBody>
                        </Card>
                      </ExpandableSection>
                    ))}
                  </div>
                )}
              </>
            )}

            {!mcpClient.isConnected && !mcpClient.isConnecting && (
              <Button variant="primary" onClick={mcpClient.connect}>
                Reconnect to MCP Server
              </Button>
            )}
          </CardBody>
        </Card>

        {/* Connect to Claude Code */}
        {server.port && (
          <Card style={{ marginTop: '1rem' }}>
            <CardTitle>Connect to Claude Code</CardTitle>
            <CardBody>
              <Text style={{ marginBottom: '1rem' }}>
                Use the following command to add this MCP server to Claude Code. This registers the server using SSE transport so Claude Code can discover and call its tools.
              </Text>
              <Text component="h4" style={{ marginBottom: '0.5rem', fontWeight: 'bold' }}>
                Add to Claude Code:
              </Text>
              <ClipboardCopy
                isReadOnly
                hoverTip="Copy"
                clickTip="Copied"
                variant={ClipboardCopyVariant.expansion}
                style={{ marginBottom: '1rem' }}
              >
                {`claude mcp add ${server.name} -s user -t sse http://localhost:${server.port}/sse`}
              </ClipboardCopy>
              <Text style={{ marginBottom: '0.5rem', marginTop: '1rem' }} component="small">
                <strong>-s user</strong> saves to your user-level settings (available across all projects).
                Use <strong>-s project</strong> to save to the current project only.
              </Text>
              <Text style={{ marginBottom: '1rem' }} component="small">
                <strong>-t sse</strong> sets the transport to Server-Sent Events, which is the protocol this MCP server uses.
              </Text>
              <Text component="h4" style={{ marginBottom: '0.5rem', fontWeight: 'bold', marginTop: '1rem' }}>
                Remove from Claude Code:
              </Text>
              <ClipboardCopy
                isReadOnly
                hoverTip="Copy"
                clickTip="Copied"
                style={{ marginBottom: '0.5rem' }}
              >
                {`claude mcp remove ${server.name} -s user`}
              </ClipboardCopy>
            </CardBody>
          </Card>
        )}
      </PageSection>

      {/* Edit Modal */}
      <Modal
        variant={ModalVariant.large}
        title="Edit VMCP Server"
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditError('');
        }}
        actions={[
          <Button
            key="update"
            variant="primary"
            onClick={handleUpdateServer}
            isLoading={updateMutation.isPending}
          >
            Update
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsEditModalOpen(false);
              setEditError('');
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
          <FormGroup label="Name" isRequired fieldId="server-name">
            <TextInput
              isRequired
              type="text"
              id="server-name"
              value={editedServer.name}
              onChange={(_, value) => setEditedServer({ ...editedServer, name: value })}
            />
          </FormGroup>
          <FormGroup label="Version" fieldId="server-version">
            <TextInput
              type="text"
              id="server-version"
              value={editedServer.version}
              onChange={(_, value) => setEditedServer({ ...editedServer, version: value })}
              placeholder="e.g., 1.0.0"
            />
          </FormGroup>
          <FormGroup label="Description" isRequired fieldId="server-description">
            <TextArea
              isRequired
              id="server-description"
              value={editedServer.description}
              onChange={(_, value) => setEditedServer({ ...editedServer, description: value })}
              rows={3}
            />
          </FormGroup>
          <FormGroup label="State" isRequired fieldId="server-state">
            <FormSelect
              value={editedServer.state}
              onChange={(_, value) => setEditedServer({ ...editedServer, state: value as 'unknown' | 'any' | 'new' | 'checked' | 'approved' })}
              id="server-state"
            >
              <FormSelectOption value="unknown" label="Unknown" />
              <FormSelectOption value="any" label="Any" />
              <FormSelectOption value="new" label="New" />
              <FormSelectOption value="checked" label="Checked" />
              <FormSelectOption value="approved" label="Approved" />
            </FormSelect>
          </FormGroup>
          <FormGroup label="Port" fieldId="server-port">
            <TextInput
              type="number"
              id="server-port"
              value={editedServer.port?.toString() || ''}
              onChange={(_, value) => setEditedServer({ ...editedServer, port: value ? parseInt(value) : undefined })}
              placeholder="Leave empty for auto-assignment"
            />
          </FormGroup>
          <FormGroup label="Skill" fieldId="server-skill">
            <Text component="small" style={{ display: 'block', marginBottom: '0.5rem', color: '#6a6e73' }}>
              Search and select a skill to expose via this VMCP server
            </Text>
            <Select
              id="server-skill-select"
              isOpen={isSkillSelectOpen}
              selected={null}
              onSelect={handleSelectSkill}
              onOpenChange={(isOpen) => setIsSkillSelectOpen(isOpen)}
              toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                <MenuToggle
                  ref={toggleRef}
                  onClick={() => setIsSkillSelectOpen(!isSkillSelectOpen)}
                  isExpanded={isSkillSelectOpen}
                  style={{ width: '100%' }}
                >
                  {skillSearchTerm || 'Select a skill...'}
                </MenuToggle>
              )}
            >
              <SelectList>
                <TextInput
                  type="search"
                  value={skillSearchTerm}
                  onChange={(_, value) => setSkillSearchTerm(value)}
                  placeholder="Search skills..."
                  style={{ padding: '0.5rem', borderBottom: '1px solid #d2d2d2' }}
                />
                {filteredSkills.length === 0 ? (
                  <SelectOption isDisabled>
                    {skillSearchTerm ? 'No skills found' : 'Start typing to search...'}
                  </SelectOption>
                ) : (
                  filteredSkills.map((skill) => (
                    <SelectOption key={skill.uuid} value={skill.name}>
                      {skill.name} {skill.description && `- ${skill.description}`}
                    </SelectOption>
                  ))
                )}
              </SelectList>
            </Select>
            {editedServer.skill_uuid && (
              <div style={{ marginTop: '0.5rem' }}>
                <Button
                  variant="plain"
                  onClick={handleClearSkill}
                  style={{
                    padding: '0.25rem 0.5rem',
                    backgroundColor: '#e7f1fa',
                    border: '1px solid #bee1f4',
                    borderRadius: '3px',
                  }}
                >
                  {skillSearchTerm} ✕
                </Button>
              </div>
            )}
          </FormGroup>
          <FormGroup label="Tags" fieldId="server-tags">
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <TextInput
                type="text"
                id="server-tags"
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
            {editedServer.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {editedServer.tags.map((tag) => (
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
          <FormGroup label="Additional Information (JSON)" fieldId="server-extra">
            <TextArea
              id="server-extra"
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
        title="Delete VMCP Server"
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
          Are you sure you want to delete the VMCP server "{server.name}"?
          This action cannot be undone.
        </Text>
      </Modal>
    </>
  );
}