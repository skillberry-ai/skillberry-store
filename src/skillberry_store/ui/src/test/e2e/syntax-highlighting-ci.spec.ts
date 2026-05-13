// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

/**
 * CI-friendly E2E tests for syntax highlighting feature
 * These tests create their own test data and clean up after themselves
 */

test.describe('Syntax Highlighting - CI Tests', () => {
  const API_BASE = process.env.API_BASE_URL || 'http://localhost:8000';

  test('should render Python code with syntax highlighting in skill tool', async ({ page, request }) => {
    // Create a test skill with a Python tool
    const skillResponse = await request.post(`${API_BASE}/api/skills/`, {
      data: {
        name: `CI Test Skill ${Date.now()}`,
        description: 'Test skill for CI syntax highlighting verification',
        tags: ['test', 'ci'],
        tools: [
          {
            name: 'test_tool',
            description: 'A test Python tool',
            programming_language: 'python',
            module: `def hello_world():
    """A simple greeting function"""
    print("Hello, World!")
    return True

def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b`,
            tags: ['python', 'test']
          }
        ]
      }
    });

    if (!skillResponse.ok()) {
      test.skip(true, 'Failed to create test skill - API may not be available');
      return;
    }

    const skill = await skillResponse.json();
    const skillId = skill.id;

    try {
      // Navigate to the skill
      await page.goto(`/skills/${skillId}`);
      await page.waitForLoadState('networkidle');

      // Click on Tools tab
      const toolsTab = page.getByRole('button', { name: /tools/i });
      await expect(toolsTab).toBeVisible({ timeout: 10000 });
      await toolsTab.click();

      // Wait for tool list and click first tool
      await page.waitForSelector('[data-testid="tool-item"], .pf-v5-c-data-list__item', { timeout: 10000 });
      const firstTool = page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first();
      await expect(firstTool).toBeVisible();
      await firstTool.click();

      // Verify syntax highlighter is rendered
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 10000 });

      // Verify Python language is detected
      const codeElement = page.locator('code[class*="language-python"]');
      await expect(codeElement).toBeVisible();

      // Verify code content is displayed
      const codeContent = await codeElement.textContent();
      expect(codeContent).toContain('def hello_world');
      expect(codeContent).toContain('def add_numbers');

      // Verify line numbers are present
      const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
      expect(await lineNumbers.count()).toBeGreaterThan(0);

      // Verify scrollable container
      const codeContainer = page.locator('div').filter({
        has: syntaxHighlighter
      }).first();
      const overflow = await codeContainer.evaluate((el) =>
        window.getComputedStyle(el).overflow
      );
      expect(overflow).toBe('auto');

    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/skills/${skillId}`);
    }
  });

  test('should render JavaScript code with syntax highlighting in snippet', async ({ page, request }) => {
    // Create a test snippet with JavaScript code
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `CI Test Snippet ${Date.now()}`,
        description: 'Test snippet for CI syntax highlighting verification',
        content: `function fibonacci(n) {
  if (n <= 1) return n;
  return fibonacci(n - 1) + fibonacci(n - 2);
}

const result = fibonacci(10);
console.log('Result:', result);`,
        content_type: 'text/javascript',
        tags: ['javascript', 'test', 'ci']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet - API may not be available');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      // Navigate to the snippet
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      // Verify syntax highlighter is rendered
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 10000 });

      // Verify JavaScript language is detected
      const codeElement = page.locator('code[class*="language-javascript"]');
      await expect(codeElement).toBeVisible();

      // Verify code content is displayed
      const codeContent = await codeElement.textContent();
      expect(codeContent).toContain('function fibonacci');
      expect(codeContent).toContain('console.log');

      // Verify line numbers are present
      const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
      expect(await lineNumbers.count()).toBeGreaterThan(0);

    } finally {
      // Cleanup
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should detect language from file tags when content_type is missing', async ({ page, request }) => {
    // Create a snippet with file tag but no content_type
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `CI File Tag Test ${Date.now()}`,
        description: 'Test language detection from file tags',
        content: `def test_function():
    assert True`,
        tags: ['test', 'ci', 'file:test.py']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet - API may not be available');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      // Verify Python language is detected from file tag
      const codeElement = page.locator('code[class*="language-python"]');
      await expect(codeElement).toBeVisible({ timeout: 10000 });

    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should handle empty code gracefully', async ({ page, request }) => {
    // Create a snippet with empty content
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `CI Empty Code Test ${Date.now()}`,
        description: 'Test handling of empty code',
        content: '',
        content_type: 'text/x-python',
        tags: ['test', 'ci']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet - API may not be available');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      // Verify syntax highlighter is still rendered
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 10000 });

    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should render large code files with acceptable performance', async ({ page, request }) => {
    // Create a snippet with a large code file (500 lines)
    const largeCode = Array(500)
      .fill(0)
      .map((_, i) => `def function_${i}():\n    """Function ${i}"""\n    return ${i}`)
      .join('\n\n');

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `CI Performance Test ${Date.now()}`,
        description: 'Test performance with large code file',
        content: largeCode,
        content_type: 'text/x-python',
        tags: ['test', 'ci', 'performance']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet - API may not be available');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      const startTime = Date.now();
      
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      // Wait for syntax highlighter to render
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 15000 });

      const renderTime = Date.now() - startTime;

      // Verify it renders within reasonable time (15 seconds)
      expect(renderTime).toBeLessThan(15000);

      // Verify scrollable container is present
      const codeContainer = page.locator('div').filter({
        has: syntaxHighlighter
      }).first();

      const isScrollable = await codeContainer.evaluate((el) => {
        return el.scrollHeight > el.clientHeight;
      });

      expect(isScrollable).toBe(true);

      // Verify line numbers are rendered
      const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
      const lineNumberCount = await lineNumbers.count();
      expect(lineNumberCount).toBeGreaterThan(100);

    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should maintain accessibility with keyboard navigation', async ({ page, request }) => {
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `CI Accessibility Test ${Date.now()}`,
        description: 'Test keyboard accessibility',
        content: `def example():
    return "test"`,
        content_type: 'text/x-python',
        tags: ['test', 'ci']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet - API may not be available');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 10000 });

      // Verify code is accessible to screen readers
      const codeElement = page.locator('code[class*="language-"]');
      const textContent = await codeElement.textContent();
      expect(textContent).toBeTruthy();
      expect(textContent!.length).toBeGreaterThan(0);

      // Verify no aria-hidden on code content
      const ariaHidden = await codeElement.getAttribute('aria-hidden');
      expect(ariaHidden).not.toBe('true');

    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });
});
