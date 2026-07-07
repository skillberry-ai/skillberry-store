// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Checkbox,
  Form,
  FormGroup,
  Modal,
  ModalVariant,
  Spinner,
  Stack,
  StackItem,
  TextInput,
} from '@patternfly/react-core';
import { pluginsApi } from '@/services/api';

interface AvailablePlugin {
  slug: string;
  name?: string;
  description?: string;
  version?: string;
  required_env?: Array<{ name: string; description?: string; required?: boolean; default?: string }>;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function PluginInstallDialog({ isOpen, onClose }: Props) {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['plugins', 'available'],
    queryFn: pluginsApi.listAvailable,
    enabled: isOpen,
  });

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [envOverrides, setEnvOverrides] = useState<Record<string, Record<string, string>>>({});
  const [installErrors, setInstallErrors] = useState<Record<string, string>>({});

  const available: AvailablePlugin[] = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  const installMutation = useMutation({
    mutationFn: async () => {
      setInstallErrors({});
      const results = await Promise.allSettled(
        Array.from(selected).map(async (slug) => {
          try {
            await pluginsApi.install(slug, true, envOverrides[slug]);
            return { slug, ok: true };
          } catch (e: any) {
            setInstallErrors((prev) => ({ ...prev, [slug]: e?.message ?? 'Install failed' }));
            throw e;
          }
        }),
      );
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
      return results;
    },
    onSuccess: (results) => {
      const anyFail = results.some((r) => r.status === 'rejected');
      if (!anyFail) {
        setSelected(new Set());
        setEnvOverrides({});
        onClose();
      }
    },
  });

  const toggleSelected = (slug: string, checked: boolean) => {
    const next = new Set(selected);
    if (checked) next.add(slug);
    else next.delete(slug);
    setSelected(next);
  };

  const setEnv = (slug: string, name: string, value: string) => {
    setEnvOverrides((prev) => ({
      ...prev,
      [slug]: { ...(prev[slug] ?? {}), [name]: value },
    }));
  };

  return (
    <Modal
      variant={ModalVariant.medium}
      title="Install plugin"
      isOpen={isOpen}
      onClose={onClose}
      actions={[
        <Button
          key="install"
          variant="primary"
          isDisabled={selected.size === 0 || installMutation.isPending}
          onClick={() => installMutation.mutate()}
        >
          {installMutation.isPending ? <Spinner size="sm" /> : `Install ${selected.size || ''}`}
        </Button>,
        <Button key="cancel" variant="link" onClick={onClose}>
          Cancel
        </Button>,
      ]}
    >
      {isLoading && <Spinner size="lg" />}
      {error && <Alert variant="danger" title="Failed to load catalog">{(error as Error).message}</Alert>}
      {!isLoading && !error && available.length === 0 && (
        <p>No installable plugins found in the catalog.</p>
      )}
      <Stack hasGutter>
        {available.map((p) => (
          <StackItem key={p.slug}>
            <Checkbox
              id={`plugin-${p.slug}`}
              label={<strong>{p.name || p.slug}</strong>}
              description={<span>{p.description} — v{p.version}</span>}
              isChecked={selected.has(p.slug)}
              onChange={(_e, checked) => toggleSelected(p.slug, !!checked)}
            />
            {selected.has(p.slug) && p.required_env && p.required_env.length > 0 && (
              <Form style={{ marginLeft: '2rem', marginTop: '0.5rem' }}>
                {p.required_env.map((ev) => (
                  <FormGroup
                    key={ev.name}
                    label={ev.name}
                    fieldId={`env-${p.slug}-${ev.name}`}
                  >
                    <TextInput
                      id={`env-${p.slug}-${ev.name}`}
                      value={envOverrides[p.slug]?.[ev.name] ?? ''}
                      placeholder={ev.default ?? (ev.required ? 'required' : 'optional')}
                      onChange={(_e, value) => setEnv(p.slug, ev.name, value)}
                    />
                  </FormGroup>
                ))}
              </Form>
            )}
            {installErrors[p.slug] && (
              <Alert variant="danger" title={`Failed to install ${p.slug}`} isInline>
                {installErrors[p.slug]}
              </Alert>
            )}
          </StackItem>
        ))}
      </Stack>
    </Modal>
  );
}
