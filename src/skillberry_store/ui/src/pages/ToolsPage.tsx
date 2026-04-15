// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTagColor } from '../utils/tagColors';
import { TagFilter } from '../components/TagFilter';
import { SearchBox, SearchMode } from '../components/SearchBox';
import { exportTools, importTools, downloadJSON } from '../utils/exportImportHelpers';
import {
  PageSection,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Button,
  SearchInput,
  Text,
  Label,
  Spinner,
  EmptyState,
  EmptyStateIcon,
  EmptyStateBody,
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  FileUpload,
  Alert,
  FormSelect,
  FormSelectOption,
} from '@patternfly/react-core';
import { Table, Thead, Tr, Th, Tbody, Td, ThProps } from '@patternfly/react-table';
import { PlusIcon, CubeIcon, SearchIcon, TrashIcon, ExportIcon, ImportIcon } from '@patternfly/react-icons';
import { toolsApi } from '@/services/api';
import type { Tool } from '@/types';

type SortableColumn = 'name' | 'description' | 'state' | 'module_name' | 'version';

export function ToolsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('text');
  const [maxResults, setMaxResults] = useState(10);
  const [similarityThreshold, setSimilarityThreshold] = useState(1);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [toolName, setToolName] = useState('');
  const [moduleFile, setModuleFile] = useState<File | null>(null);
  const [updateIfExists, setUpdateIfExists] = useState(false);
  const [createError, setCreateError] = useState('');
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importError, setImportError] = useState('');
  const [activeSortIndex, setActiveSortIndex] = useState<number | null>(null);
  const [activeSortDirection, setActiveSortDirection] = useState<'asc' | 'desc'>('asc');

  // Fetch tools
  const { data: tools, isLoading, error } = useQuery({
    queryKey: ['tools'],
    queryFn: toolsApi.list,
  });

  // Semantic search tools (only when in semantic mode)
  const { data: searchResults } = useQuery({
    queryKey: ['tools', 'search', searchTerm, maxResults, similarityThreshold],
    queryFn: () => toolsApi.search(searchTerm, maxResults, similarityThreshold),
    enabled: searchTerm.length > 0 && searchMode === 'semantic',
  });

  // Create tool mutation
  const createMutation = useMutation({
    mutationFn: ({ file, toolName, update }: { file: File; toolName?: string; update: boolean }) =>
      toolsApi.create(file, toolName, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      setIsCreateModalOpen(false);
      setToolName('');
      setModuleFile(null);
      setUpdateIfExists(false);
      setCreateError('');
    },
    onError: (error: any) => {
      setCreateError(error.message || 'Failed to create tool');
    },
  });

  // Delete tools mutation
  const deleteMutation = useMutation({
    mutationFn: async (names: string[]) => {
      await Promise.all(names.map(name => toolsApi.delete(name)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      setSelectedTools([]);
      setIsDeleteModalOpen(false);
    },
  });

  const handleCreateTool = () => {
    if (!moduleFile) {
      setCreateError('Please upload a Python file');
      return;
    }
    if (!moduleFile.name.endsWith('.py')) {
      setCreateError('Only Python (.py) files are supported');
      return;
    }
    createMutation.mutate({
      file: moduleFile,
      toolName: toolName.trim() || undefined,
      update: updateIfExists
    });
  };

  const handleSelectTool = (toolName: string, isSelected: boolean) => {
    setSelectedTools(prev =>
      isSelected
        ? [...prev, toolName]
        : prev.filter(name => name !== toolName)
    );
  };

  const handleSelectAll = (isSelected: boolean) => {
    setSelectedTools(
      isSelected ? (filteredTools?.map(t => t.name) || []) : []
    );
  };

  const handleDeleteSelected = () => {
    deleteMutation.mutate(selectedTools);
  };

  const handleExport = async () => {
    const selectedToolObjects = tools?.filter(t => selectedTools.includes(t.name)) || [];
    
    // Use helper function to export tools with module content
    const toolsWithModules = await exportTools(selectedToolObjects);
    
    // Download as JSON file
    downloadJSON(toolsWithModules, `tools-export-${new Date().toISOString().split('T')[0]}.json`);
  };

  const handleImport = async () => {
    if (!importFile) {
      setImportError('Please select a file to import');
      return;
    }

    try {
      const text = await importFile.text();
      const importedTools = JSON.parse(text) as (Tool & { module_content?: string })[];
      
      if (!Array.isArray(importedTools)) {
        setImportError('Invalid file format. Expected an array of tools.');
        return;
      }

      // Use helper function to import tools
      await importTools(importedTools);

      queryClient.invalidateQueries({ queryKey: ['tools'] });
      setIsImportModalOpen(false);
      setImportFile(null);
      setImportError('');
    } catch (error) {
      setImportError('Failed to parse JSON file. Please ensure it is valid JSON.');
    }
  };

  const getSortableRowValues = (tool: Tool): (string | number)[] => {
    return [
      tool.name,
      tool.description || '',
      tool.state || '',
      tool.module_name || '',
      tool.version || '',
    ];
  };

  // Get all unique tags from tools
  const allTags = useMemo(() => {
    if (!tools) return [];
    const tagSet = new Set<string>();
    tools.forEach(tool => {
      tool.tags?.forEach(tag => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [tools]);

  const filteredTools = useMemo(() => {
    let filtered = tools;

    // Apply search filtering
    if (searchTerm && filtered) {
      if (searchMode === 'semantic' && searchResults) {
        // Semantic search: filter by backend results (handle both name and filename)
        filtered = filtered.filter((tool) =>
          searchResults.some((result) =>
            (result.name === tool.name) || (result.filename === tool.name)
          )
        );
      } else if (searchMode === 'text') {
        // Text search: filter by matching text in name or description
        const lowerSearch = searchTerm.toLowerCase();
        filtered = filtered.filter((tool) =>
          tool.name.toLowerCase().includes(lowerSearch) ||
          tool.description?.toLowerCase().includes(lowerSearch)
        );
      }
    }

    // Apply tag filtering
    if (filtered && selectedTags.length > 0) {
      filtered = filtered.filter(tool =>
        selectedTags.every(selectedTag =>
          tool.tags?.includes(selectedTag)
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
        
        return 0;
      });
    }

    return filtered;
  }, [tools, searchResults, searchTerm, searchMode, selectedTags, activeSortIndex, activeSortDirection]);

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
        <Alert variant="danger" title="Error loading tools">
          {(error as Error).message}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Title headingLevel="h1" size="2xl">
          Tools
        </Title>
        <Text>Manage executable tools with parameters and execution capabilities</Text>
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
                placeholder="Search tools..."
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
                isDisabled={selectedTools.length === 0}
              >
                Export ({selectedTools.length})
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
                isDisabled={selectedTools.length === 0}
              >
                Delete ({selectedTools.length})
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="primary"
                icon={<PlusIcon />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                Create Tool
              </Button>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>

        {!filteredTools || filteredTools.length === 0 ? (
          <EmptyState>
            <EmptyStateIcon icon={searchTerm ? SearchIcon : CubeIcon} />
            <Title headingLevel="h4" size="lg">
              {searchTerm ? 'No tools found' : 'No tools yet'}
            </Title>
            <EmptyStateBody>
              {searchTerm
                ? 'Try adjusting your search criteria'
                : 'Create your first tool to get started'}
            </EmptyStateBody>
            {!searchTerm && (
              <Button 
                variant="primary" 
                icon={<PlusIcon />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                Create Tool
              </Button>
            )}
          </EmptyState>
        ) : (
          <Table aria-label="Tools table" variant="compact">
            <Thead>
              <Tr>
                <Th
                  select={{
                    onSelect: (_event, isSelected) => handleSelectAll(isSelected),
                    isSelected: selectedTools.length === filteredTools.length && filteredTools.length > 0,
                  }}
                />
                <Th sort={getSortParams(0)}>Name</Th>
                <Th sort={getSortParams(1)}>Description</Th>
                <Th sort={getSortParams(2)}>State</Th>
                <Th>Tags</Th>
                <Th sort={getSortParams(3)}>Module Name</Th>
                <Th sort={getSortParams(4)}>Version</Th>
              </Tr>
            </Thead>
            <Tbody>
              {filteredTools.map((tool, index) => (
                <Tr key={tool.uuid}>
                  <Td
                    select={{
                      rowIndex: index,
                      onSelect: (_event, isSelected) => handleSelectTool(tool.name, isSelected),
                      isSelected: selectedTools.includes(tool.name),
                    }}
                  />
                  <Td
                    dataLabel="Name"
                    onClick={() => navigate(`/tools/${tool.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {tool.name}
                  </Td>
                  <Td
                    dataLabel="Description"
                    onClick={() => navigate(`/tools/${tool.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {tool.description || 'No description'}
                  </Td>
                  <Td
                    dataLabel="State"
                    onClick={() => navigate(`/tools/${tool.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {tool.state || '-'}
                  </Td>
                  <Td
                    dataLabel="Tags"
                    onClick={() => navigate(`/tools/${tool.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {tool.tags && tool.tags.length > 0 ? (
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        {tool.tags.map((tag) => (
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
                    dataLabel="Module Name"
                    onClick={() => navigate(`/tools/${tool.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {tool.module_name || '-'}
                  </Td>
                  <Td
                    dataLabel="Version"
                    onClick={() => navigate(`/tools/${tool.name}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {tool.version || '-'}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </PageSection>

      {/* Create Tool Modal */}
      <Modal
        variant={ModalVariant.medium}
        title="Create New Tool"
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setToolName('');
          setModuleFile(null);
          setUpdateIfExists(false);
          setCreateError('');
        }}
        actions={[
          <Button
            key="create"
            variant="primary"
            onClick={handleCreateTool}
            isLoading={createMutation.isPending}
          >
            Create
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsCreateModalOpen(false);
              setToolName('');
              setModuleFile(null);
              setUpdateIfExists(false);
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
        <Alert variant="info" title="How it works" isInline style={{ marginBottom: '1rem' }}>
          Upload a Python file with a function that has a properly formatted docstring.
          The tool will automatically extract the function name, description, and parameters from the docstring.
        </Alert>
        <Form>
          <FormGroup
            label="Python File"
            isRequired
            fieldId="tool-module"
          >
            <Text component="small" style={{ display: 'block', marginBottom: '0.5rem', color: '#6a6e73' }}>
              Upload a .py file containing a function with a docstring
            </Text>
            <FileUpload
              id="tool-module"
              value={moduleFile || undefined}
              filename={moduleFile?.name}
              onFileInputChange={(_event: any, file: File) => setModuleFile(file)}
              onClearClick={() => setModuleFile(null)}
              hideDefaultPreview
              browseButtonText="Upload Python File"
              accept=".py"
            />
          </FormGroup>
          <FormGroup
            label="Function Name"
            fieldId="tool-name"
          >
            <Text component="small" style={{ display: 'block', marginBottom: '0.5rem', color: '#6a6e73' }}>
              Optional: Specify which function to use if the file contains multiple functions. If not provided, the first function will be used.
            </Text>
            <TextInput
              type="text"
              id="tool-name"
              value={toolName}
              onChange={(_, value) => setToolName(value)}
              placeholder="e.g., my_function"
            />
          </FormGroup>
          <FormGroup fieldId="tool-update">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="checkbox"
                id="tool-update"
                checked={updateIfExists}
                onChange={(e) => setUpdateIfExists(e.target.checked)}
              />
              <label htmlFor="tool-update">
                Update if tool already exists
              </label>
            </div>
          </FormGroup>
        </Form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete Tools"
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
          Are you sure you want to delete {selectedTools.length} tool{selectedTools.length > 1 ? 's' : ''}?
          This action cannot be undone.
        </Text>
        <ul style={{ marginTop: '1rem' }}>
          {selectedTools.map(name => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      </Modal>

      {/* Import Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Import Tools"
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
          Select a JSON file containing an array of tool objects (with module_content) to import.
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