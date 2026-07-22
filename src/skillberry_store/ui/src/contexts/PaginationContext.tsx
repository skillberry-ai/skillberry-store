// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

const STORAGE_KEY = 'sbs-list-page-size';
export const DEFAULT_PAGE_SIZE = 25;
export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

function readInitialPageSize(): number {
  if (typeof window === 'undefined') return DEFAULT_PAGE_SIZE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PAGE_SIZE;
    const parsed = Number.parseInt(raw, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_PAGE_SIZE;
  } catch {
    return DEFAULT_PAGE_SIZE;
  }
}

interface PaginationContextValue {
  pageSize: number;
  setPageSize: (n: number) => void;
}

const PaginationContext = createContext<PaginationContextValue | null>(null);

export function PaginationProvider({ children }: { children: React.ReactNode }) {
  const [pageSize, setPageSizeState] = useState<number>(() => readInitialPageSize());

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(pageSize));
    } catch {
      // ignore quota / disabled storage
    }
  }, [pageSize]);

  const setPageSize = useCallback((n: number) => {
    setPageSizeState(n > 0 ? n : DEFAULT_PAGE_SIZE);
  }, []);

  const value = useMemo(() => ({ pageSize, setPageSize }), [pageSize, setPageSize]);
  return (
    <PaginationContext.Provider value={value}>{children}</PaginationContext.Provider>
  );
}

export function usePagination(): PaginationContextValue {
  const ctx = useContext(PaginationContext);
  if (!ctx) {
    // Provider missing: fall back to defaults so components stay usable in
    // tests / storybook-style renders.
    return { pageSize: DEFAULT_PAGE_SIZE, setPageSize: () => {} };
  }
  return ctx;
}
