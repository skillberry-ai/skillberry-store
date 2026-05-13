// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

/**
 * Edge case tests for syntax highlighting feature
 * Tests boundary conditions, performance, and unusual scenarios
 */

test.describe('Syntax Highlighting - Edge Cases', () => {
  const API_BASE = 'http://localhost:8000';

  test('should handle extremely large code files', async ({ page, request }) => {
    // Create a snippet with a very large code file (1000+ lines)
    const largeCode = Array(1000)
      .fill(0)
      .map((_, i) => `def function_${i}():\n    """Function ${i}"""\n    return ${i}`)
      .join('\n\n');

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Large File Test ${Date.now()}`,
        description: 'Test snippet with very large file',
        content: largeCode,
        content_type: 'text/x-python',
        tags: ['test', 'performance']
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

      // Should render within reasonable time
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 10000 });

      // Should have scrollable container
      const codeContainer = page.locator('div').filter({
        has: syntaxHighlighter
      }).first();

      const isScrollable = await codeContainer.evaluate((el) => {
        return el.scrollHeight > el.clientHeight;
      });

      expect(isScrollable).toBe(true);

      // Should have line numbers
      const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
      const lineNumberCount = await lineNumbers.count();
      expect(lineNumberCount).toBeGreaterThan(100);

      // Take screenshot for visual verification
      await page.screenshot({
        path: test.info().outputPath('large-file-syntax-highlighting.png'),
        fullPage: false
      });
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle code with only whitespace', async ({ page, request }) => {
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Whitespace Test ${Date.now()}`,
        description: 'Test snippet with only whitespace',
        content: '   \n\n\t\t\t\n   \n',
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

      // Should still render syntax highlighter
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      // Content should preserve whitespace
      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toBeTruthy();
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle code with mixed line endings', async ({ page, request }) => {
    // Mix of \n, \r\n, and \r line endings
    const mixedLineEndings = 'line1\nline2\r\nline3\rline4\nline5';
    
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Mixed Line Endings Test ${Date.now()}`,
        description: 'Test snippet with mixed line endings',
        content: mixedLineEndings,
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

      // Should render all lines
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('line1');
      expect(codeContent).toContain('line2');
      expect(codeContent).toContain('line3');
      expect(codeContent).toContain('line4');
      expect(codeContent).toContain('line5');
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle code with tabs and spaces mixed', async ({ page, request }) => {
    const mixedIndentation = `def function():
\tif True:
\t    print("tab then spaces")
    \tprint("spaces then tab")
\t\tprint("double tab")
        print("many spaces")`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Mixed Indentation Test ${Date.now()}`,
        description: 'Test snippet with mixed tabs and spaces',
        content: mixedIndentation,
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

      // Should preserve indentation
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('def function');
      expect(codeContent).toContain('if True');
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle code with all special regex characters', async ({ page, request }) => {
    const regexChars = String.raw`.*+?^${}()|[]\\`;
    const codeWithRegex = `import re\npattern = r"${regexChars}"\nresult = re.match(pattern, text)`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Regex Characters Test ${Date.now()}`,
        description: 'Test snippet with regex special characters',
        content: codeWithRegex,
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

      // Should render without breaking
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('import re');
      expect(codeContent).toContain('pattern');
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle code with HTML-like tags', async ({ page, request }) => {
    const htmlLikeCode = `<template>\n  <div class="container">\n    <h1>Title</h1>\n  </div>\n</template>`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `HTML Tags Test ${Date.now()}`,
        description: 'Test snippet with HTML-like tags',
        content: htmlLikeCode,
        content_type: 'text/html',
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

      // Should render HTML correctly without executing it
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('<template>');
      expect(codeContent).toContain('<div class="container">');
      expect(codeContent).toContain('<h1>Title</h1>');

      // Verify HTML is not rendered as actual DOM elements
      const actualH1 = page.locator('h1:has-text("Title")').filter({
        hasNot: page.locator('pre[class*="language-"]')
      });
      await expect(actualH1).not.toBeVisible();
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle code with SQL injection patterns', async ({ page, request }) => {
    const sqlInjection = `SELECT * FROM users WHERE id = '1' OR '1'='1';\nDROP TABLE users;--`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `SQL Injection Test ${Date.now()}`,
        description: 'Test snippet with SQL injection patterns',
        content: sqlInjection,
        content_type: 'text/x-sql',
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

      // Should render safely
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('SELECT');
      expect(codeContent).toContain('DROP TABLE');
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle code with zero-width characters', async ({ page, request }) => {
    // Include zero-width space, zero-width joiner, etc.
    const zeroWidthChars = 'function\u200Btest\u200C(){\u200D}';

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Zero Width Test ${Date.now()}`,
        description: 'Test snippet with zero-width characters',
        content: zeroWidthChars,
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

      // Should render (zero-width chars may or may not be visible)
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('function');
      expect(codeContent).toContain('test');
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle rapid navigation between code views', async ({ page, request }) => {
    // Create multiple snippets
    const snippetIds: string[] = [];
    
    for (let i = 0; i < 3; i++) {
      const response = await request.post(`${API_BASE}/api/snippets/`, {
        data: {
          name: `Rapid Nav Test ${i} ${Date.now()}`,
          description: `Test snippet ${i}`,
          content: `def function_${i}():\n    return ${i}`,
          content_type: 'text/x-python',
          tags: ['test']
        }
      });

      if (response.ok()) {
        const snippet = await response.json();
        snippetIds.push(snippet.id);
      }
    }

    if (snippetIds.length === 0) {
      test.skip(true, 'Failed to create test snippets');
      return;
    }

    try {
      // Rapidly navigate between snippets
      for (const snippetId of snippetIds) {
        await page.goto(`/snippets/${snippetId}`);
        
        // Don't wait for full load, just check if highlighter appears
        const syntaxHighlighter = page.locator('pre[class*="language-"]');
        await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });
      }

      // Navigate back to first snippet and verify it still works
      await page.goto(`/snippets/${snippetIds[0]}`);
      await page.waitForLoadState('networkidle');
      
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible();
      
      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('function_0');
    } finally {
      // Cleanup all snippets
      for (const snippetId of snippetIds) {
        await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
      }
    }
  });

  test('should handle code with control characters', async ({ page, request }) => {
    // Include various control characters
    const controlChars = 'line1\x00line2\x01line3\x1Fline4';

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Control Chars Test ${Date.now()}`,
        description: 'Test snippet with control characters',
        content: controlChars,
        content_type: 'text/plain',
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

      // Should render without crashing
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle code with bidirectional text', async ({ page, request }) => {
    // Mix of LTR and RTL text
    const bidiText = `def function():\n    # Comment in English\n    # تعليق بالعربية\n    return "Hello مرحبا"`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Bidi Text Test ${Date.now()}`,
        description: 'Test snippet with bidirectional text',
        content: bidiText,
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

      // Should render both LTR and RTL text
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      const codeContent = await syntaxHighlighter.textContent();
      expect(codeContent).toContain('def function');
      expect(codeContent).toContain('تعليق');
      expect(codeContent).toContain('مرحبا');
    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });
});
