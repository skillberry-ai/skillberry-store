// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { Fragment } from 'react';
import { useActiveManifests } from './registry';

interface PluginSlotProps {
  name: string;
  ctx?: Record<string, unknown>;
}

/**
 * Extension point rendered by main pages. Any active plugin that contributes
 * to the slot name will render its component here, receiving `ctx` as props.
 * If no plugin contributes, nothing renders.
 */
export function PluginSlot({ name, ctx }: PluginSlotProps) {
  const activeManifests = useActiveManifests();
  const contributions = activeManifests.flatMap((m) => m.slots[name] || []);
  if (contributions.length === 0) return null;
  return (
    <>
      {contributions.map((c) => {
        const Comp = c.component as React.ComponentType<any>;
        return (
          <Fragment key={c.id}>
            <Comp {...(ctx || {})} />
          </Fragment>
        );
      })}
    </>
  );
}
