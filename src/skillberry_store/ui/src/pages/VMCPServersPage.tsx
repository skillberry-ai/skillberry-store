// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTagColor } from '../utils/tagColors';
import { TagFilter } from '../components/TagFilter';
import { SearchBox, SearchMode } from '../components/SearchBox';
import {
  PageSection,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Button,
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
  FileUpload,
  Select,
  SelectOption,
  SelectList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import { Table, Thead, Tr, Th, Tbody, Td, ThProps } from '@patternfly/react-table';
import { PlusIcon, ServerIcon, SearchIcon, TrashIcon, ExportIcon, ImportIcon } from '@patternfly/react-icons';
import { vmcpApi, skillsApi } from '@/services/api';
import type { VMCPServer } from '@/types';

type SortableColumn = 'name' | 'description' | 'state' | 'port' | 'version';

export function VMCPServersPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('text');
  const [maxResults, setMaxResults] = useState(10);
  const [similarityThreshold, setSimilarityThreshold] = useState(1);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newServer, setNewServer] = useState({
    name: '',
    version: '',
    description: '',
    state: 'approved' as 'unknown' | 'any' | 'new' | 'checked' | 'approved',
    tags: [] as string[],
    port: undefined as number | undefined,
    skill_uuid: '',
  });
  const [tagInput, setTagInput] = useState('');
  const [createError, setCreateError] = useState('');
  const [selectedServers, setSelectedServers] = useState<string[]>([]);
  
  // Skill selection state
  const [isSkillSelectOpen, setIsSkillSelectOpen] = useState(false);
  const [skillSearchTerm, setSkillSearchTerm] = useState('');
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importError, setImportError] = useState('');
  const [activeSortIndex, setActiveSortIndex] = useState<number | null>(null);
  const [activeSortDirection, setActiveSortDirection] = useState<'asc' | 'desc'>('asc');

  const { data: servers, isLoading, error } = useQuery({
    queryKey: ['vmcp-servers'],
    queryFn: vmcpApi.list,
  });

  // Fetch all skills for the dropdown
  const { data: allSkills } = useQuery({
    queryKey: ['skills'],
    queryFn: skillsApi.list,
  });

  // Semantic search servers (only when in semantic mode)
  const { data: searchResults } = useQuery({
    queryKey: ['vmcp-servers', 'search', searchTerm, maxResults, similarityThreshold],
    queryFn: () => vmcpApi.search(searchTerm, maxResults, similarityThreshold),
    enabled: searchTerm.length > 0 && searchMode === 'semantic',
  });

  // Create server mutation
  const createMutation = useMutation({
    mutationFn: (server: Omit<VMCPServer, 'uuid' | 'runtime' | 'running'>) =>
      vmcpApi.create(server),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vmcp-servers'] });
      setIsCreateModalOpen(false);
      setNewServer({
        name: '',
        version: '',
        description: '',
        state: 'approved',
        tags: [],
        port: undefined,
        skill_uuid: '',
      });
      setTagInput('');
      setCreateError('');
    },
    onError: (error: any) => {
      setCreateError(error.message || 'Failed to create VMCP server');
    },
  });

  // Delete servers mutation
  const deleteMutation = useMutation({
    mutationFn: async (names: string[]) => {
      await Promise.all(names.map(name => vmcpApi.delete(name)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vmcp-servers'] });
      setSelectedServers([]);
      setIsDeleteModalOpen(false);
    },
  });

  const handleCreateServer = () => {
    if (!newServer.name || !newServer.description) {
      setCreateError('Please fill in all required fields');
      return;
    }
    console.log('Creating VMCP server with data:', newServer);
    createMutation.mutate(newServer);
  };

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
        setNewServer({
          ...newServer,
          skill_uuid: selectedSkill.uuid,
        });
        setSkillSearchTerm(selectedSkill.name);
        setIsSkillSelectOpen(false);
      }
    }
  };

  const handleClearSkill = () => {
    setNewServer({
      ...newServer,
      skill_uuid: '',
    });
    setSkillSearchTerm('');
  };

  const handleAddTag = () => {
    console.log('handleAddTag called, tagInput:', tagInput);
    console.log('Current tags:', newServer.tags);
    if (tagInput.trim() && !newServer.tags.includes(tagInput.trim())) {
      const updatedTags = [...newServer.tags, tagInput.trim()];
      console.log('Adding tag, new tags array:', updatedTags);
      setNewServer({
        ...newServer,
        tags: updatedTags,
      });
      setTagInput('');
    } else {
      console.log('Tag not added - either empty or duplicate');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setNewServer({
      ...newServer,
      tags: newServer.tags.filter(tag => tag !== tagToRemove),
    });
  };

  const handleSelectServer = (serverName: string, isSelected: boolean) => {
    setSelectedServers(prev =>
      isSelected
        ? [...prev, serverName]
        : prev.filter(name => name !== serverName)
    );
  };

  const handleSelectAll = (isSelected: boolean) => {
    setSelectedServers(
      isSelected ? (filteredServers?.map(s => s.name) || []) : []
    );
  };

  const handleDeleteSelected = () => {
    deleteMutation.mutate(selectedServers);
  };

  const handleExport = () => {
    const selectedServerObjects = servers?.filter(s => selectedServers.includes(s.name)) || [];
    const exportData = JSON.stringify(selectedServerObjects, null, 2);
    const blob = new Blob([exportData], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `vmcp-servers-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleImport = async () => {
    if (!importFile) {
      setImportError('Please select a file to import');
      return;
    }

    try {
      const text = await importFile.text();
      const importedServers = JSON.parse(text) as VMCPServer[];
      
      if (!Array.isArray(importedServers)) {
        setImportError('Invalid file format. Expected an array of VMCP servers.');
        return;
      }

      // Import each server
      for (const server of importedServers) {
        try {
          await vmcpApi.create(server);
        } catch (error: any) {
          console.error(`Failed to import VMCP server ${server.name}:`, error);
        }
      }

      queryClient.invalidateQueries({ queryKey: ['vmcp-servers'] });
      setIsImportModalOpen(false);
      setImportFile(null);
      setImportError('');
    } catch (error) {
      setImportError('Failed to parse JSON file. Please ensure it is valid JSON.');
    }
  };

  const getSortableRowValues = (server: VMCPServer): (string | number)[] => {
    return [
      server.name,
      server.description || '',
      server.state || '',
      server.port || 0,
      server.version || '',
    ];
  };

  // Get all unique tags from servers
  const allTags = useMemo(() => {
    if (!servers) return [];
    const tagSet = new Set<string>();
    servers.forEach(server => {
      server.tags?.forEach(tag => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [servers]);

  const filteredServers = useMemo(() => {
    let filtered = servers;

    // Apply search filtering
    if (searchTerm && filtered) {
      if (searchMode === 'semantic' && searchResults) {
        // Semantic search: filter by backend results
        filtered = filtered.filter((server) =>
          searchResults.some((result) =>
            (result.name === server.name) || (result.filename === server.name)
          )
        );
      } else if (searchMode === 'text') {
        // Text search: filter by matching text in name or description
        const lowerSearch = searchTerm.toLowerCase();
        filtered = filtered.filter((server) =>
          server.name.toLowerCase().includes(lowerSearch) ||
          server.description?.toLowerCase().includes(lowerSearch)
        );
      }
    }

    // Apply tag filtering
    if (filtered && selectedTags.length > 0) {
      filtered = filtered.filter(server =>
        selectedTags.every(selectedTag =>
          server.tags?.includes(selectedTag)
        )
      );
    }

    if (filtered && activeSortIndex !== null) {
      filtered = [...filtered].sort((a, b) => {
        const aValue = getSortableRowValues(a)[activeSortIndex];
        const bValue = getSortableRowValues(b)[activeSortIndex];
        
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          const comparison = aValue.localeCompare(bValue);
          return activeSortDirection === 'asc' ? comparison : -comparison;
        }
        
        if (typeof aValue === 'number' && typeof bValue === 'number') {
          return activeSortDirection === 'asc' ? aValue - bValue : bValue - aValue;
        }
        
        return 0;
      });
    }

    return filtered;
  }, [servers, searchResults, searchTerm, searchMode, selectedTags, activeSortIndex, activeSortDirection]);

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
        <Alert variant="danger" title="Error loading Virtual MCP servers">
          {(error as Error).message}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Title headingLevel="h1" size="2xl">
          Virtual MCP Servers
        </Title>
        <Text>Create and manage virtual MCP servers for tool subsets</Text>
      </PageSection>

      <PageSection>
        <Toolbar>
          <ToolbarContent>
            <ToolbarItem variant="search-filter" style={{ flexGrow: 1 }}>
              <SearchBox
                value={searchTerm}
                onChange={setSearchTerm}
                onClear={() => setSearchTerm('')}
                mode={searchMode}
                onModeChange={setSearchMode}
                placeholder="Search VMCP servers..."
                maxResults={maxResults}
                onMaxResultsChange={setMaxResults}
                similarityThreshold={similarityThreshold}
                onSimilarityThresholdChange={setSimilarityThreshold}
              />
            </ToolbarItem>
            <ToolbarItem>
              <TagFilter
                allTags={allTags}
                selectedTags={selectedTags}
                onTagsChange={setSelectedTags}
              />
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="secondary"
                icon={<ExportIcon />}
                onClick={handleExport}
                isDisabled={selectedServers.length === 0}
              >
                Export ({selectedServers.length})
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="secondary"
                icon={<ImportIcon />}
                onClick={() => setIsImportModalOpen(true)}
              >
                Import
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="danger"
                icon={<TrashIcon />}
                onClick={() => setIsDeleteModalOpen(true)}
                isDisabled={selectedServers.length === 0}
              >
                Delete ({selectedServers.length})
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="primary"
                icon={<PlusIcon />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                Create VMCP Server
              </Button>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>

        {!filteredServers || filteredServers.length === 0 ? (
          <EmptyState>
            <EmptyStateIcon icon={searchTerm ? SearchIcon : ServerIcon} />
            <Title headingLevel="h4" size="lg">
              {searchTerm ? 'No VMCP servers found' : 'No VMCP servers yet'}
            </Title>
            <EmptyStateBody>
              {searchTerm
                ? 'Try adjusting your search criteria'
                : 'Create your first VMCP server to get started'}
            </EmptyStateBody>
            {!searchTerm && (
              <Button
                variant="primary"
                icon={<PlusIcon />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                Create VMCP Server
              </Button>
            )}
          </EmptyState>
        ) : (
          <Table aria-label="VMCP Servers table" variant="compact">
            <Thead>
              <Tr>
                <Th
                  select={{
                    onSelect: (_event, isSelected) => handleSelectAll(isSelected),
                    isSelected: selectedServers.length === filteredServers.length && filteredServers.length > 0,
                  }}
                />
                <Th sort={getSortParams(0)}>Name</Th>
                <Th sort={getSortParams(1)}>Description</Th>
                <Th sort={getSortParams(2)}>State</Th>
                <Th>Tags</Th>
                <Th sort={getSortParams(3)}>Port</Th>
                <Th>Status</Th>
                <Th sort={getSortParams(4)}>Version</Th>
              </Tr>
            </Thead>
            <Tbody>
              {filteredServers.map((server, index) => (
                <Tr key={server.uuid}>
                  <Td
                    select={{
                      rowIndex: index,
                      onSelect: (_event, isSelected) => handleSelectServer(server.name, isSelected),
                      isSelected: selectedServers.includes(server.name),
                    }}
                  />
                  <Td
                    dataLabel="Name"
                    onClick={() => navigate(`/vmcp-servers/${server.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {server.name}
                  </Td>
                  <Td
                    dataLabel="Description"
                    onClick={() => navigate(`/vmcp-servers/${server.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {server.description || 'No description'}
                  </Td>
                  <Td
                    dataLabel="State"
                    onClick={() => navigate(`/vmcp-servers/${server.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {server.state || '-'}
                  </Td>
                  <Td
                    dataLabel="Tags"
                    onClick={() => navigate(`/vmcp-servers/${server.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {server.tags && server.tags.length > 0 ? (
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        {server.tags.map((tag) => (
                          <Label key={tag} color={getTagColor(tag)} isCompact>
                            {tag}
                          </Label>
                        ))}
                      </div>
                    ) : (
                      '-'
                    )}
                  </Td>
                  <Td
                    dataLabel="Port"
                    onClick={() => navigate(`/vmcp-servers/${server.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {server.port || '-'}
                  </Td>
                  <Td
                    dataLabel="Status"
                    onClick={() => navigate(`/vmcp-servers/${server.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {server.running ? (
                      <Label color="green" isCompact>Running</Label>
                    ) : (
                      <Label color="red" isCompact>Stopped</Label>
                    )}
                  </Td>
                  <Td
                    dataLabel="Version"
                    onClick={() => navigate(`/vmcp-servers/${server.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {server.version || '-'}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </PageSection>

      {/* Create VMCP Server Modal */}
      <Modal
        variant={ModalVariant.medium}
        title="Create New VMCP Server"
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setNewServer({
            name: '',
            version: '',
            description: '',
            state: 'approved',
            tags: [],
            port: undefined,
            skill_uuid: '',
          });
          setTagInput('');
          setSkillSearchTerm('');
          setCreateError('');
        }}
        actions={[
          <Button
            key="create"
            variant="primary"
            onClick={handleCreateServer}
            isLoading={createMutation.isPending}
          >
            Create
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsCreateModalOpen(false);
              setNewServer({
                name: '',
                version: '',
                description: '',
                state: 'approved',
                tags: [],
                port: undefined,
                skill_uuid: '',
              });
              setTagInput('');
              setSkillSearchTerm('');
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
          <FormGroup label="Name" isRequired fieldId="server-name">
            <TextInput
              isRequired
              type="text"
              id="server-name"
              value={newServer.name}
              onChange={(_, value) => setNewServer({ ...newServer, name: value })}
            />
          </FormGroup>
          <FormGroup label="Version" fieldId="server-version">
            <TextInput
              type="text"
              id="server-version"
              value={newServer.version}
              onChange={(_, value) => setNewServer({ ...newServer, version: value })}
              placeholder="e.g., 1.0.0"
            />
          </FormGroup>
          <FormGroup label="Description" isRequired fieldId="server-description">
            <TextArea
              isRequired
              id="server-description"
              value={newServer.description}
              onChange={(_, value) => setNewServer({ ...newServer, description: value })}
              rows={2}
            />
          </FormGroup>
          <FormGroup label="State" isRequired fieldId="server-state">
            <FormSelect
              value={newServer.state}
              onChange={(_, value) => setNewServer({ ...newServer, state: value as 'unknown' | 'any' | 'new' | 'checked' | 'approved' })}
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
              value={newServer.port?.toString() || ''}
              onChange={(_, value) => setNewServer({ ...newServer, port: value ? parseInt(value) : undefined })}
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
            {newServer.skill_uuid && (
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
            {newServer.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {newServer.tags.map((tag) => (
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
        </Form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete VMCP Servers"
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
          Are you sure you want to delete {selectedServers.length} VMCP server{selectedServers.length > 1 ? 's' : ''}?
          This action cannot be undone.
        </Text>
        <ul style={{ marginTop: '1rem' }}>
          {selectedServers.map(name => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      </Modal>

      {/* Import Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Import VMCP Servers"
        isOpen={isImportModalOpen}
        onClose={() => {
          setIsImportModalOpen(false);
          setImportFile(null);
          setImportError('');
        }}
        actions={[
          <Button
            key="import"
            variant="primary"
            onClick={handleImport}
          >
            Import
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsImportModalOpen(false);
              setImportFile(null);
              setImportError('');
            }}
          >
            Cancel
          </Button>,
        ]}
      >
        {importError && (
          <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>
            {importError}
          </Alert>
        )}
        <Text style={{ marginBottom: '1rem' }}>
          Select a JSON file containing an array of VMCP server objects to import.
        </Text>
        <FileUpload
          id="import-file"
          value={importFile || undefined}
          filename={importFile?.name}
          onFileInputChange={(_event: any, file: File) => setImportFile(file)}
          onClearClick={() => setImportFile(null)}
          hideDefaultPreview
          browseButtonText="Select JSON File"
          accept=".json"
        />
      </Modal>
    </>
  );
}