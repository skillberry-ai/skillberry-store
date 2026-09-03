// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0
//
// The operator-configured login message on the sign-in screen.
// See §6.3 and §12.4 of docs/design/login-info.md.
//
// The server injects `<meta name="sbs-login-info" content="...">` into
// index.html at serve time, so these tests set that tag on the jsdom document
// before rendering — exactly what the component reads.

import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from './LoginPage';

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    mode: 'standalone' as const,
    token: null,
    tenantId: null,
    signIn: vi.fn(),
    signOut: vi.fn(),
    whoami: vi.fn(),
  }),
}));

const META_NAME = 'sbs-login-info';

function setLoginInfoMeta(content: string) {
  const meta = document.createElement('meta');
  meta.setAttribute('name', META_NAME);
  meta.setAttribute('content', content);
  document.head.appendChild(meta);
}

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

afterEach(() => {
  document.head
    .querySelectorAll(`meta[name="${META_NAME}"]`)
    .forEach((el) => el.remove());
});

describe('LoginPage login-information message', () => {
  it('renders the message from the meta tag', () => {
    setLoginInfoMeta('Shared eval box — do not store secrets.');
    renderLoginPage();

    // getByText throws when absent, so this both finds and asserts.
    expect(screen.getByText('Shared eval box — do not store secrets.')).not.toBeNull();
  });

  it('renders the message verbatim, adding no heading or label', () => {
    // A change that reintroduces a "Notice:" prefix or a separate title must
    // fail here: a message that wants to open with a word says so itself.
    const message = 'Access requests: ops@example.com';
    setLoginInfoMeta(message);
    const { container } = renderLoginPage();

    const alert = container.querySelector('[data-testid="login-info"]');
    expect(alert).not.toBeNull();
    // PatternFly's Alert adds a screen-reader-only "Info alert:" prefix; the
    // visible text must be the message and nothing else.
    const visible = Array.from(alert!.querySelectorAll('span'))
      .map((el) => el.textContent)
      .filter((text): text is string => !!text);
    expect(visible).toContain(message);
    expect(visible.some((text) => text !== message && text.includes(message))).toBe(
      false
    );
  });

  it('renders no alert when the meta tag is absent', () => {
    const { container } = renderLoginPage();

    expect(container.querySelector('[data-testid="login-info"]')).toBeNull();
  });

  it('renders no alert when the meta tag content is empty', () => {
    setLoginInfoMeta('');
    const { container } = renderLoginPage();

    expect(container.querySelector('[data-testid="login-info"]')).toBeNull();
  });

  it('renders markup in the message as visible text, creating no element', () => {
    const hostile = '<script>alert(1)</script>';
    setLoginInfoMeta(hostile);
    const { container } = renderLoginPage();

    const alert = container.querySelector('[data-testid="login-info"]');
    expect(alert).not.toBeNull();
    expect(alert!.querySelector('script')).toBeNull();
    expect(screen.getByText(hostile)).not.toBeNull();
  });

  it('preserves configured line breaks with white-space: pre-line', () => {
    const message = 'First line.\nSecond line.';
    setLoginInfoMeta(message);
    const { container } = renderLoginPage();

    const rendered = Array.from(
      container.querySelectorAll<HTMLElement>('[data-testid="login-info"] span')
    ).find((el) => el.textContent === message);
    expect(rendered).toBeDefined();
    expect(rendered!.style.whiteSpace).toBe('pre-line');
    expect(rendered!.style.fontWeight).toBe('normal');
  });

  it('still renders the sign-in form alongside the message', () => {
    setLoginInfoMeta('Heads up.');
    renderLoginPage();

    expect(screen.getByLabelText(/username/i)).not.toBeNull();
    expect(screen.getByLabelText(/password/i)).not.toBeNull();
  });
});
