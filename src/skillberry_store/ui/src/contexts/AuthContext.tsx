// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0
//
// Access-control frontend context. Mode is a compile-time constant injected
// by vite.config.ts (see §10.4 of docs/design/access-control.md). In
// `standalone` mode this context also installs a `window.fetch` interceptor
// on mount that (a) adds `Authorization: Bearer <token>` on same-origin
// `/api/*` calls when a token is set, and (b) clears the token and forces a
// redirect to `/login` when the server returns 401.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

type AclMode = 'disabled' | 'standalone';

const MODE: AclMode =
  ((import.meta as any).env?.VITE_ACL_MODE as AclMode) || 'disabled';

const TOKEN_KEY = 'sbs.session.token';

export interface WhoAmI {
  tenant_id: string | null;
  groups: string[];
  roles: string[];
}

interface AuthContextValue {
  mode: AclMode;
  token: string | null;
  tenantId: string | null;
  signIn(username: string, password: string): Promise<void>;
  signOut(): Promise<void>;
  whoami(): Promise<WhoAmI>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}

function loadToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // sessionStorage disabled — best-effort only.
  }
}

interface ProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: ProviderProps) {
  const [token, setToken] = useState<string | null>(() =>
    MODE === 'standalone' ? loadToken() : null
  );
  const [tenantId, setTenantId] = useState<string | null>(null);
  const tokenRef = useRef(token);
  tokenRef.current = token;

  const clear = useCallback(() => {
    setToken(null);
    setTenantId(null);
    storeToken(null);
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `login_failed_${res.status}`);
    }
    const body = (await res.json()) as {
      token: string;
      tenant_id: string;
      expires_at: string;
    };
    storeToken(body.token);
    setToken(body.token);
    setTenantId(body.tenant_id);
  }, []);

  const signOut = useCallback(async () => {
    const currentToken = tokenRef.current;
    if (currentToken) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${currentToken}` },
        });
      } catch {
        // Best-effort; always clear local state.
      }
    }
    clear();
  }, [clear]);

  const whoami = useCallback(async (): Promise<WhoAmI> => {
    const currentToken = tokenRef.current;
    if (MODE === 'disabled' || !currentToken) {
      return { tenant_id: null, groups: [], roles: [] };
    }
    const res = await fetch('/api/auth/whoami', {
      headers: { Authorization: `Bearer ${currentToken}` },
    });
    if (!res.ok) {
      throw new Error(`whoami_failed_${res.status}`);
    }
    return res.json();
  }, []);

  // ------------------------------------------------------------------ //
  // Global fetch interceptor. Installed exactly once when the provider
  // mounts in `standalone` mode; restores the original on unmount.
  // ------------------------------------------------------------------ //
  useEffect(() => {
    if (MODE !== 'standalone') return;
    if (typeof window === 'undefined' || typeof window.fetch !== 'function') return;

    const original = window.fetch.bind(window);

    const wrapped: typeof window.fetch = async (input, init) => {
      const url =
        typeof input === 'string'
          ? input
          : input instanceof URL
            ? input.toString()
            : (input as Request).url;

      // Only intercept API calls, and never re-add auth to the login endpoint.
      const isApi = url.includes('/api/') || url.startsWith('/api/');
      const isLogin = url.includes('/api/auth/login');

      let finalInit = init;
      if (isApi && !isLogin && tokenRef.current) {
        const headers = new Headers(init?.headers || {});
        if (!headers.has('Authorization')) {
          headers.set('Authorization', `Bearer ${tokenRef.current}`);
        }
        finalInit = { ...(init || {}), headers };
      }
      const response = await original(input as any, finalInit);
      if (isApi && !isLogin && response.status === 401) {
        // Session expired or invalid; force re-login.
        clear();
        if (
          typeof window !== 'undefined' &&
          window.location.pathname !== '/login'
        ) {
          window.location.assign('/login');
        }
      }
      return response;
    };

    window.fetch = wrapped;
    return () => {
      window.fetch = original;
    };
  }, [clear]);

  // On first mount (standalone + persisted token), pull whoami to hydrate
  // the tenant badge. Non-fatal on failure.
  useEffect(() => {
    if (MODE !== 'standalone' || !token) return;
    let cancelled = false;
    (async () => {
      try {
        const info = await whoami();
        if (!cancelled) setTenantId(info.tenant_id);
      } catch {
        // interceptor above already handled 401 → redirect.
      }
    })();
    return () => {
      cancelled = true;
    };
    // Only refresh whoami when the token changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      mode: MODE,
      token,
      tenantId,
      signIn,
      signOut,
      whoami,
    }),
    [token, tenantId, signIn, signOut, whoami]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
