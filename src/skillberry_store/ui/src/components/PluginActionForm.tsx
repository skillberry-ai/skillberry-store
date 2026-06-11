// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
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
import { ObjectPicker } from './ObjectPicker';
import { MultiSelectField } from './MultiSelectField';
import { ResultDetails } from './ResultDetails';

interface PluginActionFormProps {
  action: PluginAction;
  pluginName: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (params: Record<string, any>) => Promise<PluginActionResult>;
  /** The owning plugin's ui_config.capabilities (e.g. { fix, fix_status }). */
  capabilities?: Record<string, any>;
  /** Call a secondary plugin endpoint (e.g. "fix"). */
  onCallAction?: (
    pluginName: string,
    actionName: string,
    params: Record<string, any>,
  ) => Promise<any>;
}

/** True when a result carries data the user would want to read (so the modal
 *  should stay open instead of auto-closing). */
function hasReadableResult(result: any): boolean {
  if (!result || typeof result !== 'object') return false;
  return (
    Array.isArray(result.results) ||
    Array.isArray(result.findings) ||
    Array.isArray(result.not_found) ||
    result.summary != null ||
    result.data != null
  );
}

export function PluginActionForm({
  action,
  pluginName,
  isOpen,
  onClose,
  onSubmit,
  capabilities,
  onCallAction,
}: PluginActionFormProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PluginActionResult | null>(null);

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

      // Auto-close only for simple fire-and-forget actions. If the action
      // returned data worth reading (e.g. scan findings), keep the modal open
      // so the user can review it and close it themselves.
      if (response.success && !hasReadableResult(response)) {
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

    // Object picker → searchable multi-select of store objects (emits UUIDs)
    if (propertySchema.type === 'object_picker') {
      const selected: string[] = Array.isArray(value) ? value : [];
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
          <ObjectPicker
            objectTypes={propertySchema.object_types || ['skill', 'tool', 'snippet']}
            multiple={propertySchema.multiple !== false}
            value={selected}
            onChange={(uuids) =>
              setFormData((prev) => ({ ...prev, [propertyName]: uuids }))
            }
          />
        </FormGroup>
      );
    }

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

    // Array with a fixed option set → multi-select dropdown (checkboxes)
    if (
      propertySchema.type === 'array' &&
      (propertySchema.widget === 'multiselect' || propertySchema.items?.enum)
    ) {
      const options: string[] = propertySchema.items?.enum || [];
      const selected: string[] = Array.isArray(value)
        ? value
        : Array.isArray(propertySchema.default)
          ? propertySchema.default
          : [];
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
          <MultiSelectField
            options={options}
            value={selected}
            onChange={(vals) =>
              setFormData((prev) => ({ ...prev, [propertyName]: vals }))
            }
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

      {result && !result.success && (
        <Alert variant="warning" title="Action completed with issues" isInline style={{ marginBottom: '1rem' }}>
          {result.message || result.error || 'Action completed but may have issues'}
        </Alert>
      )}

      {result && hasReadableResult(result) && (
        <ResultDetails
          result={result}
          fixCapability={capabilities?.fix === true}
          fixStatus={capabilities?.fix_status}
          onFix={
            onCallAction
              ? (objectUuids, severities) =>
                  onCallAction(pluginName, 'fix', {
                    object_uuids: objectUuids,
                    severities,
                  })
              : undefined
          }
        />
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
