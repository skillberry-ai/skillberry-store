// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

/**
 * Error handling tests for syntax highlighting feature
 * Tests how the UI handles various error conditions
 */

test.describe('Syntax Highlighting - Error Handling', () => {
  const API_BASE = 'http://localhost:8000';

  test('should handle API failure when loading skill', async ({ page, context }) => {
    // Intercept API call and return error
    await context.route(`${API_BASE}/api/skills/nonexistent-skill`, route => {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Skill not found' })
      });
    });

    await page.goto('/skills/nonexistent-skill');
    await page.waitForLoadState('networkidle');

    // Should display error message
    const errorMessage = page.locator('text=/not found|error/i');
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
  });

  test('should handle API failure when loading snippet', async ({ page, context }) => {
    // Intercept API call and return error
    await context.route(`${API_BASE}/api/snippets/nonexistent-snippet`, route => {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Snippet not found' })
      });
    });

    await page.goto('/snippets/nonexistent-snippet');
    await page.waitForLoadState('networkidle');

    // Should display error message
    const errorMessage = page.locator('text=/not found|error/i');
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
  });

  test('should handle empty tool module gracefully', async ({ page, request }) => {
    // Create a skill with an empty tool module
    const skillResponse = await request.post(`${API_BASE}/api/skills/`, {
      data: {
        name: `Empty Tool Test ${Date.now()}`,
        description: 'Test skill with empty tool',
        tags: ['test'],
        tools: [
          {
            name: 'empty_tool',
            description: 'An empty tool',
            programming_language: 'python',
            module: '',
            tags: ['python']
          }
        ]
      }
    });

    if (!skillResponse.ok()) {
      test.skip(true, 'Failed to create test skill');
      return;
    }

    const skill = await skillResponse.json();
    const skillId = skill.id;

    try {
      await page.goto(`/skills/${skillId}`);
      await page.waitForLoadState('networkidle');

      // Navigate to Tools tab
      const toolsTab = page.getByRole('button', { name: /tools/i });
      await toolsTab.click();

      // Click on the empty tool
      await page.waitForSelector('[data-testid="tool-item"], .pf-v5-c-data-list__item', { timeout: 5000 });
      const firstTool = page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first();
      await firstTool.click();

      // Should still render syntax highlighter (even if empty)
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      // Code should be empty
      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent?.trim()).toBe('');
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/skills/${skillId}`);
    }
  });

  test('should handle malformed code content', async ({ page, request }) => {
    // Create a snippet with special characters and malformed content
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Malformed Code Test ${Date.now()}`,
        description: 'Test snippet with special characters',
        content: `<script>alert('XSS')</script>\n\n\t\t\t\n"quotes" and 'quotes'\n&amp; &lt; &gt;`,
        content_type: 'text/javascript',
        tags: ['test']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      // Should render without XSS vulnerability
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      // Verify special characters are properly escaped
      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('<script>');
      expect(codeContent).toContain('alert');
      
      // Verify no actual script execution
      const alerts = [];
      page.on('dialog', dialog => {
        alerts.push(dialog.message());
        dialog.dismiss();
      });
      
      await page.waitForTimeout(1000);
      expect(alerts).toHaveLength(0);
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle network timeout gracefully', async ({ page, context }) => {
    // Simulate slow network
    await context.route(`${API_BASE}/api/skills/slow-skill`, route => {
      setTimeout(() => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'slow-skill',
            name: 'Slow Skill',
            description: 'A slow loading skill',
            tags: [],
            tools: []
          })
        });
      }, 10000); // 10 second delay
    });

    await page.goto('/skills/slow-skill');
    
    // Should show loading state
    const loadingIndicator = page.locator('text=/loading|spinner/i, [role="progressbar"]');
    await expect(loadingIndicator).toBeVisible({ timeout: 2000 });
  });

  test('should handle missing language detection gracefully', async ({ page, request }) => {
    // Create a snippet with unknown content type
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Unknown Language Test ${Date.now()}`,
        description: 'Test snippet with unknown language',
        content: `some random code\nthat has no clear language`,
        content_type: 'application/octet-stream',
        tags: ['test']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      // Should still render with default language (python)
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      // Should have some language class applied
      const codeElement = page.locator('code[class*="language-"]');
      const className = await codeElement.getAttribute('class');
      expect(className).toMatch(/language-\w+/);
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle very long lines without breaking layout', async ({ page, request }) => {
    // Create a snippet with very long lines
    const longLine = 'x'.repeat(1000);
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Long Lines Test ${Date.now()}`,
        description: 'Test snippet with very long lines',
        content: `def function():\n    ${longLine}\n    return True`,
        content_type: 'text/x-python',
        tags: ['test']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      // Should render with horizontal scroll
      const codeContainer = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]')
      }).first();

      const overflow = await codeContainer.evaluate((el) =>
        window.getComputedStyle(el).overflow
      );
      
      expect(overflow).toBe('auto');

      // Verify no layout break
      const viewportWidth = page.viewportSize()?.width || 1280;
      const containerWidth = await codeContainer.evaluate((el) => el.scrollWidth);
      
      // Container should be scrollable if content is wider
      if (containerWidth > viewportWidth) {
        expect(overflow).toBe('auto');
      }
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle Unicode and emoji in code', async ({ page, request }) => {
    // Create a snippet with Unicode characters and emoji
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Unicode Test ${Date.now()}`,
        description: 'Test snippet with Unicode',
        content: `def greet():\n    print("Hello 世界 🌍")\n    # Comment with émojis 🎉\n    return "✓"`,
        content_type: 'text/x-python',
        tags: ['test']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      // Should render Unicode correctly
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('世界');
      expect(codeContent).toContain('🌍');
      expect(codeContent).toContain('🎉');
      expect(codeContent).toContain('✓');
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });
});
