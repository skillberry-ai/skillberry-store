// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useEffect, useMemo, useState } from 'react';
import {
  Select,
  SelectList,
  SelectOption,
  MenuToggle,
  TextInput,
  Button,
  Label,
  Spinner,
  Alert,
} from '@patternfly/react-core';
import type { MenuToggleElement } from '@patternfly/react-core';
import { toolsApi, skillsApi, snippetsApi } from '@/services/api';

/** An object the user can pick, tagged with its store type. */
interface PickableObject {
  uuid: string;
  name: string;
  description?: string;
  type: 'skill' | 'tool' | 'snippet';
}

interface ObjectPickerProps {
  /** Which store types to list (subset of skill/tool/snippet). */
  objectTypes: string[];
  /** Allow selecting more than one object. */
  multiple?: boolean;
  /** Currently selected UUIDs. */
  value: string[];
  /** Called with the new selected UUID list. */
  onChange: (uuids: string[]) => void;
}

const TYPE_COLOR: Record<PickableObject['type'], 'blue' | 'green' | 'purple'> = {
  skill: 'blue',
  tool: 'green',
  snippet: 'purple',
};

/**
 * Searchable, multi-select picker over store objects (skills/tools/snippets).
 * Emits selected UUIDs. Mirrors the Select pattern used on SkillsPage, but
 * keyed by UUID and tagged with the object's type so the type is visible
 * (the backend infers content type from the UUID).
 */
export function ObjectPicker({
  objectTypes,
  multiple = true,
  value,
  onChange,
}: ObjectPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [objects, setObjects] = useState<PickableObject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const wanted = new Set(objectTypes);
        const calls: Promise<PickableObject[]>[] = [];
        if (wanted.has('tool')) {
          calls.push(
            toolsApi.list().then((items) =>
              items.map((t) => ({ uuid: t.uuid, name: t.name, description: t.description, type: 'tool' as const }))
            )
          );
        }
        if (wanted.has('skill')) {
          calls.push(
            skillsApi.list().then((items) =>
              items.map((s) => ({ uuid: s.uuid, name: s.name, description: s.description, type: 'skill' as const }))
            )
          );
        }
        if (wanted.has('snippet')) {
          calls.push(
            snippetsApi.list().then((items) =>
              items.map((s) => ({ uuid: s.uuid, name: s.name, description: s.description, type: 'snippet' as const }))
            )
          );
        }
        const lists = await Promise.all(calls);
        if (!cancelled) setObjects(lists.flat());
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Failed to load objects');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [objectTypes.join(',')]);

  const byUuid = useMemo(
    () => Object.fromEntries(objects.map((o) => [o.uuid, o])),
    [objects]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return objects;
    return objects.filter(
      (o) =>
        o.name.toLowerCase().includes(q) ||
        o.uuid.toLowerCase().includes(q) ||
        (o.description || '').toLowerCase().includes(q)
    );
  }, [objects, search]);

  const handleSelect = (_event: any, selectedValue: string | number | undefined) => {
    const uuid = String(selectedValue);
    if (!uuid) return;
    if (multiple) {
      if (value.includes(uuid)) {
        onChange(value.filter((v) => v !== uuid));
      } else {
        onChange([...value, uuid]);
      }
    } else {
      onChange([uuid]);
      setIsOpen(false);
    }
  };

  const remove = (uuid: string) => onChange(value.filter((v) => v !== uuid));

  if (error) {
    return (
      <Alert variant="warning" title="Could not load objects" isInline>
        {error}
      </Alert>
    );
  }

  const toggleText = loading
    ? 'Loading…'
    : value.length === 0
      ? 'Select object(s)…'
      : `${value.length} selected`;

  return (
    <>
      <Select
        id="object-picker-select"
        isOpen={isOpen}
        selected={multiple ? value : value[0] ?? null}
        onSelect={handleSelect}
        onOpenChange={(open) => setIsOpen(open)}
        // Render the menu in a body-level portal and match it to the toggle
        // width, so it cannot be clipped by (or overflow beyond) the modal/
        // viewport; the popper flips/shifts to stay on screen.
        popperProps={{
          appendTo: () => document.body,
          width: 'trigger',
          enableFlip: true,
        }}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            onClick={() => setIsOpen(!isOpen)}
            isExpanded={isOpen}
            isDisabled={loading}
            style={{ width: '100%' }}
          >
            {loading ? <Spinner size="sm" /> : toggleText}
          </MenuToggle>
        )}
      >
        <TextInput
          type="search"
          value={search}
          onChange={(_, v) => setSearch(v)}
          placeholder="Search by name, UUID, or description…"
          style={{ padding: '0.5rem', borderBottom: '1px solid #d2d2d2' }}
        />
        <SelectList style={{ maxHeight: '20rem', overflowY: 'auto' }}>
          {filtered.length === 0 ? (
            <SelectOption isDisabled>
              {objects.length === 0 ? 'No objects available' : 'No matches'}
            </SelectOption>
          ) : (
            filtered.map((o) => (
              <SelectOption
                key={o.uuid}
                value={o.uuid}
                hasCheckbox={multiple}
                isSelected={value.includes(o.uuid)}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <Label color={TYPE_COLOR[o.type]} isCompact>
                      {o.type}
                    </Label>
                    <span style={{ fontWeight: 'bold' }}>{o.name}</span>
                  </div>
                  <div style={{ fontSize: '0.85em', color: '#6a6e73', fontFamily: 'monospace' }}>
                    {o.uuid}
                  </div>
                  {o.description && (
                    <div style={{ fontSize: '0.9em', color: '#6a6e73' }}>{o.description}</div>
                  )}
                </div>
              </SelectOption>
            ))
          )}
        </SelectList>
      </Select>
      {value.length > 0 && (
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
          {value.map((uuid) => {
            const o = byUuid[uuid];
            return (
              <Button
                key={uuid}
                variant="plain"
                onClick={() => remove(uuid)}
                style={{
                  padding: '0.25rem 0.5rem',
                  backgroundColor: '#e7f1fa',
                  border: '1px solid #bee1f4',
                  borderRadius: '3px',
                }}
              >
                {o ? `${o.type}: ${o.name}` : uuid} ✕
              </Button>
            );
          })}
        </div>
      )}
    </>
  );
}
