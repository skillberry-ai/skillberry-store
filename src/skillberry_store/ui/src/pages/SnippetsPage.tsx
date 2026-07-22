// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { getTagColor } from '../utils/tagColors';
import { TagFilter } from '../components/TagFilter';
import { NamespaceFilter } from '../components/NamespaceFilter';
import { SearchBox, SearchMode } from '../components/SearchBox';
import { exportSnippets, importSnippets, downloadJSON } from '../utils/exportImportHelpers';
import { PAGE_SIZE_OPTIONS, usePagination } from '../contexts/PaginationContext';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import {
  PageSection,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Pagination,
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
} from '@patternfly/react-core';
import { Table, Thead, Tr, Th, Tbody, Td, ThProps } from '@patternfly/react-table';
import { PlusIcon, FileCodeIcon, SearchIcon, TrashIcon, ExportIcon, ImportIcon } from '@patternfly/react-icons';
import { snippetsApi } from '@/services/api';
import type { Snippet } from '@/types';


export function SnippetsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('text');
  const [maxResults, setMaxResults] = useState(10);
  const [similarityThreshold, setSimilarityThreshold] = useState(1);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedNamespaces, setSelectedNamespaces] = useState<string[]>([]);
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
  const [deleteError, setDeleteError] = useState('');
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importError, setImportError] = useState('');
  const [activeSortIndex, setActiveSortIndex] = useState<number | null>(null);
  const [activeSortDirection, setActiveSortDirection] = useState<'asc' | 'desc'>('asc');
  const { pageSize, setPageSize } = usePagination();
  const [page, setPage] = useState<number>(1);

  // ── Derived query args ────────────────────────────────────────────
  const debouncedSearch = useDebouncedValue(searchTerm, 250);
  const isSemantic = searchMode === 'semantic' && debouncedSearch.length > 0;

  const combinedTags = useMemo(
    () => [
      ...selectedTags,
      ...selectedNamespaces.map(ns => `namespace:${ns}`),
    ],
    [selectedTags, selectedNamespaces]
  );

  const SNIPPET_SORT_FIELDS = ['name', 'description', 'state', 'content_type', 'version'] as const;
  const sortSpec = useMemo(() => {
    if (activeSortIndex === null) return undefined;
    const field = SNIPPET_SORT_FIELDS[activeSortIndex] ?? 'modified_at';
    return `${field}:${activeSortDirection}`;
  }, [activeSortIndex, activeSortDirection]);

  const offset = (page - 1) * pageSize;

  // ── Queries ────────────────────────────────────────────────────────
  // Server-paginated in text/uuid/empty modes; semantic mode goes to a
  // separate /search endpoint that returns projected results (no paging —
  // bounded by max_number_of_results).
  const pagedQuery = useQuery({
    queryKey: [
      'snippets',
      'paged',
      { offset, limit: pageSize, search: debouncedSearch, tags: combinedTags, sort: sortSpec, mode: searchMode },
    ],
    queryFn: () =>
      snippetsApi.listPaged({
        limit: pageSize,
        offset,
        search: searchMode === 'semantic' ? undefined : debouncedSearch || undefined,
        tags: combinedTags,
        sort: sortSpec,
      }),
    enabled: !isSemantic,
    // Keep the previous page/search result visible while a new query is in
    // flight so the toolbar (and the search input's focus) never unmounts.
    placeholderData: keepPreviousData,
  });

  const semanticQuery = useQuery({
    queryKey: ['snippets', 'semantic', debouncedSearch, maxResults, similarityThreshold],
    queryFn: () => snippetsApi.searchProjected(debouncedSearch, maxResults, similarityThreshold),
    enabled: isSemantic,
    placeholderData: keepPreviousData,
  });

  const facetsQuery = useQuery({
    queryKey: ['snippets', 'facets'],
    queryFn: snippetsApi.facets,
    staleTime: 60_000,
  });

  // ── Unified accessors ─────────────────────────────────────────────
  const displayedSnippets: Snippet[] = isSemantic
    ? semanticQuery.data ?? []
    : pagedQuery.data?.items ?? [];
  const totalFiltered = isSemantic
    ? displayedSnippets.length
    : pagedQuery.data?.total ?? 0;
  const isLoading = isSemantic ? semanticQuery.isLoading : pagedQuery.isLoading;
  const error = isSemantic ? semanticQuery.error : pagedQuery.error;

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
      setDeleteError('');
    },
    onError: (error: any) => {
      setDeleteError(error.message || 'Failed to delete snippet(s)');
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
    // Standard paginated-table UX: header checkbox toggles the current page.
    setSelectedSnippets(
      isSelected ? displayedSnippets.map(s => s.name) : []
    );
  };

  const handleDeleteSelected = () => {
    deleteMutation.mutate(selectedSnippets);
  };

  const handleExport = async () => {
    // Selection can span pages — fetch each selected snippet's full object
    // so `content` is present in the export.
    const fetched = await Promise.all(
      selectedSnippets.map(name =>
        snippetsApi.get(name).catch(() => null)
      )
    );
    const selectedSnippetObjects = fetched.filter(
      (s): s is Snippet => s !== null
    );

    const snippetsForExport = exportSnippets(selectedSnippetObjects);
    downloadJSON(snippetsForExport, `snippets-export-${new Date().toISOString().split('T')[0]}.json`);
  };

  const handleImport = async () => {
    if (!importFile) {
      setImportError('Please select a file to import');
      return;
    }

    try {
      const text = await importFile.text();
      const importedSnippets = JSON.parse(text) as Snippet[];

      if (!Array.isArray(importedSnippets)) {
        setImportError('Invalid file format. Expected an array of snippets.');
        return;
      }

      const result = await importSnippets(importedSnippets);
      queryClient.invalidateQueries({ queryKey: ['snippets'] });

      if (result.failures.length > 0) {
        const summary = result.failures
          .map(f => `• ${f.name}: ${f.error}`)
          .join('\n');
        setImportError(
          `Imported ${result.importedCount} of ${importedSnippets.length} snippet(s). Failures:\n${summary}`
        );
      } else {
        setIsImportModalOpen(false);
        setImportFile(null);
        setImportError('');
      }
    } catch (error) {
      setImportError('Failed to parse JSON file. Please ensure it is valid JSON.');
    }
  };

  // Picker widgets read the facets endpoint so they can enumerate every
  // tag / namespace without fetching every snippet.
  const allTags = facetsQuery.data?.tags ?? [];
  const allNamespaces = facetsQuery.data?.namespaces ?? [];

  // Snap back to page 1 whenever the filters that would change the total
  // count change — otherwise the pager can point past the end.
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, searchMode, combinedTags, sortSpec, pageSize]);

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
            <ToolbarItem variant="search-filter" style={{ flexGrow: 1 }}>
              <SearchBox
                value={searchTerm}
                onChange={setSearchTerm}
                onClear={() => setSearchTerm('')}
                mode={searchMode}
                onModeChange={setSearchMode}
                placeholder="Search snippets..."
                maxResults={maxResults}
                onMaxResultsChange={setMaxResults}
                similarityThreshold={similarityThreshold}
                onSimilarityThresholdChange={setSimilarityThreshold}
              />
            </ToolbarItem>
            <ToolbarItem>
              <NamespaceFilter
                allNamespaces={allNamespaces}
                selectedNamespaces={selectedNamespaces}
                onNamespacesChange={setSelectedNamespaces}
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
                isDisabled={selectedSnippets.length === 0}
              >
                Export ({selectedSnippets.length})
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

        {isLoading ? (
          <div className="loading-container">
            <Spinner size="xl" />
          </div>
        ) : totalFiltered === 0 ? (
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
          <>
          <Pagination
            itemCount={totalFiltered}
            perPage={pageSize}
            page={page}
            onSetPage={(_e, newPage) => setPage(newPage)}
            perPageOptions={PAGE_SIZE_OPTIONS.map(v => ({ title: String(v), value: v }))}
            onPerPageSelect={(_e, newPerPage, newPage) => { setPageSize(newPerPage); setPage(newPage); }}
            variant="top"
            widgetId="snippets-pagination-top"
          />
          <Table aria-label="Snippets table" variant="compact">
            <Thead>
              <Tr>
                <Th
                  select={{
                    onSelect: (_event, isSelected) => handleSelectAll(isSelected),
                    isSelected: selectedSnippets.length === totalFiltered && totalFiltered > 0,
                  }}
                />
                <Th sort={getSortParams(0)} width={20}>Name</Th>
                <Th sort={getSortParams(1)} width={35} modifier="truncate">Description</Th>
                <Th sort={getSortParams(2)} width={10}>State</Th>
                <Th width={15}>Tags</Th>
                <Th sort={getSortParams(3)} width={10}>Content Type</Th>
                <Th sort={getSortParams(4)} width={10}>Version</Th>
              </Tr>
            </Thead>
            <Tbody>
              {displayedSnippets.map((snippet, index) => (
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
                    onClick={() => navigate(`/snippets/${snippet.uuid}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.name}
                  </Td>
                  <Td
                    dataLabel="Description"
                    modifier="truncate"
                    onClick={() => navigate(`/snippets/${snippet.uuid}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.description || 'No description'}
                  </Td>
                  <Td
                    dataLabel="State"
                    onClick={() => navigate(`/snippets/${snippet.uuid}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.state || '-'}
                  </Td>
                  <Td
                    dataLabel="Tags"
                    onClick={() => navigate(`/snippets/${snippet.uuid}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.tags && snippet.tags.filter(tag => !tag.startsWith('namespace:')).length > 0 ? (
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        {snippet.tags
                          .filter(tag => !tag.startsWith('namespace:'))
                          .map((tag) => (
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
                    dataLabel="Content Type"
                    onClick={() => navigate(`/snippets/${snippet.uuid}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.content_type || '-'}
                  </Td>
                  <Td
                    dataLabel="Version"
                    onClick={() => navigate(`/snippets/${snippet.uuid}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    {snippet.version || '-'}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
          <Pagination
            itemCount={totalFiltered}
            perPage={pageSize}
            page={page}
            onSetPage={(_e, newPage) => setPage(newPage)}
            perPageOptions={PAGE_SIZE_OPTIONS.map(v => ({ title: String(v), value: v }))}
            onPerPageSelect={(_e, newPerPage, newPage) => { setPageSize(newPerPage); setPage(newPage); }}
            variant="bottom"
            widgetId="snippets-pagination-bottom"
          />
          </>
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
        onClose={() => { setIsDeleteModalOpen(false); setDeleteError(''); }}
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
            onClick={() => { setIsDeleteModalOpen(false); setDeleteError(''); }}
          >
            Cancel
          </Button>,
        ]}
      >
        {deleteError && (
          <Alert variant="danger" title="Delete failed" isInline style={{ marginBottom: '1rem' }}>
            {deleteError}
          </Alert>
        )}
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

      {/* Import Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Import Snippets"
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
            <span style={{ whiteSpace: 'pre-wrap' }}>{importError}</span>
          </Alert>
        )}
        <Text style={{ marginBottom: '1rem' }}>
          Select a JSON file containing an array of snippet objects to import.
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