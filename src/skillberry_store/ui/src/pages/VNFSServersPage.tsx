// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTagColor } from '../utils/tagColors';
import { TagFilter } from '../components/TagFilter';
import { SearchBox, SearchMode } from '../components/SearchBox';
import { exportVNFSServers, importVNFSServers, downloadJSON } from '../utils/exportImportHelpers';
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
  Radio,
} from '@patternfly/react-core';
import { Table, Thead, Tr, Th, Tbody, Td, ThProps } from '@patternfly/react-table';
import { PlusIcon, ServerIcon, SearchIcon, TrashIcon, ExportIcon, ImportIcon } from '@patternfly/react-icons';
import { vnfsApi, skillsApi } from '@/services/api';
import type { VNFSServer } from '@/types';

export function VNFSServersPage() {
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
    protocol: 'webdav',
  });
  const [tagInput, setTagInput] = useState('');
  const [createError, setCreateError] = useState('');
  const [selectedServers, setSelectedServers] = useState<string[]>([]);

  const [isSkillSelectOpen, setIsSkillSelectOpen] = useState(false);
  const [skillSearchTerm, setSkillSearchTerm] = useState('');
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importError, setImportError] = useState('');
  const [activeSortIndex, setActiveSortIndex] = useState<number | null>(null);
  const [activeSortDirection, setActiveSortDirection] = useState<'asc' | 'desc'>('asc');

  const { data: servers, isLoading, error } = useQuery({
    queryKey: ['vnfs-servers'],
    queryFn: vnfsApi.list,
  });

  const { data: allSkills } = useQuery({
    queryKey: ['skills'],
    queryFn: skillsApi.list,
  });

  const { data: searchResults } = useQuery({
    queryKey: ['vnfs-servers', 'search', searchTerm, maxResults, similarityThreshold],
    queryFn: () => vnfsApi.search(searchTerm, maxResults, similarityThreshold),
    enabled: searchTerm.length > 0 && searchMode === 'semantic',
  });

  const createMutation = useMutation({
    mutationFn: (server: Omit<VNFSServer, 'uuid' | 'running' | 'export_path'>) =>
      vnfsApi.create(server),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vnfs-servers'] });
      setIsCreateModalOpen(false);
      setNewServer({ name: '', version: '', description: '', state: 'approved', tags: [], port: undefined, skill_uuid: '', protocol: 'webdav' });
      setTagInput('');
      setCreateError('');
    },
    onError: (error: any) => {
      setCreateError(error.message || 'Failed to create vNFS server');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (names: string[]) => {
      await Promise.all(names.map(name => vnfsApi.delete(name)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vnfs-servers'] });
      setSelectedServers([]);
      setIsDeleteModalOpen(false);
    },
  });

  const handleCreateServer = () => {
    if (!newServer.name || !newServer.description) {
      setCreateError('Please fill in all required fields');
      return;
    }
    createMutation.mutate(newServer);
  };

  const filteredSkills = useMemo(() => {
    if (!allSkills) return [];
    if (!skillSearchTerm) return allSkills;
    const lower = skillSearchTerm.toLowerCase();
    return allSkills.filter(s =>
      s.name.toLowerCase().includes(lower) || s.description?.toLowerCase().includes(lower)
    );
  }, [allSkills, skillSearchTerm]);

  const handleSelectSkill = (_event: any, value: string | number | undefined) => {
    if (typeof value === 'string') {
      const selected = allSkills?.find(s => s.name === value);
      if (selected) {
        setNewServer({ ...newServer, skill_uuid: selected.uuid, name: selected.name, description: selected.description || '' });
        setSkillSearchTerm(selected.name);
        setIsSkillSelectOpen(false);
      }
    }
  };

  const handleClearSkill = () => {
    setNewServer({ ...newServer, skill_uuid: '' });
    setSkillSearchTerm('');
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !newServer.tags.includes(tagInput.trim())) {
      setNewServer({ ...newServer, tags: [...newServer.tags, tagInput.trim()] });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setNewServer({ ...newServer, tags: newServer.tags.filter(t => t !== tagToRemove) });
  };

  const handleSelectServer = (serverName: string, isSelected: boolean) => {
    setSelectedServers(prev => isSelected ? [...prev, serverName] : prev.filter(n => n !== serverName));
  };

  const handleSelectAll = (isSelected: boolean) => {
    setSelectedServers(isSelected ? (filteredServers?.map(s => s.name) || []) : []);
  };

  const handleDeleteSelected = () => {
    deleteMutation.mutate(selectedServers);
  };

  const handleExport = () => {
    const selected = servers?.filter(s => selectedServers.includes(s.name)) || [];
    downloadJSON(exportVNFSServers(selected), `vnfs-servers-export-${new Date().toISOString().split('T')[0]}.json`);
  };

  const handleImport = async () => {
    if (!importFile) { setImportError('Please select a file to import'); return; }
    try {
      const text = await importFile.text();
      const imported = JSON.parse(text) as VNFSServer[];
      if (!Array.isArray(imported)) { setImportError('Invalid file format. Expected an array of vNFS servers.'); return; }
      await importVNFSServers(imported);
      queryClient.invalidateQueries({ queryKey: ['vnfs-servers'] });
      setIsImportModalOpen(false);
      setImportFile(null);
      setImportError('');
    } catch {
      setImportError('Failed to parse JSON file. Please ensure it is valid JSON.');
    }
  };

  const getSortableRowValues = (server: VNFSServer): (string | number)[] => [
    server.name,
    server.description || '',
    server.state || '',
    server.port || 0,
    server.version || '',
  ];

  const allTags = useMemo(() => {
    if (!servers) return [];
    const tagSet = new Set<string>();
    servers.forEach(s => s.tags?.forEach(t => tagSet.add(t)));
    return Array.from(tagSet).sort();
  }, [servers]);

  const filteredServers = useMemo(() => {
    let filtered = servers;
    if (searchTerm && filtered) {
      if (searchMode === 'semantic' && searchResults) {
        filtered = filtered.filter(s =>
          searchResults.some(r => r.name === s.name || r.filename === s.name)
        );
      } else if (searchMode === 'text') {
        const lower = searchTerm.toLowerCase();
        filtered = filtered.filter(s =>
          s.name.toLowerCase().includes(lower) || s.description?.toLowerCase().includes(lower)
        );
      }
    }
    if (filtered && selectedTags.length > 0) {
      filtered = filtered.filter(s => selectedTags.every(t => s.tags?.includes(t)));
    }
    if (filtered && activeSortIndex !== null) {
      filtered = [...filtered].sort((a, b) => {
        const aVal = getSortableRowValues(a)[activeSortIndex];
        const bVal = getSortableRowValues(b)[activeSortIndex];
        if (typeof aVal === 'string' && typeof bVal === 'string') {
          const cmp = aVal.localeCompare(bVal);
          return activeSortDirection === 'asc' ? cmp : -cmp;
        }
        if (typeof aVal === 'number' && typeof bVal === 'number') {
          return activeSortDirection === 'asc' ? aVal - bVal : bVal - aVal;
        }
        return 0;
      });
    }
    return filtered;
  }, [servers, searchResults, searchTerm, searchMode, selectedTags, activeSortIndex, activeSortDirection]);

  const getSortParams = (columnIndex: number): ThProps['sort'] => ({
    sortBy: { index: activeSortIndex ?? 0, direction: activeSortDirection },
    onSort: (_event, index, direction) => { setActiveSortIndex(index); setActiveSortDirection(direction); },
    columnIndex,
  });

  const resetCreateModal = () => {
    setIsCreateModalOpen(false);
    setNewServer({ name: '', version: '', description: '', state: 'approved', tags: [], port: undefined, skill_uuid: '', protocol: 'webdav' });
    setTagInput('');
    setSkillSearchTerm('');
    setCreateError('');
  };

  if (isLoading) {
    return <PageSection><div className="loading-container"><Spinner size="xl" /></div></PageSection>;
  }

  if (error) {
    return <PageSection><Alert variant="danger" title="Error loading Virtual NFS servers">{(error as Error).message}</Alert></PageSection>;
  }

  return (
    <>
      <PageSection variant="light">
        <Title headingLevel="h1" size="2xl">Virtual NFS Servers</Title>
        <Text>Create and manage virtual NFS servers to expose skills as mountable filesystems</Text>
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
                placeholder="Search vNFS servers..."
                maxResults={maxResults}
                onMaxResultsChange={setMaxResults}
                similarityThreshold={similarityThreshold}
                onSimilarityThresholdChange={setSimilarityThreshold}
              />
            </ToolbarItem>
            <ToolbarItem>
              <TagFilter allTags={allTags} selectedTags={selectedTags} onTagsChange={setSelectedTags} />
            </ToolbarItem>
            <ToolbarItem>
              <Button variant="secondary" icon={<ExportIcon />} onClick={handleExport} isDisabled={selectedServers.length === 0}>
                Export ({selectedServers.length})
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button variant="secondary" icon={<ImportIcon />} onClick={() => setIsImportModalOpen(true)}>
                Import
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button variant="danger" icon={<TrashIcon />} onClick={() => setIsDeleteModalOpen(true)} isDisabled={selectedServers.length === 0}>
                Delete ({selectedServers.length})
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button variant="primary" icon={<PlusIcon />} onClick={() => setIsCreateModalOpen(true)}>
                Create vNFS Server
              </Button>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>

        {!filteredServers || filteredServers.length === 0 ? (
          <EmptyState>
            <EmptyStateIcon icon={searchTerm ? SearchIcon : ServerIcon} />
            <Title headingLevel="h4" size="lg">
              {searchTerm ? 'No vNFS servers found' : 'No vNFS servers yet'}
            </Title>
            <EmptyStateBody>
              {searchTerm ? 'Try adjusting your search criteria' : 'Create your first vNFS server to get started'}
            </EmptyStateBody>
            {!searchTerm && (
              <Button variant="primary" icon={<PlusIcon />} onClick={() => setIsCreateModalOpen(true)}>
                Create vNFS Server
              </Button>
            )}
          </EmptyState>
        ) : (
          <Table aria-label="vNFS Servers table" variant="compact">
            <Thead>
              <Tr>
                <Th select={{ onSelect: (_e, isSelected) => handleSelectAll(isSelected), isSelected: selectedServers.length === filteredServers.length && filteredServers.length > 0 }} />
                <Th sort={getSortParams(0)}>Name</Th>
                <Th sort={getSortParams(1)}>Description</Th>
                <Th sort={getSortParams(2)}>State</Th>
                <Th>Tags</Th>
                <Th sort={getSortParams(3)}>Port</Th>
                <Th>Protocol</Th>
                <Th>Status</Th>
                <Th sort={getSortParams(4)}>Version</Th>
              </Tr>
            </Thead>
            <Tbody>
              {filteredServers.map((server, index) => (
                <Tr key={server.uuid}>
                  <Td select={{ rowIndex: index, onSelect: (_e, isSelected) => handleSelectServer(server.name, isSelected), isSelected: selectedServers.includes(server.name) }} />
                  <Td dataLabel="Name" onClick={() => navigate(`/vnfs-servers/${server.name}`)} style={{ cursor: 'pointer' }}>{server.name}</Td>
                  <Td dataLabel="Description" onClick={() => navigate(`/vnfs-servers/${server.name}`)} style={{ cursor: 'pointer' }}>{server.description || 'No description'}</Td>
                  <Td dataLabel="State" onClick={() => navigate(`/vnfs-servers/${server.name}`)} style={{ cursor: 'pointer' }}>{server.state || '-'}</Td>
                  <Td dataLabel="Tags" onClick={() => navigate(`/vnfs-servers/${server.name}`)} style={{ cursor: 'pointer' }}>
                    {server.tags && server.tags.length > 0 ? (
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        {server.tags.map(tag => <Label key={tag} color={getTagColor(tag)} isCompact>{tag}</Label>)}
                      </div>
                    ) : '-'}
                  </Td>
                  <Td dataLabel="Port" onClick={() => navigate(`/vnfs-servers/${server.name}`)} style={{ cursor: 'pointer' }}>{server.port || '-'}</Td>
                  <Td dataLabel="Protocol" onClick={() => navigate(`/vnfs-servers/${server.name}`)} style={{ cursor: 'pointer' }}>
                    <Label color={server.protocol === 'nfs' ? 'blue' : 'cyan'} isCompact>{server.protocol || 'webdav'}</Label>
                  </Td>
                  <Td dataLabel="Status" onClick={() => navigate(`/vnfs-servers/${server.name}`)} style={{ cursor: 'pointer' }}>
                    {server.running ? <Label color="green" isCompact>Running</Label> : <Label color="red" isCompact>Stopped</Label>}
                  </Td>
                  <Td dataLabel="Version" onClick={() => navigate(`/vnfs-servers/${server.name}`)} style={{ cursor: 'pointer' }}>{server.version || '-'}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </PageSection>

      {/* Create vNFS Server Modal */}
      <Modal
        variant={ModalVariant.medium}
        title="Create New vNFS Server"
        isOpen={isCreateModalOpen}
        onClose={resetCreateModal}
        actions={[
          <Button key="create" variant="primary" onClick={handleCreateServer} isLoading={createMutation.isPending}>Create</Button>,
          <Button key="cancel" variant="link" onClick={resetCreateModal}>Cancel</Button>,
        ]}
      >
        {createError && <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>{createError}</Alert>}
        <Form>
          <FormGroup label="Skill" fieldId="server-skill">
            <Text component="small" style={{ display: 'block', marginBottom: '0.5rem', color: '#6a6e73' }}>
              Search and select a skill to expose via this vNFS server
            </Text>
            <Select
              id="server-skill-select"
              isOpen={isSkillSelectOpen}
              selected={null}
              onSelect={handleSelectSkill}
              onOpenChange={(isOpen) => setIsSkillSelectOpen(isOpen)}
              toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                <MenuToggle ref={toggleRef} onClick={() => setIsSkillSelectOpen(!isSkillSelectOpen)} isExpanded={isSkillSelectOpen} style={{ width: '100%' }}>
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
                  <SelectOption isDisabled>{skillSearchTerm ? 'No skills found' : 'Start typing to search...'}</SelectOption>
                ) : (
                  filteredSkills.map(skill => (
                    <SelectOption key={skill.uuid} value={skill.name}>
                      {skill.name} {skill.description && `- ${skill.description}`}
                    </SelectOption>
                  ))
                )}
              </SelectList>
            </Select>
            {newServer.skill_uuid && (
              <div style={{ marginTop: '0.5rem' }}>
                <Button variant="plain" onClick={handleClearSkill} style={{ padding: '0.25rem 0.5rem', backgroundColor: '#e7f1fa', border: '1px solid #bee1f4', borderRadius: '3px' }}>
                  {skillSearchTerm} ✕
                </Button>
              </div>
            )}
          </FormGroup>
          <FormGroup label="Protocol" isRequired fieldId="server-protocol">
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              <Radio
                id="protocol-webdav"
                name="protocol"
                label="WebDAV"
                value="webdav"
                isChecked={newServer.protocol === 'webdav'}
                onChange={() => setNewServer({ ...newServer, protocol: 'webdav' })}
              />
              <Radio
                id="protocol-nfs"
                name="protocol"
                label="NFS"
                value="nfs"
                isChecked={newServer.protocol === 'nfs'}
                onChange={() => setNewServer({ ...newServer, protocol: 'nfs' })}
              />
            </div>
          </FormGroup>
          <FormGroup label="Name" isRequired fieldId="server-name">
            <TextInput isRequired type="text" id="server-name" value={newServer.name} onChange={(_, v) => setNewServer({ ...newServer, name: v })} />
          </FormGroup>
          <FormGroup label="Description" isRequired fieldId="server-description">
            <TextArea isRequired id="server-description" value={newServer.description} onChange={(_, v) => setNewServer({ ...newServer, description: v })} rows={2} />
          </FormGroup>
          <FormGroup label="Version" fieldId="server-version">
            <TextInput type="text" id="server-version" value={newServer.version} onChange={(_, v) => setNewServer({ ...newServer, version: v })} placeholder="e.g., 1.0.0" />
          </FormGroup>
          <FormGroup label="State" isRequired fieldId="server-state">
            <FormSelect value={newServer.state} onChange={(_, v) => setNewServer({ ...newServer, state: v as typeof newServer.state })} id="server-state">
              <FormSelectOption value="unknown" label="Unknown" />
              <FormSelectOption value="any" label="Any" />
              <FormSelectOption value="new" label="New" />
              <FormSelectOption value="checked" label="Checked" />
              <FormSelectOption value="approved" label="Approved" />
            </FormSelect>
          </FormGroup>
          <FormGroup label="Port" fieldId="server-port">
            <TextInput type="number" id="server-port" value={newServer.port?.toString() || ''} onChange={(_, v) => setNewServer({ ...newServer, port: v ? parseInt(v) : undefined })} placeholder="Leave empty for auto-assignment" />
          </FormGroup>
          <FormGroup label="Tags" fieldId="server-tags">
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <TextInput type="text" id="server-tags" value={tagInput} onChange={(_, v) => setTagInput(v)} placeholder="Add a tag" onKeyPress={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddTag(); } }} />
              <Button variant="secondary" onClick={handleAddTag}>Add</Button>
            </div>
            {newServer.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {newServer.tags.map(tag => (
                  <Button key={tag} variant="plain" onClick={() => handleRemoveTag(tag)} style={{ padding: '0.25rem 0.5rem', backgroundColor: '#f0f0f0', border: '1px solid #d2d2d2', borderRadius: '3px' }}>
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
        title="Delete vNFS Servers"
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        actions={[
          <Button key="delete" variant="danger" onClick={handleDeleteSelected} isLoading={deleteMutation.isPending}>Delete</Button>,
          <Button key="cancel" variant="link" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>,
        ]}
      >
        <Text>
          Are you sure you want to delete {selectedServers.length} vNFS server{selectedServers.length > 1 ? 's' : ''}? This action cannot be undone.
        </Text>
        <ul style={{ marginTop: '1rem' }}>
          {selectedServers.map(name => <li key={name}>{name}</li>)}
        </ul>
      </Modal>

      {/* Import Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Import vNFS Servers"
        isOpen={isImportModalOpen}
        onClose={() => { setIsImportModalOpen(false); setImportFile(null); setImportError(''); }}
        actions={[
          <Button key="import" variant="primary" onClick={handleImport}>Import</Button>,
          <Button key="cancel" variant="link" onClick={() => { setIsImportModalOpen(false); setImportFile(null); setImportError(''); }}>Cancel</Button>,
        ]}
      >
        {importError && <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>{importError}</Alert>}
        <Text style={{ marginBottom: '1rem' }}>
          Select a JSON file containing an array of vNFS server objects to import.
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
