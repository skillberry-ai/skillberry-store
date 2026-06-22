// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  Checkbox,
  Button,
  Alert,
  FormSelect,
  FormSelectOption,
  TextContent,
} from '@patternfly/react-core';
import type { PluginAction, PluginActionResult } from '@/types';

// A file picked from a dropped/selected folder, with its path relative to that folder.
type PickedFile = { file: File; path: string };

async function readDirEntries(reader: any): Promise<any[]> {
  const all: any[] = [];
  // readEntries yields children in batches; call until it returns none.
  for (;;) {
    const batch: any[] = await new Promise((res, rej) => reader.readEntries(res, rej));
    if (!batch.length) break;
    all.push(...batch);
  }
  return all;
}

async function walkEntry(entry: any, prefix: string, out: PickedFile[]): Promise<void> {
  if (entry.isFile) {
    const file: File = await new Promise((res, rej) => entry.file(res, rej));
    out.push({ file, path: prefix + entry.name });
  } else if (entry.isDirectory) {
    const children = await readDirEntries(entry.createReader());
    for (const child of children) await walkEntry(child, `${prefix}${entry.name}/`, out);
  }
}

// Recursively read a dropped folder via the DataTransferItem entries API,
// falling back to the flat file list when the browser doesn't support it.
async function gatherDroppedFiles(dt: DataTransfer): Promise<PickedFile[]> {
  const out: PickedFile[] = [];
  const entries = Array.from(dt.items)
    .map((it: any) => (it.webkitGetAsEntry ? it.webkitGetAsEntry() : null))
    .filter(Boolean);
  if (entries.length) {
    for (const e of entries) await walkEntry(e, '', out);
    return out;
  }
  return Array.from(dt.files).map((f) => ({ file: f, path: (f as any).webkitRelativePath || f.name }));
}

function gatherInputFiles(list: FileList): PickedFile[] {
  return Array.from(list).map((f) => ({ file: f, path: (f as any).webkitRelativePath || f.name }));
}

interface PluginActionFormProps {
  action: PluginAction;
  pluginName: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (params: Record<string, any>) => Promise<PluginActionResult>;
}

export function PluginActionForm({
  action,
  pluginName,
  isOpen,
  onClose,
  onSubmit,
}: PluginActionFormProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PluginActionResult | null>(null);

  // Async-job polling (opt-in via action.async_action). `jobId` drives the poll;
  // `timedOut` is set once the configured deadline passes.
  const asyncConfig = action.async_action;
  const [jobId, setJobId] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);

  // Optional post-result "cleanup" action (e.g. delete a kept workspace).
  const [cleanupState, setCleanupState] = useState<'idle' | 'deleting' | 'done'>('idle');

  // Directory-upload state per field (drag-drop a folder → upload → token).
  const [uploadState, setUploadState] = useState<
    Record<string, { status: 'idle' | 'uploading' | 'done' | 'error'; count?: number; name?: string; error?: string }>
  >({});

  // Dynamic dropdown state: field name → [{label, value}]
  const [dynamicOptions, setDynamicOptions] = useState<Record<string, { label: string; value: string }[]>>({});
  // Raw fetched items per field, retained so x-prefill can read keys other than label/value.
  const [dynamicRawItems, setDynamicRawItems] = useState<Record<string, any[]>>({});
  const [optionsLoading, setOptionsLoading] = useState<Record<string, boolean>>({});

  const extractItems = (data: unknown): unknown[] => {
    if (Array.isArray(data)) return data;
    if (data && typeof data === 'object') {
      const vals = Object.values(data as object);
      if (vals.length === 1) {
        const v = vals[0];
        if (Array.isArray(v)) return v;
        if (v && typeof v === 'object') return Object.values(v as object);
      }
    }
    return [];
  };

  const interpolateUrl = (template: string, data: Record<string, any>) =>
    template.replace(/\{(\w+)\}/g, (_, key) => encodeURIComponent(data[key] ?? ''));

  const fetchOptions = async (propertyName: string, schema: any, currentFormData: Record<string, any>) => {
    const url = interpolateUrl(schema['x-options-from'], currentFormData);
    const labelKey: string = schema['x-option-label'] ?? 'label';
    const valueKey: string = schema['x-option-value'] ?? 'value';
    const excludeTags: string[] = schema['x-exclude-tags'] ?? [];
    setOptionsLoading((prev) => ({ ...prev, [propertyName]: true }));
    try {
      const resp = await fetch(url);
      if (!resp.ok) return;
      const raw = await resp.json();
      const items = extractItems(raw) as any[];
      const filtered = items.filter(
        (item) => !excludeTags.some((tag) => (item.tags ?? []).includes(tag))
      );
      const options = filtered.map((item) => ({ label: item[labelKey], value: item[valueKey] }));
      setDynamicOptions((prev) => ({ ...prev, [propertyName]: options }));
      setDynamicRawItems((prev) => ({ ...prev, [propertyName]: filtered }));
      if (options.length === 1) {
        setFormData((prev) => ({ ...prev, [propertyName]: options[0].value }));
      }
    } finally {
      setOptionsLoading((prev) => ({ ...prev, [propertyName]: false }));
    }
  };

  // Apply an x-prefill map: when a dropdown option is selected, copy values from the
  // selected raw option object into sibling form fields. Returns the patch (excluding the
  // dropdown's own value) so callers can merge it into a single state update.
  const computePrefill = (
    propertyName: string,
    schema: any,
    selectedValue: string
  ): Record<string, any> => {
    const prefill = schema['x-prefill'] as Record<string, string> | undefined;
    if (!prefill) return {};
    const valueKey: string = schema['x-option-value'] ?? 'value';
    const items = dynamicRawItems[propertyName] ?? [];
    const selected = items.find((item) => String(item[valueKey]) === String(selectedValue));
    const patch: Record<string, any> = {};
    for (const [targetField, optionKey] of Object.entries(prefill)) {
      const raw = selected ? selected[optionKey] : undefined;
      // Copy the RAW value: arrays stay arrays (the list widget renders them),
      // strings stay strings.
      patch[targetField] = raw ?? '';
    }
    return patch;
  };

  // Poll the plugin-declared status endpoint while a job is pending. React Query
  // stops polling (refetchInterval → false) once the job is ready or failed.
  const statusQuery = useQuery({
    queryKey: ['plugin-action-status', pluginName, jobId],
    enabled: !!jobId && !!asyncConfig,
    refetchInterval: (query) => {
      const status = (query.state.data as { status?: string } | undefined)?.status;
      if (status === 'ready' || status === 'failed') return false;
      return asyncConfig?.poll_interval_ms ?? 2000;
    },
    queryFn: async () => {
      const url = interpolateUrl(asyncConfig!.status_endpoint, { job_id: jobId! });
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return resp.json() as Promise<{ status?: string; detail?: string; message?: string }>;
    },
  });

  const jobStatus = statusQuery.data?.status;
  const isPolling = !!jobId && !timedOut && jobStatus !== 'ready' && jobStatus !== 'failed';
  const inAsyncJob = !!asyncConfig && (jobId !== null || timedOut);

  // Start a timeout deadline whenever a new job begins polling.
  useEffect(() => {
    if (!jobId || !asyncConfig) return;
    setTimedOut(false);
    const handle = setTimeout(() => {
      setTimedOut(true);
      setJobId(null); // disables the query
    }, asyncConfig.timeout_ms ?? 180_000);
    return () => clearTimeout(handle);
  }, [jobId, asyncConfig]);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);
    setResult(null);
    setJobId(null);
    setTimedOut(false);

    // Coerce array-typed fields from comma-separated strings to string[]
    const coercedData: Record<string, any> = { ...formData };
    if (action.params_schema.properties) {
      for (const [key, schema] of Object.entries(action.params_schema.properties) as [string, any][]) {
        if (schema.type === 'array') {
          const v = coercedData[key];
          if (Array.isArray(v)) {
            coercedData[key] = v.map((s: string) => String(s).trim()).filter(Boolean);
          } else if (typeof v === 'string') {
            // Legacy/safety: comma-separated string from older state.
            coercedData[key] = v
              .split(',')
              .map((s: string) => s.trim())
              .filter(Boolean);
          }
        }
      }
    }

    try {
      const response = await onSubmit(coercedData);
      setResult(response);

      const pendingJobId =
        asyncConfig && response.success && response.data?.status === 'pending'
          ? (response.data.job_id as string | undefined)
          : undefined;

      if (pendingJobId) {
        // Async job: begin polling instead of treating the response as final.
        setJobId(pendingJobId);
      } else if (response.success && response.data == null) {
        // Auto-close on success only when there's no data to display
        setTimeout(() => {
          handleClose();
        }, 2000);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to execute action');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setJobId(null);
    setTimedOut(false);
    setFormData({});
    setError(null);
    setResult(null);
    setCleanupState('idle');
    setUploadState({});
    onClose();
  };

  const handleCleanup = async () => {
    if (!asyncConfig?.cleanup_action || !jobId) return;
    setCleanupState('deleting');
    try {
      const url = interpolateUrl(asyncConfig.cleanup_action.endpoint, { job_id: jobId });
      const resp = await fetch(url, { method: 'POST' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setCleanupState('done');
    } catch {
      setCleanupState('idle');
    }
  };

  // Upload a picked folder to the field's endpoint; store the returned token as
  // the field value so it submits like any other field.
  const uploadDirectory = async (propertyName: string, endpoint: string, picked: PickedFile[]) => {
    if (!picked.length) return;
    const topName = picked[0].path.split('/')[0] || `${picked.length} files`;
    setUploadState((p) => ({ ...p, [propertyName]: { status: 'uploading', name: topName } }));
    try {
      const fd = new FormData();
      // The third arg sets each part's filename to its relative path, which the
      // server uses to rebuild the folder structure.
      for (const { file, path } of picked) fd.append('files', file, path);
      const resp = await fetch(endpoint, { method: 'POST', body: fd });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      const id = json?.data?.upload_id as string | undefined;
      const count = (json?.data?.file_count as number | undefined) ?? picked.length;
      if (!id) throw new Error('No upload id returned');
      setFormData((prev) => ({ ...prev, [propertyName]: id }));
      setUploadState((p) => ({ ...p, [propertyName]: { status: 'done', count, name: topName } }));
    } catch (e: any) {
      setFormData((prev) => {
        const next = { ...prev };
        delete next[propertyName];
        return next;
      });
      setUploadState((p) => ({ ...p, [propertyName]: { status: 'error', error: e?.message || 'Upload failed' } }));
    }
  };

  const clearUpload = (propertyName: string) => {
    setFormData((prev) => {
      const next = { ...prev };
      delete next[propertyName];
      return next;
    });
    setUploadState((p) => ({ ...p, [propertyName]: { status: 'idle' } }));
  };

  // Seed schema defaults into formData when the form opens so prefilled values
  // (e.g. the store MCP servers JSON) are actually submitted, not just displayed.
  useEffect(() => {
    if (!isOpen || !action.params_schema.properties) return;
    setFormData((prev) => {
      const next = { ...prev };
      for (const [name, schema] of Object.entries(action.params_schema.properties) as [string, any][]) {
        if (next[name] === undefined && schema.default !== undefined) {
          next[name] = schema.default;
        }
      }
      return next;
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // Fetch options for non-dependent fields on open
  useEffect(() => {
    if (!isOpen || !action.params_schema.properties) return;
    for (const [name, schema] of Object.entries(action.params_schema.properties) as [string, any][]) {
      if (schema['x-options-from'] && !schema['x-depends-on']) {
        fetchOptions(name, schema, formData);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // Refetch dependent dropdowns when their parent value changes
  useEffect(() => {
    if (!action.params_schema.properties) return;
    for (const [name, schema] of Object.entries(action.params_schema.properties) as [string, any][]) {
      const parentField = schema['x-depends-on'];
      if (schema['x-options-from'] && parentField) {
        if (formData[parentField]) {
          fetchOptions(name, schema, formData);
        } else {
          setDynamicOptions((prev) => ({ ...prev, [name]: [] }));
          setFormData((prev) => { const next = { ...prev }; delete next[name]; return next; });
        }
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [Object.entries(action.params_schema.properties ?? {})
      .filter(([, s]: [string, any]) => s['x-depends-on'])
      .map(([, s]: [string, any]) => formData[s['x-depends-on']])
      .join(',')]);

  // A field may declare `x-visible-when: { field, equals }` to only render when
  // another field has a given value (e.g. a server URL shown once a box is ticked).
  const isFieldVisible = (propertySchema: any): boolean => {
    const cond = propertySchema['x-visible-when'];
    if (!cond) return true;
    const current = formData[cond.field] ?? action.params_schema.properties?.[cond.field]?.default;
    return current === cond.equals;
  };

  const renderField = (propertyName: string, propertySchema: any) => {
    if (!isFieldVisible(propertySchema)) return null;

    const isRequired = action.params_schema.required?.includes(propertyName);
    const value = formData[propertyName] !== undefined
      ? formData[propertyName]
      : (propertySchema.default ?? '');

    const handleChange = (newValue: string | boolean) => {
      setFormData((prev) => ({
        ...prev,
        [propertyName]: newValue,
      }));
    };

    // Handle different field types
    if (propertySchema.type === 'boolean') {
      return (
        <FormGroup
          key={propertyName}
          label={propertySchema.title ?? propertyName}
          isRequired={isRequired}
          fieldId={propertyName}
        >
          <Checkbox
            id={propertyName}
            isChecked={!!value}
            onChange={(_event, checked) => handleChange(checked)}
            label={propertySchema.description || propertyName}
          />
        </FormGroup>
      );
    }

    // Directory upload (drag-drop a folder → upload → store the returned token)
    if (propertySchema.format === 'directory-upload') {
      const endpoint: string = propertySchema['x-upload-endpoint'];
      const title: string = propertySchema.title ?? propertyName;
      const inputId = `${propertyName}-dirinput`;
      const st = uploadState[propertyName] ?? { status: 'idle' as const };
      return (
        <FormGroup key={propertyName} label={title} isRequired={isRequired} fieldId={propertyName}>
          {propertySchema.description && (
            <div style={{ fontSize: '0.875rem', color: '#6A6E73', marginBottom: '0.25rem' }}>
              {propertySchema.description}
            </div>
          )}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={async (e) => {
              e.preventDefault();
              const picked = await gatherDroppedFiles(e.dataTransfer);
              uploadDirectory(propertyName, endpoint, picked);
            }}
            onClick={() => document.getElementById(inputId)?.click()}
            style={{
              border: '2px dashed #b8bbbe',
              borderRadius: '6px',
              padding: '1.25rem',
              textAlign: 'center',
              cursor: 'pointer',
              background: '#fafafa',
            }}
          >
            {st.status === 'uploading' && <span>Uploading {st.name}…</span>}
            {st.status === 'done' && (
              <span>✓ {st.name} — {st.count} file(s) ready. Click or drop to replace.</span>
            )}
            {st.status === 'error' && (
              <span style={{ color: '#c9190b' }}>{st.error}. Click or drop to retry.</span>
            )}
            {(st.status === 'idle' || st.status === undefined) && (
              <span>Drag-drop a skills folder here, or click to browse</span>
            )}
            <input
              id={inputId}
              type="file"
              multiple
              {...({ webkitdirectory: '', directory: '' } as any)}
              style={{ display: 'none' }}
              onChange={(e) => {
                const files = e.target.files;
                if (files && files.length) uploadDirectory(propertyName, endpoint, gatherInputFiles(files));
              }}
            />
          </div>
          {st.status === 'done' && (
            <Button variant="link" isInline onClick={() => clearUpload(propertyName)} style={{ marginTop: '0.25rem' }}>
              Remove folder
            </Button>
          )}
        </FormGroup>
      );
    }

    // Handle text area for longer text
    if (propertySchema.type === 'string' && propertySchema.description?.toLowerCase().includes('description')) {
      return (
        <FormGroup
          key={propertyName}
          label={propertyName}
          isRequired={isRequired}
          fieldId={propertyName}
        >
          {propertySchema.description && (
            <div style={{ fontSize: '0.875rem', color: '#6A6E73', marginBottom: '0.25rem' }}>
              {propertySchema.description}
            </div>
          )}
          <TextArea
            id={propertyName}
            value={value as string}
            onChange={(_event, newValue) => handleChange(newValue)}
            rows={4}
          />
        </FormGroup>
      );
    }

    // Enum → native select
    if (propertySchema.enum) {
      return (
        <FormGroup
          key={propertyName}
          label={propertyName}
          isRequired={isRequired}
          fieldId={propertyName}
        >
          {propertySchema.description && (
            <div style={{ fontSize: '0.875rem', color: '#6A6E73', marginBottom: '0.25rem' }}>
              {propertySchema.description}
            </div>
          )}
          <FormSelect
            id={propertyName}
            value={value as string}
            onChange={(_event, newValue) => handleChange(newValue)}
          >
            {propertySchema.enum.map((option: string) => (
              <FormSelectOption key={option} value={option} label={option} />
            ))}
          </FormSelect>
        </FormGroup>
      );
    }

    // Dynamic dropdown (x-options-from)
    if (propertySchema['x-options-from']) {
      const parentField = propertySchema['x-depends-on'];
      const isDisabled = !!parentField && !formData[parentField];
      const options = dynamicOptions[propertyName] ?? [];
      const loading = optionsLoading[propertyName] ?? false;
      const title: string = propertySchema.title ?? propertyName;
      return (
        <FormGroup
          key={propertyName}
          label={title}
          isRequired={isRequired}
          fieldId={propertyName}
        >
          <FormSelect
            id={propertyName}
            value={(value as string) || ''}
            onChange={(_event, newValue) => {
              if (propertySchema['x-prefill']) {
                const patch = computePrefill(propertyName, propertySchema, newValue);
                setFormData((prev) => ({ ...prev, [propertyName]: newValue, ...patch }));
              } else {
                handleChange(newValue);
              }
            }}
            isDisabled={isDisabled || loading}
          >
            <FormSelectOption
              value=""
              label={loading ? 'Loading…' : isDisabled ? `Select a ${parentField} first` : `Select ${title.toLowerCase()}`}
              isDisabled
            />
            {options.map((opt) => (
              <FormSelectOption key={opt.value} value={opt.value} label={opt.label} />
            ))}
          </FormSelect>
        </FormGroup>
      );
    }

    if (propertySchema.type === 'string' && propertySchema.format === 'textarea') {
      return (
        <FormGroup
          key={propertyName}
          label={propertySchema.title ?? propertyName}
          isRequired={isRequired}
          fieldId={propertyName}
        >
          {propertySchema.description && (
            <div style={{ fontSize: '0.875rem', color: '#6A6E73', marginBottom: '0.25rem' }}>
              {propertySchema.description}
            </div>
          )}
          <TextArea
            id={propertyName}
            value={(value as string) ?? ''}
            onChange={(_event, newValue) => handleChange(newValue)}
            rows={6}
            aria-label={propertySchema.title ?? propertyName}
          />
        </FormGroup>
      );
    }

    // Array → editable list of text inputs (add/remove rows)
    if (propertySchema.type === 'array') {
      const items: string[] = Array.isArray(value) ? value : value ? [String(value)] : [];
      const displayItems = items.length === 0 ? [''] : items;
      const title: string = propertySchema.title ?? propertyName;

      const setItems = (next: string[]) => {
        setFormData((prev) => ({ ...prev, [propertyName]: next }));
      };
      const updateItem = (index: number, newValue: string) => {
        const next = [...displayItems];
        next[index] = newValue;
        setItems(next);
      };
      const removeItem = (index: number) => {
        const next = displayItems.filter((_, i) => i !== index);
        setItems(next);
      };
      const addItem = () => {
        setItems([...displayItems, '']);
      };

      return (
        <FormGroup
          key={propertyName}
          label={title}
          isRequired={isRequired}
          fieldId={propertyName}
        >
          {propertySchema.description && (
            <div style={{ fontSize: '0.875rem', color: '#6A6E73', marginBottom: '0.25rem' }}>
              {propertySchema.description}
            </div>
          )}
          {displayItems.map((item, index) => (
            <div
              key={index}
              style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.25rem' }}
            >
              <TextInput
                id={index === 0 ? propertyName : `${propertyName}-${index}`}
                value={item}
                onChange={(_event, newValue) => updateItem(index, newValue)}
                aria-label={`${title} item ${index + 1}`}
              />
              <Button
                variant="plain"
                aria-label={`Remove ${title} item ${index + 1}`}
                onClick={() => removeItem(index)}
              >
                ✕
              </Button>
            </div>
          ))}
          <Button variant="link" onClick={addItem}>
            Add
          </Button>
        </FormGroup>
      );
    }

    // Default to text input
    return (
      <FormGroup
        key={propertyName}
        label={propertySchema.title ?? propertyName}
        isRequired={isRequired}
        fieldId={propertyName}
      >
        {propertySchema.description && (
          <div style={{ fontSize: '0.875rem', color: '#6A6E73', marginBottom: '0.25rem' }}>
            {propertySchema.description}
          </div>
        )}
        <TextInput
          id={propertyName}
          value={value as string}
          onChange={(_event, newValue) => handleChange(newValue)}
          type={propertySchema.type === 'number' ? 'number' : 'text'}
        />
      </FormGroup>
    );
  };

  return (
    <Modal
      variant={ModalVariant.medium}
      title={action.label}
      description={action.description}
      isOpen={isOpen}
      onClose={handleClose}
      actions={[
        <Button
          key="submit"
          variant="primary"
          onClick={jobStatus === 'ready' ? handleClose : handleSubmit}
          isLoading={isSubmitting || isPolling}
          isDisabled={isSubmitting || isPolling}
        >
          {jobStatus === 'ready'
            ? asyncConfig?.labels.done ?? 'Done'
            : isSubmitting || isPolling
            ? 'Working…'
            : 'Execute'}
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      {error && (
        <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>
          {error}
        </Alert>
      )}

      {/* Async-job lifecycle (opt-in via action.async_action). All strings come
          from the plugin's async_action.labels — nothing plugin-specific here. */}
      {inAsyncJob && asyncConfig && (
        <>
          {isPolling && (
            <Alert variant="info" title={asyncConfig.labels.pending} isInline style={{ marginBottom: '1rem' }}>
              {result?.message}
            </Alert>
          )}
          {jobStatus === 'ready' && (
            <Alert variant="success" title={asyncConfig.labels.ready} isInline style={{ marginBottom: '1rem' }}>
              {statusQuery.data?.message}
            </Alert>
          )}
          {jobStatus === 'ready' &&
            asyncConfig.result_link &&
            (statusQuery.data as any)?.[asyncConfig.result_link.field] && (
              <div style={{ marginBottom: '0.75rem' }}>
                <a
                  href={(statusQuery.data as any)[asyncConfig.result_link.field] as string}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {asyncConfig.result_link.label}
                </a>
              </div>
            )}
          {jobStatus === 'ready' &&
            asyncConfig.result_markdown_field &&
            (statusQuery.data as any)?.[asyncConfig.result_markdown_field] && (
              <TextContent style={{ marginTop: '0.5rem' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {(statusQuery.data as any)[asyncConfig.result_markdown_field] as string}
                </ReactMarkdown>
              </TextContent>
            )}
          {jobStatus === 'ready' &&
            asyncConfig.cleanup_action &&
            (statusQuery.data as any)?.[asyncConfig.cleanup_action.when_field] && (
              <div style={{ marginBottom: '1rem' }}>
                {cleanupState === 'done' ? (
                  <Alert variant="info" title="Workspace deleted" isInline />
                ) : (
                  <Button
                    variant="secondary"
                    isDanger
                    onClick={handleCleanup}
                    isLoading={cleanupState === 'deleting'}
                    isDisabled={cleanupState === 'deleting'}
                  >
                    {asyncConfig.cleanup_action.label}
                  </Button>
                )}
              </div>
            )}
          {jobStatus === 'failed' && (
            <Alert variant="danger" title={asyncConfig.labels.failed} isInline style={{ marginBottom: '1rem' }}>
              {statusQuery.data?.detail ?? 'Unknown error'}
            </Alert>
          )}
          {timedOut && (
            <Alert variant="warning" title={asyncConfig.labels.timeout} isInline style={{ marginBottom: '1rem' }} />
          )}
        </>
      )}

      {!inAsyncJob && result && result.success && (
        <Alert variant="success" title="Success" isInline style={{ marginBottom: '1rem' }}>
          {result.message || 'Action completed successfully'}
        </Alert>
      )}

      {!inAsyncJob && result?.data != null && (
        <pre style={{
          marginBottom: '1rem',
          maxHeight: '20rem',
          overflow: 'auto',
          background: '#f5f5f5',
          padding: '0.75rem',
          borderRadius: '3px',
          fontSize: '0.8em',
          whiteSpace: 'pre-wrap',
        }}>
          {JSON.stringify(result.data, null, 2)}
        </pre>
      )}

      {!inAsyncJob && result && !result.success && result.error && (
        <Alert variant="danger" title={result.message || 'Action failed'} isInline style={{ marginBottom: '1rem' }}>
          {result.error}
        </Alert>
      )}

      {!inAsyncJob && result && !result.success && !result.error && (
        <Alert variant="warning" title={result.message || 'Action completed with issues'} isInline style={{ marginBottom: '1rem' }} />
      )}

      <Form>
        {action.params_schema.properties &&
          Object.entries(action.params_schema.properties).map(([name, schema]) =>
            renderField(name, schema)
          )}
      </Form>
    </Modal>
  );
}

// Made with Bob
