// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

const POLL_INTERVAL_MS = 5000;
const WATCHED_KEYS = ['skills', 'tools', 'snippets', 'vmcp-servers', 'vnfs-servers'];

export function useChangesMonitor(): void {
  const queryClient = useQueryClient();
  const lastCountRef = useRef<number | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch('/api/changes');
        if (!res.ok) return;
        const { count } = await res.json();
        if (lastCountRef.current !== null && count !== lastCountRef.current) {
          WATCHED_KEYS.forEach(key =>
            queryClient.invalidateQueries({ queryKey: [key] })
          );
        }
        lastCountRef.current = count;
      } catch {
        // network error — silently skip this tick
      }
    };

    const id = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [queryClient]);
}
