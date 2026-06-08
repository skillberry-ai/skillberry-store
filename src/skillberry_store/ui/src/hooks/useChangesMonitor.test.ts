import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { useChangesMonitor } from './useChangesMonitor';

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe('useChangesMonitor', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not call invalidateQueries on the first tick', async () => {
    const queryClient = new QueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ count: 5 }),
    }));

    renderHook(() => useChangesMonitor(), { wrapper: makeWrapper(queryClient) });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it('calls invalidateQueries when count changes on second tick', async () => {
    const queryClient = new QueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => {
      callCount++;
      return {
        ok: true,
        json: async () => ({ count: callCount === 1 ? 3 : 7 }),
      };
    }));

    renderHook(() => useChangesMonitor(), { wrapper: makeWrapper(queryClient) });

    // First tick — stores count 3, no invalidation
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(invalidateSpy).not.toHaveBeenCalled();

    // Second tick — count changed to 7, invalidation fires
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(invalidateSpy).toHaveBeenCalledTimes(5); // one per watched key
  });

  it('does not call invalidateQueries when count is unchanged', async () => {
    const queryClient = new QueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ count: 4 }),
    }));

    renderHook(() => useChangesMonitor(), { wrapper: makeWrapper(queryClient) });

    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });

    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it('silently skips tick when fetch fails', async () => {
    const queryClient = new QueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network error')));

    renderHook(() => useChangesMonitor(), { wrapper: makeWrapper(queryClient) });

    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });

    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it('silently skips tick when response is not ok', async () => {
    const queryClient = new QueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));

    renderHook(() => useChangesMonitor(), { wrapper: makeWrapper(queryClient) });

    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });

    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});
