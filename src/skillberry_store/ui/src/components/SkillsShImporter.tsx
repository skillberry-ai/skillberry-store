// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * SkillsShImporter — dedicated UI for the skillssh-importer plugin.
 *
 * Flow:
 *  1. User types a query → hits Search
 *  2. Results appear in a selectable table (id, name, source, description)
 *  3. Description is fetched lazily per row (one GET per skill)
 *  4. Hovering a row shows full metadata (installs, url, sourceType) in a Popover
 *  5. User ticks rows and hits "Import selected" → POST /import
 */

import { useState, useEffect, useRef } from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  TextInput,
  Alert,
  Spinner,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Popover,
  Label,
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  Flex,
  FlexItem,
} from '@patternfly/react-core';
import { Table, Thead, Tr, Th, Tbody, Td } from '@patternfly/react-table';
import { SearchIcon, ImportIcon } from '@patternfly/react-icons';
import type { Plugin } from '@/types';

// ── Types ────────────────────────────────────────────────────────────────────

interface SkillResult {
  id: string;
  slug: string;
  name: string;
  source: string;
  installs: number;
  sourceType: string;
  installUrl: string | null;
  url: string;
  isDuplicate?: boolean;
}

interface DescriptionCache {
  [id: string]: { status: 'loading' | 'done' | 'error'; description: string; installs?: number };
}

interface ImportedSkill {
  skill_id: string;
  skill_name: string;
  skill_uuid: string | null;
  tools_imported: number;
  snippets_imported: number;
  tags: string[];
}

// ── Component ─────────────────────────────────────────────────────────────────

interface SkillsShImporterProps {
  plugin: Plugin;
  isOpen: boolean;
  onClose: () => void;
}

export function SkillsShImporter({ plugin, isOpen, onClose }: SkillsShImporterProps) {
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [results, setResults] = useState<SkillResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [descriptions, setDescriptions] = useState<DescriptionCache>({});
  const fetchingRef = useRef<Set<string>>(new Set());

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    success: boolean;
    message: string;
    skills: ImportedSkill[];
    failed: { skill_id: string; error: string }[];
  } | null>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSubmittedQuery('');
      setResults([]);
      setSearchError(null);
      setSelected(new Set());
      setImportResult(null);
      setDescriptions({});
      fetchingRef.current.clear();
    }
  }, [isOpen]);

  // ── Search ──────────────────────────────────────────────────────────────────

  const handleSearch = async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setSearching(true);
    setSearchError(null);
    setResults([]);
    setSelected(new Set());
    setImportResult(null);
    setDescriptions({});
    fetchingRef.current.clear();
    setSubmittedQuery(q);
    try {
      const resp = await fetch(`/api/plugins/skillssh-importer/search`, {
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
      setResults(body.data.results ?? []);
    } catch (e: any) {
      setSearchError(e.message);
    } finally {
      setSearching(false);
    }
  };

  // ── Lazy description loading ─────────────────────────────────────────────────

  const fetchDescription = async (id: string) => {
    if (fetchingRef.current.has(id) || descriptions[id]) return;
    fetchingRef.current.add(id);
    setDescriptions((prev) => ({ ...prev, [id]: { status: 'loading', description: '' } }));
    try {
      const resp = await fetch(`/api/plugins/skillssh-importer/skill-description/${encodeURIComponent(id)}`);
      const body = await resp.json();
      setDescriptions((prev) => ({
        ...prev,
        [id]: { status: 'done', description: body.description ?? '', installs: body.installs },
      }));
    } catch {
      setDescriptions((prev) => ({ ...prev, [id]: { status: 'error', description: '' } }));
    }
  };

  // ── Selection helpers ────────────────────────────────────────────────────────

  const toggleRow = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === results.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(results.map((r) => r.id)));
    }
  };

  // ── Import ───────────────────────────────────────────────────────────────────

  const handleImport = async () => {
    if (selected.size === 0) return;
    setImporting(true);
    setImportResult(null);
    try {
      const resp = await fetch(`/api/plugins/skillssh-importer/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_ids: Array.from(selected), fetch_audits: true }),
      });
      const body = await resp.json();
      const data = body.data ?? body;
      setImportResult({
        success: body.success ?? false,
        message: body.message ?? '',
        skills: data.skills ?? [],
        failed: data.failed ?? [],
      });
      if (body.success) setSelected(new Set());
    } catch (e: any) {
      setImportResult({ success: false, message: e.message, skills: [], failed: [] });
    } finally {
      setImporting(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  const allSelected = results.length > 0 && selected.size === results.length;

  return (
    <Modal
      variant={ModalVariant.large}
      title={`Import from skills.sh`}
      isOpen={isOpen}
      onClose={onClose}
      description={`Search the skills.sh directory and import selected skills into the store.`}
      actions={[
        <Button
          key="import"
          variant="primary"
          icon={importing ? <Spinner size="sm" /> : <ImportIcon />}
          isDisabled={selected.size === 0 || importing}
          onClick={handleImport}
        >
          {importing ? 'Importing…' : `Import selected (${selected.size})`}
        </Button>,
        <Button key="close" variant="link" onClick={onClose}>
          Close
        </Button>,
      ]}
    >
      {/* ── Status banner when disabled ── */}
      {!plugin.enabled && (
        <Alert variant="warning" title="Plugin not configured" isInline style={{ marginBottom: '1rem' }}>
          {plugin.status}
        </Alert>
      )}

      {/* ── Search bar ── */}
      <Toolbar style={{ paddingLeft: 0 }}>
        <ToolbarContent>
          <ToolbarItem style={{ flex: 1 }}>
            <TextInput
              value={query}
              onChange={(_e, v) => setQuery(v)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search skills (e.g. pptx, react native, supabase…)"
              aria-label="Search query"
            />
          </ToolbarItem>
          <ToolbarItem>
            <Button
              variant="primary"
              icon={searching ? <Spinner size="sm" /> : <SearchIcon />}
              isDisabled={query.trim().length < 2 || searching || !plugin.enabled}
              onClick={handleSearch}
            >
              {searching ? 'Searching…' : 'Search'}
            </Button>
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>

      {/* ── Search error ── */}
      {searchError && (
        <Alert variant="danger" title="Search failed" isInline style={{ margin: '0.5rem 0' }}>
          {searchError}
        </Alert>
      )}

      {/* ── Import result ── */}
      {importResult && (
        <Alert
          variant={importResult.success ? 'success' : importResult.skills.length > 0 ? 'warning' : 'danger'}
          title={importResult.message}
          isInline
          style={{ margin: '0.5rem 0' }}
        >
          {importResult.skills.length > 0 && (
            <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem' }}>
              {importResult.skills.map((s) => (
                <li key={s.skill_id}>
                  <strong>{s.skill_name}</strong> — {s.tools_imported} tool{s.tools_imported !== 1 ? 's' : ''},&nbsp;
                  {s.snippets_imported} snippet{s.snippets_imported !== 1 ? 's' : ''}
                </li>
              ))}
            </ul>
          )}
          {importResult.failed.length > 0 && (
            <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem', color: '#a30000' }}>
              {importResult.failed.map((f) => (
                <li key={f.skill_id}><strong>{f.skill_id}</strong>: {f.error}</li>
              ))}
            </ul>
          )}
        </Alert>
      )}

      {/* ── Results table ── */}
      {results.length === 0 && !searching && submittedQuery && !searchError && (
        <EmptyState style={{ marginTop: '2rem' }}>
          <EmptyStateIcon icon={SearchIcon} />
          <EmptyStateBody>No skills found for "{submittedQuery}"</EmptyStateBody>
        </EmptyState>
      )}

      {results.length > 0 && (
        <>
          <div style={{ fontSize: '0.8rem', color: '#6a6e73', margin: '0.25rem 0 0.5rem' }}>
            {results.length} result{results.length !== 1 ? 's' : ''} — hover a row for details
          </div>
          <div style={{ overflowX: 'auto' }}>
            <Table aria-label="skills.sh search results" variant="compact">
              <Thead>
                <Tr>
                  <Th
                    select={{
                      onSelect: toggleAll,
                      isSelected: allSelected,
                      isHeaderSelectDisabled: results.length === 0,
                    }}
                  />
                  <Th width={30}>Name / ID</Th>
                  <Th width={20}>Source</Th>
                  <Th>Description</Th>
                </Tr>
              </Thead>
              <Tbody>
                {results.map((skill) => {
                  const desc = descriptions[skill.id];
                  return (
                    <SkillRow
                      key={skill.id}
                      skill={skill}
                      desc={desc}
                      isSelected={selected.has(skill.id)}
                      onToggle={() => toggleRow(skill.id)}
                      onVisible={() => fetchDescription(skill.id)}
                    />
                  );
                })}
              </Tbody>
            </Table>
          </div>
        </>
      )}
    </Modal>
  );
}

// ── SkillRow — single table row with lazy description + hover popover ─────────

interface DescEntry {
  status: 'loading' | 'done' | 'error';
  description: string;
  installs?: number;
}

interface SkillRowProps {
  skill: SkillResult;
  desc: DescEntry | undefined;
  isSelected: boolean;
  onToggle: () => void;
  onVisible: () => void;
}

function SkillRow({ skill, desc, isSelected, onToggle, onVisible }: SkillRowProps) {
  const rowRef = useRef<HTMLTableRowElement>(null);
  const hasTriggered = useRef(false);

  // IntersectionObserver — fetch description when the row enters the viewport
  useEffect(() => {
    if (hasTriggered.current || desc) return;
    const el = rowRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasTriggered.current) {
          hasTriggered.current = true;
          onVisible();
          obs.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [desc, onVisible]);

  const popoverBody = (
    <div style={{ fontSize: '0.85rem', lineHeight: 1.5 }}>
      <div><strong>ID:</strong> {skill.id}</div>
      <div><strong>Installs:</strong> {(desc?.installs ?? skill.installs).toLocaleString()}</div>
      <div><strong>Source type:</strong> {skill.sourceType}</div>
      {skill.installUrl && (
        <div>
          <strong>Install URL:</strong>{' '}
          <a href={skill.installUrl} target="_blank" rel="noopener noreferrer">
            {skill.installUrl}
          </a>
        </div>
      )}
      <div>
        <strong>View on skills.sh:</strong>{' '}
        <a href={skill.url} target="_blank" rel="noopener noreferrer">
          {skill.url}
        </a>
      </div>
      {skill.isDuplicate && (
        <Label color="orange" style={{ marginTop: '0.4rem' }}>Duplicate</Label>
      )}
    </div>
  );

  return (
    <Popover
      aria-label={`Details for ${skill.name}`}
      headerContent={<strong>{skill.name}</strong>}
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
          select={{
            rowIndex: 0,
            onSelect: (e) => { e.stopPropagation(); onToggle(); },
            isSelected,
          }}
          onClick={(e) => e.stopPropagation()}
        />
        <Td dataLabel="Name / ID">
          <Flex direction={{ default: 'column' }} spaceItems={{ default: 'spaceItemsNone' }}>
            <FlexItem>
              <strong>{skill.name}</strong>
            </FlexItem>
            <FlexItem>
              <span style={{ fontSize: '0.75rem', color: '#6a6e73' }}>{skill.id}</span>
            </FlexItem>
          </Flex>
        </Td>
        <Td dataLabel="Source">
          <span style={{ fontSize: '0.85rem' }}>{skill.source}</span>
        </Td>
        <Td dataLabel="Description">
          {!desc || desc.status === 'loading' ? (
            <Spinner size="sm" />
          ) : desc.status === 'error' || !desc.description ? (
            <span style={{ color: '#6a6e73', fontStyle: 'italic', fontSize: '0.85rem' }}>—</span>
          ) : (
            <span style={{ fontSize: '0.85rem' }}>{desc.description}</span>
          )}
        </Td>
      </Tr>
    </Popover>
  );
}

// Made with Bob
