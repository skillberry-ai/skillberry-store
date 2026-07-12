// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * CatalogImportView — generic renderer for the "catalog-import" plugin UI archetype.
 *
 * Renders a search → lazy-detail → select → import flow entirely from a
 * CatalogImportConfig (chrome + endpoints) and the fixed CatalogItem contract
 * returned by the plugin's backend. Contains NO plugin-specific strings, endpoints,
 * or field names — any plugin whose get_ui_config() ships a catalog-import custom_ui
 * gets this UI for free.
 */

import { useState, useEffect, useRef } from 'react';
import {
  Modal, ModalVariant, Button, TextInput, Alert, Spinner,
  Toolbar, ToolbarContent, ToolbarItem, Popover, Label,
  EmptyState, EmptyStateBody, EmptyStateIcon, Flex, FlexItem,
} from '@patternfly/react-core';
import { Table, Thead, Tr, Th, Tbody, Td } from '@patternfly/react-table';
import { SearchIcon, ImportIcon } from '@patternfly/react-icons';
import type { Plugin, CatalogImportConfig, CatalogItem, CatalogItemDetail } from '@/types';

interface DescEntry { status: 'loading' | 'done' | 'error'; description: string; }
interface DescriptionCache { [id: string]: DescEntry; }

interface ImportedRow { id: string; title: string; summary?: string; }
interface FailedRow { id: string; error: string; }

interface CatalogImportViewProps {
  config: CatalogImportConfig;
  plugin: Plugin;
  isOpen: boolean;
  onClose: () => void;
}

export function CatalogImportView({ config, plugin, isOpen, onClose }: CatalogImportViewProps) {
  const minChars = config.min_query_chars ?? 2;
  const cols = config.columns ?? {};

  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [results, setResults] = useState<CatalogItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [descriptions, setDescriptions] = useState<DescriptionCache>({});
  const fetchingRef = useRef<Set<string>>(new Set());

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    success: boolean; message: string; imported: ImportedRow[]; failed: FailedRow[];
  } | null>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery(''); setSubmittedQuery(''); setResults([]); setSearchError(null);
      setSelected(new Set()); setImportResult(null); setDescriptions({});
      fetchingRef.current.clear();
    }
  }, [isOpen]);

  const handleSearch = async () => {
    const q = query.trim();
    if (q.length < minChars) return;
    setSearching(true); setSearchError(null); setResults([]); setSelected(new Set());
    setImportResult(null); setDescriptions({}); fetchingRef.current.clear();
    setSubmittedQuery(q);
    try {
      const resp = await fetch(config.search_endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, limit: 50 }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail ?? 'Search failed');
      }
      const body = await resp.json();
      if (!body.success) throw new Error(body.message ?? 'Search failed');
      setResults(body.data?.items ?? []);
    } catch (e: any) {
      setSearchError(e.message);
    } finally {
      setSearching(false);
    }
  };

  const fetchDescription = async (id: string) => {
    if (!config.detail_endpoint || fetchingRef.current.has(id) || descriptions[id]) return;
    fetchingRef.current.add(id);
    setDescriptions((prev) => ({ ...prev, [id]: { status: 'loading', description: '' } }));
    try {
      const url = config.detail_endpoint.replace('{id}', encodeURIComponent(id));
      const resp = await fetch(url);
      const body = await resp.json();
      setDescriptions((prev) => ({ ...prev, [id]: { status: 'done', description: body.description ?? '' } }));
    } catch {
      setDescriptions((prev) => ({ ...prev, [id]: { status: 'error', description: '' } }));
    }
  };

  const toggleRow = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };
  const toggleAll = () => {
    setSelected(selected.size === results.length ? new Set() : new Set(results.map((r) => r.id)));
  };

  const handleImport = async () => {
    if (selected.size === 0) return;
    setImporting(true); setImportResult(null);
    try {
      const resp = await fetch(config.import_endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_ids: Array.from(selected), ...(config.import_extra_params ?? {}) }),
      });
      const body = await resp.json();
      const data = body.data ?? body;
      setImportResult({
        success: body.success ?? false,
        message: body.message ?? '',
        imported: data.imported ?? [],
        failed: data.failed ?? [],
      });
      if (body.success) setSelected(new Set());
    } catch (e: any) {
      setImportResult({ success: false, message: e.message, imported: [], failed: [] });
    } finally {
      setImporting(false);
    }
  };

  const allSelected = results.length > 0 && selected.size === results.length;
  const importLabel = config.import_button_label ?? 'Import selected';

  return (
    <Modal
      variant={ModalVariant.large}
      title={config.title}
      isOpen={isOpen}
      onClose={onClose}
      description={config.description}
      actions={[
        <Button key="import" variant="primary"
          icon={importing ? <Spinner size="sm" /> : <ImportIcon />}
          isDisabled={selected.size === 0 || importing}
          onClick={handleImport}
        >
          {importing ? 'Importing…' : `${importLabel} (${selected.size})`}
        </Button>,
        <Button key="close" variant="link" onClick={onClose}>Close</Button>,
      ]}
    >
      {!plugin.enabled && (
        <Alert variant="warning" title="Plugin not configured" isInline style={{ marginBottom: '1rem' }}>
          {plugin.status}
          {config.setup_instructions && (
            <div style={{ marginTop: '0.5rem' }}>
              <strong>{config.setup_instructions.title}</strong>
              <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem' }}>
                {config.setup_instructions.steps.map((s, i) => (
                  <li key={i}><strong>{s.label}</strong> — {s.description}</li>
                ))}
              </ul>
              {config.setup_instructions.docs_url && (
                <a href={config.setup_instructions.docs_url} target="_blank" rel="noopener noreferrer">Docs</a>
              )}
            </div>
          )}
        </Alert>
      )}

      <Toolbar style={{ paddingLeft: 0 }}>
        <ToolbarContent>
          <ToolbarItem style={{ flex: 1 }}>
            <TextInput
              value={query}
              onChange={(_e, v) => setQuery(v)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder={config.search_placeholder}
              aria-label="Search query"
            />
          </ToolbarItem>
          <ToolbarItem>
            <Button variant="primary"
              icon={searching ? <Spinner size="sm" /> : <SearchIcon />}
              isDisabled={query.trim().length < minChars || searching || !plugin.enabled}
              onClick={handleSearch}
            >
              {searching ? 'Searching…' : 'Search'}
            </Button>
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>

      {searchError && (
        <Alert variant="danger" title="Search failed" isInline style={{ margin: '0.5rem 0' }}>{searchError}</Alert>
      )}

      {importResult && (
        <Alert
          variant={importResult.success ? 'success' : importResult.imported.length > 0 ? 'warning' : 'danger'}
          title={importResult.message}
          isInline
          style={{ margin: '0.5rem 0' }}
        >
          {importResult.imported.length > 0 && (
            <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem' }}>
              {importResult.imported.map((s) => (
                <li key={s.id}><strong>{s.title}</strong>{s.summary ? ` — ${s.summary}` : ''}</li>
              ))}
            </ul>
          )}
          {importResult.failed.length > 0 && (
            <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem', color: '#a30000' }}>
              {importResult.failed.map((f) => (<li key={f.id}><strong>{f.id}</strong>: {f.error}</li>))}
            </ul>
          )}
        </Alert>
      )}

      {results.length === 0 && !searching && submittedQuery && !searchError && (
        <EmptyState style={{ marginTop: '2rem' }}>
          <EmptyStateIcon icon={SearchIcon} />
          <EmptyStateBody>No results found for "{submittedQuery}"</EmptyStateBody>
        </EmptyState>
      )}

      {results.length > 0 && (
        <>
          <div style={{ fontSize: '0.8rem', color: '#6a6e73', margin: '0.25rem 0 0.5rem' }}>
            {results.length} result{results.length !== 1 ? 's' : ''} — hover a row for details
          </div>
          <div style={{ overflowX: 'auto' }}>
            <Table aria-label="catalog search results" variant="compact">
              <Thead>
                <Tr>
                  <Th select={{ onSelect: toggleAll, isSelected: allSelected, isHeaderSelectDisabled: results.length === 0 }} />
                  <Th width={30}>{cols.primary ?? 'Name'}</Th>
                  <Th width={20}>{cols.secondary ?? 'Source'}</Th>
                  <Th>{cols.description ?? 'Description'}</Th>
                </Tr>
              </Thead>
              <Tbody>
                {results.map((item) => (
                  <CatalogRow
                    key={item.id}
                    item={item}
                    desc={descriptions[item.id]}
                    lazy={!!config.detail_endpoint}
                    isSelected={selected.has(item.id)}
                    onToggle={() => toggleRow(item.id)}
                    onVisible={() => fetchDescription(item.id)}
                  />
                ))}
              </Tbody>
            </Table>
          </div>
        </>
      )}
    </Modal>
  );
}

interface CatalogRowProps {
  item: CatalogItem;
  desc: DescEntry | undefined;
  lazy: boolean;
  isSelected: boolean;
  onToggle: () => void;
  onVisible: () => void;
}

function CatalogRow({ item, desc, lazy, isSelected, onToggle, onVisible }: CatalogRowProps) {
  const rowRef = useRef<HTMLTableRowElement>(null);
  const hasTriggered = useRef(false);

  useEffect(() => {
    if (!lazy || hasTriggered.current || desc) return;
    const el = rowRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !hasTriggered.current) {
        hasTriggered.current = true;
        onVisible();
        obs.disconnect();
      }
    }, { threshold: 0.1 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [desc, lazy, onVisible]);

  const details: CatalogItemDetail[] = item.details ?? [];
  const popoverBody = (
    <div style={{ fontSize: '0.85rem', lineHeight: 1.5 }}>
      {details.map((d, i) => (
        <div key={i}>
          <strong>{d.label}:</strong>{' '}
          {d.href ? (<a href={d.href} target="_blank" rel="noopener noreferrer">{d.value}</a>) : d.value}
        </div>
      ))}
      {(item.badges ?? []).map((b, i) => (
        <Label key={i} color={(b.color as any) ?? 'grey'} style={{ marginTop: '0.4rem' }}>{b.label}</Label>
      ))}
    </div>
  );

  // description precedence: lazy-loaded value, else the item's own description.
  const descText = desc?.description ?? item.description ?? '';
  const descLoading = lazy && (!desc || desc.status === 'loading');

  return (
    <Popover
      aria-label={`Details for ${item.title}`}
      headerContent={<strong>{item.title}</strong>}
      bodyContent={popoverBody}
      triggerAction="hover"
      position="right"
    >
      <Tr
        ref={rowRef}
        isRowSelected={isSelected}
        style={{ cursor: 'pointer', backgroundColor: isSelected ? 'var(--pf-v5-c-table--tr--m-selected--BackgroundColor, #e7f1fa)' : undefined }}
        onClick={onToggle}
      >
        <Td
          select={{ rowIndex: 0, onSelect: (e) => { e.stopPropagation(); onToggle(); }, isSelected }}
          onClick={(e) => e.stopPropagation()}
        />
        <Td dataLabel="primary">
          <Flex direction={{ default: 'column' }} spaceItems={{ default: 'spaceItemsNone' }}>
            <FlexItem><strong>{item.title}</strong></FlexItem>
            {item.subtitle && (
              <FlexItem><span style={{ fontSize: '0.75rem', color: '#6a6e73' }}>{item.subtitle}</span></FlexItem>
            )}
          </Flex>
        </Td>
        <Td dataLabel="secondary"><span style={{ fontSize: '0.85rem' }}>{item.source ?? ''}</span></Td>
        <Td dataLabel="description">
          {descLoading ? (
            <Spinner size="sm" />
          ) : !descText ? (
            <span style={{ color: '#6a6e73', fontStyle: 'italic', fontSize: '0.85rem' }}>—</span>
          ) : (
            <span style={{ fontSize: '0.85rem' }}>{descText}</span>
          )}
        </Td>
      </Tr>
    </Popover>
  );
}

// Made with Bob
