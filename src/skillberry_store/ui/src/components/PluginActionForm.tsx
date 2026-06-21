// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useEffect } from 'react';
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
} from '@patternfly/react-core';
import type { PluginAction, PluginActionResult } from '@/types';

interface PluginActionFormProps {
  action: PluginAction;
  pluginName: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (params: Record<string, any>) => Promise<PluginActionResult>;
}

export function PluginActionForm({
  action,
  pluginName: _pluginName,
  isOpen,
  onClose,
  onSubmit,
}: PluginActionFormProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PluginActionResult | null>(null);

  // Dynamic dropdown state: field name → [{label, value}]
  const [dynamicOptions, setDynamicOptions] = useState<Record<string, { label: string; value: string }[]>>({});
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
      if (options.length === 1) {
        setFormData((prev) => ({ ...prev, [propertyName]: options[0].value }));
      }
    } finally {
      setOptionsLoading((prev) => ({ ...prev, [propertyName]: false }));
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);
    setResult(null);

    // Coerce array-typed fields from comma-separated strings to string[]
    const coercedData: Record<string, any> = { ...formData };
    if (action.params_schema.properties) {
      for (const [key, schema] of Object.entries(action.params_schema.properties) as [string, any][]) {
        if (schema.type === 'array' && typeof coercedData[key] === 'string') {
          coercedData[key] = coercedData[key]
            .split(',')
            .map((s: string) => s.trim())
            .filter(Boolean);
        }
      }
    }

    try {
      const response = await onSubmit(coercedData);
      setResult(response);

      if (response.success && response.data == null) {
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
    setFormData({});
    setError(null);
    setResult(null);
    onClose();
  };

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

  const renderField = (propertyName: string, propertySchema: any) => {
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
          label={propertyName}
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
            onChange={(_event, newValue) => handleChange(newValue)}
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

    // Default to text input
    const isArray = propertySchema.type === 'array';
    const description = isArray
      ? `${propertySchema.description || ''} (comma-separated)`.trim()
      : propertySchema.description;
    return (
      <FormGroup
        key={propertyName}
        label={propertyName}
        isRequired={isRequired}
        fieldId={propertyName}
      >
        {description && (
          <div style={{ fontSize: '0.875rem', color: '#6A6E73', marginBottom: '0.25rem' }}>
            {description}
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
          onClick={handleSubmit}
          isLoading={isSubmitting}
          isDisabled={isSubmitting}
        >
          Execute
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

      {result && result.success && (
        <Alert variant="success" title="Success" isInline style={{ marginBottom: '1rem' }}>
          {result.message || 'Action completed successfully'}
        </Alert>
      )}

      {result?.data != null && (
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

      {result && !result.success && (
        <Alert variant="warning" title="Action completed with issues" isInline style={{ marginBottom: '1rem' }}>
          {result.message || result.error || 'Action completed but may have issues'}
        </Alert>
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
