// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useMemo, useState } from 'react';
import {
  Label,
  Checkbox,
  Button,
  ToggleGroup,
  ToggleGroupItem,
  Alert,
  Tooltip,
  ExpandableSection,
} from '@patternfly/react-core';

interface Finding {
  engine?: string;
  rule_id?: string;
  severity?: string;
  message?: string;
  line?: number | null;
  file?: string;
}

interface ScanResult {
  uuid?: string;
  name?: string;
  content_type?: string;
  summary?: Record<string, number>;
  findings?: Finding[];
}

interface FixResult {
  uuid?: string;
  name?: string;
  content_type?: string;
  status?: string;
  old_code?: string;
  new_code?: string;
}

interface ResultDetailsProps {
  result: any;
  /** Whether the LLM "fix" capability is available (key configured). */
  fixCapability?: boolean;
  /** Human-readable reason fix is unavailable (for the disabled tooltip). */
  fixStatus?: string;
  /** Call the plugin's fix endpoint with selected uuids + severities. */
  onFix?: (objectUuids: string[], severities: string[]) => Promise<any>;
}

const SEVERITIES = ['critical', 'high', 'medium', 'low'] as const;
type Severity = (typeof SEVERITIES)[number];

const SEVERITY_COLOR: Record<string, 'red' | 'orange' | 'gold' | 'grey'> = {
  critical: 'red',
  high: 'orange',
  medium: 'gold',
  low: 'grey',
};

function FindingRow({ f }: { f: Finding }) {
  return (
    <div style={{ padding: '0.35rem 0', borderBottom: '1px solid #f0f0f0' }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <Label color={SEVERITY_COLOR[f.severity || ''] || 'grey'} isCompact>
          {f.severity || '—'}
        </Label>
        <span style={{ fontFamily: 'monospace', fontSize: '0.85em' }}>{f.rule_id}</span>
        {f.file && (
          <span style={{ fontSize: '0.8em', color: '#6a6e73' }}>
            {f.file}
            {f.line != null ? `:${f.line}` : ''}
          </span>
        )}
      </div>
      {f.message && (
        <div style={{ fontSize: '0.85em', color: '#444', marginTop: '0.15rem' }}>{f.message}</div>
      )}
    </div>
  );
}

/** Per-object fix outcome (status + collapsible old→new diff). */
function FixOutcome({ fixes }: { fixes: FixResult[] }) {
  return (
    <div style={{ marginBottom: '1rem' }}>
      {fixes.map((fx, i) => (
        <div key={fx.uuid || i} style={{ marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <Label color={fx.status === 'fixed' ? 'green' : 'grey'} isCompact>
              {fx.status}
            </Label>
            {fx.name && <span style={{ fontWeight: 'bold' }}>{fx.name}</span>}
            <span style={{ fontFamily: 'monospace', fontSize: '0.8em', color: '#6a6e73' }}>
              {fx.uuid}
            </span>
          </div>
          {fx.status === 'fixed' && fx.new_code != null && (
            <ExpandableSection toggleText="Show change">
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <pre style={preStyle('before')}>{fx.old_code}</pre>
                <pre style={preStyle('after')}>{fx.new_code}</pre>
              </div>
            </ExpandableSection>
          )}
        </div>
      ))}
    </div>
  );
}

function preStyle(kind: 'before' | 'after'): React.CSSProperties {
  return {
    flex: 1,
    maxHeight: '16rem',
    overflow: 'auto',
    fontSize: '0.75em',
    padding: '0.5rem',
    borderRadius: '3px',
    background: kind === 'before' ? '#fdf2f2' : '#f2fbf2',
  };
}

/**
 * Renders a plugin action's result inline so the user can read it (the modal
 * stays open). Specialized for the SAST scan shape ({results, not_found,
 * summary}) with a severity filter, per-object selection, and an LLM "Fix"
 * button; falls back to pretty-printed JSON for any other `data`.
 */
export function ResultDetails({ result, fixCapability, fixStatus, onFix }: ResultDetailsProps) {
  const scanResults: ScanResult[] | undefined = Array.isArray(result.results)
    ? result.results
    : undefined;
  const notFound: string[] = Array.isArray(result.not_found) ? result.not_found : [];

  // Active severity filter (default: all on).
  const [active, setActive] = useState<Set<Severity>>(new Set(SEVERITIES));
  // Objects selected for fixing.
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [fixing, setFixing] = useState(false);
  const [fixError, setFixError] = useState<string | null>(null);
  const [fixes, setFixes] = useState<FixResult[] | null>(null);

  const toggleSeverity = (s: Severity) => {
    setActive((prev) => {
      const next = new Set(prev);
      next.has(s) ? next.delete(s) : next.add(s);
      return next;
    });
  };

  // Per object: findings matching the active severities. Only tool/snippet
  // objects with matching findings are fixable.
  const perObject = useMemo(() => {
    if (!scanResults) return [];
    return scanResults.map((r) => {
      const matching = (r.findings || []).filter(
        (f) => f.severity && active.has(f.severity as Severity)
      );
      const fixable =
        (r.content_type === 'tool' || r.content_type === 'snippet') && matching.length > 0;
      return { r, matching, fixable };
    });
  }, [scanResults, active]);

  const fixableUuids = perObject.filter((o) => o.fixable).map((o) => o.r.uuid as string);

  const toggleSelected = (uuid: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(uuid) ? next.delete(uuid) : next.add(uuid);
      return next;
    });
  };

  const runFix = async () => {
    if (!onFix) return;
    setFixing(true);
    setFixError(null);
    setFixes(null);
    try {
      const resp = await onFix(Array.from(selected), Array.from(active));
      setFixes(Array.isArray(resp?.results) ? resp.results : []);
    } catch (e: any) {
      setFixError(e?.message || 'Fix failed');
    } finally {
      setFixing(false);
    }
  };

  if (scanResults) {
    const selectedFixable = Array.from(selected).filter((u) => fixableUuids.includes(u));
    const fixDisabledReason = !fixCapability
      ? fixStatus || 'Set OPENAI_API_KEY to enable Fix'
      : selectedFixable.length === 0
        ? 'Select at least one object with matching findings'
        : null;

    const fixButton = (
      <Button
        variant="primary"
        size="sm"
        isLoading={fixing}
        isDisabled={!!fixDisabledReason || fixing}
        onClick={runFix}
      >
        Fix selected ({selectedFixable.length})
      </Button>
    );

    return (
      <div style={{ marginBottom: '1rem' }}>
        {/* Severity filter + fix controls */}
        <div
          style={{
            display: 'flex',
            gap: '0.75rem',
            alignItems: 'center',
            flexWrap: 'wrap',
            marginBottom: '0.5rem',
          }}
        >
          <ToggleGroup aria-label="Filter by severity">
            {SEVERITIES.map((s) => (
              <ToggleGroupItem
                key={s}
                text={s}
                buttonId={`sev-${s}`}
                isSelected={active.has(s)}
                onChange={() => toggleSeverity(s)}
              />
            ))}
          </ToggleGroup>
          {onFix &&
            (fixDisabledReason ? (
              <Tooltip content={fixDisabledReason}>
                <span>{fixButton}</span>
              </Tooltip>
            ) : (
              fixButton
            ))}
        </div>

        {fixError && (
          <Alert variant="danger" title="Fix failed" isInline style={{ marginBottom: '0.5rem' }}>
            {fixError}
          </Alert>
        )}
        {fixes && <FixOutcome fixes={fixes} />}

        <div
          style={{
            maxHeight: '22rem',
            overflowY: 'auto',
            border: '1px solid #d2d2d2',
            borderRadius: '3px',
            padding: '0.5rem',
          }}
        >
          {notFound.length > 0 && (
            <div style={{ fontSize: '0.85em', color: '#a30000', marginBottom: '0.5rem' }}>
              Not found: {notFound.join(', ')}
            </div>
          )}
          {perObject.map(({ r, matching, fixable }, i) => {
            if (matching.length === 0) return null; // hidden by the active filter
            const uuid = r.uuid as string;
            return (
              <div key={uuid || i} style={{ marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  {fixable && (
                    <Checkbox
                      id={`sel-${uuid}`}
                      isChecked={selected.has(uuid)}
                      onChange={() => toggleSelected(uuid)}
                      aria-label={`Select ${r.name || uuid}`}
                    />
                  )}
                  <Label color="blue" isCompact>{r.content_type}</Label>
                  {r.name && <span style={{ fontWeight: 'bold' }}>{r.name}</span>}
                  <span style={{ fontFamily: 'monospace', fontSize: '0.8em', color: '#6a6e73' }}>
                    {uuid}
                  </span>
                </div>
                <div style={{ marginTop: '0.25rem', paddingLeft: '1.5rem' }}>
                  {matching.map((f, j) => (
                    <FindingRow key={j} f={f} />
                  ))}
                </div>
              </div>
            );
          })}
          {perObject.every((o) => o.matching.length === 0) && (
            <div style={{ fontSize: '0.85em', color: '#6a6e73' }}>
              No findings at the selected severities.
            </div>
          )}
        </div>
      </div>
    );
  }

  // Generic fallback: show whatever data the action returned.
  const payload = result.data ?? result;
  return (
    <pre
      style={{
        marginBottom: '1rem',
        maxHeight: '24rem',
        overflow: 'auto',
        background: '#f5f5f5',
        padding: '0.5rem',
        borderRadius: '3px',
        fontSize: '0.8em',
      }}
    >
      {JSON.stringify(payload, null, 2)}
    </pre>
  );
}
