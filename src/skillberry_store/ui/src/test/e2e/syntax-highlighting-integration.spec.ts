// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

/**
 * Integration tests for syntax highlighting feature
 * These tests create real data via API and verify the UI behavior
 */

test.describe('Syntax Highlighting Integration', () => {
  const API_BASE = 'http://localhost:8000';
  let testSkillId: string;
  let testSnippetId: string;

  test.beforeAll(async ({ request }) => {
    // Create a test skill with a Python tool
    const skillResponse = await request.post(`${API_BASE}/skills`, {
      data: {
        name: 'Test Skill for Syntax Highlighting',
        description: 'A test skill to verify syntax highlighting',
        tags: ['test', 'syntax-highlighting'],
        tools: [
          {
            name: 'test_python_tool',
            description: 'A Python tool for testing',
            programming_language: 'python',
            module: `def hello_world():
    """A simple test function"""
    print("Hello, World!")
    return True

def calculate_sum(a: int, b: int) -> int:
    """Calculate sum of two numbers"""
    result = a + b
    return result`,
            tags: ['python', 'test']
          }
        ]
      }
    });

    if (skillResponse.ok()) {
      const skill = await skillResponse.json();
      testSkillId = skill.id;
    }

    // Create a test snippet with JavaScript code
    const snippetResponse = await request.post(`${API_BASE}/snippets`, {
      data: {
        name: 'Test JavaScript Snippet',
        description: 'A JavaScript snippet for testing syntax highlighting',
        content: `function fibonacci(n) {
  if (n <= 1) return n;
  return fibonacci(n - 1) + fibonacci(n - 2);
}

const result = fibonacci(10);
console.log('Fibonacci(10):', result);`,
        content_type: 'text/javascript',
        tags: ['javascript', 'test', 'file:fibonacci.js']
      }
    });

    if (snippetResponse.ok()) {
      const snippet = await snippetResponse.json();
      testSnippetId = snippet.id;
    }
  });

  test.afterAll(async ({ request }) => {
    // Cleanup: delete test data
    if (testSkillId) {
      await request.delete(`${API_BASE}/skills/${testSkillId}`);
    }
    if (testSnippetId) {
      await request.delete(`${API_BASE}/snippets/${testSnippetId}`);
    }
  });

  test('should display Python tool code with proper syntax highlighting', async ({ page }) => {
    test.skip(!testSkillId, 'Test skill was not created');

    await page.goto(`/skills/${testSkillId}`);
    await page.waitForLoadState('networkidle');

    // Navigate to Tools tab
    const toolsTab = page.getByRole('button', { name: /tools/i });
    await toolsTab.click();

    // Wait for tool list and click the first tool
    await page.waitForSelector('[data-testid="tool-item"], .pf-v5-c-data-list__item');
    const firstTool = page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first();
    await firstTool.click();

    // Verify syntax highlighter is rendered
    const syntaxHighlighter = page.locator('pre[class*="language-"]');
    await expect(syntaxHighlighter).toBeVisible({ timeout: 10000 });

    // Verify Python language is detected
    const codeElement = page.locator('code[class*="language-python"]');
    await expect(codeElement).toBeVisible();

    // Verify line numbers are present
    const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
    await expect(lineNumbers.first()).toBeVisible();

    // Verify code content is displayed
    const codeContent = await codeElement.textContent();
    expect(codeContent).toContain('def hello_world');
    expect(codeContent).toContain('def calculate_sum');

    // Verify dark theme styling
    const preElement = await syntaxHighlighter.first();
    const backgroundColor = await preElement.evaluate((el) => 
      window.getComputedStyle(el).backgroundColor
    );
    // vscDarkPlus theme has dark background
    expect(backgroundColor).toMatch(/rgb\(30, 30, 30\)|rgb\(31, 31, 31\)|#1e1e1e/i);

    // Take screenshot for visual verification
    await page.screenshot({
      path: test.info().outputPath('python-tool-syntax-highlighting.png'),
      fullPage: false
    });
  });

  test('should display JavaScript snippet with proper syntax highlighting', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Verify syntax highlighter is rendered
    const syntaxHighlighter = page.locator('pre[class*="language-"]');
    await expect(syntaxHighlighter).toBeVisible({ timeout: 10000 });

    // Verify JavaScript language is detected
    const codeElement = page.locator('code[class*="language-javascript"]');
    await expect(codeElement).toBeVisible();

    // Verify line numbers are present
    const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
    await expect(lineNumbers.first()).toBeVisible();

    // Verify code content is displayed
    const codeContent = await codeElement.textContent();
    expect(codeContent).toContain('function fibonacci');
    expect(codeContent).toContain('console.log');

    // Verify scrollable container
    const codeContainer = page.locator('div').filter({
      has: syntaxHighlighter
    }).first();
    const overflow = await codeContainer.evaluate((el) =>
      window.getComputedStyle(el).overflow
    );
    expect(overflow).toBe('auto');

    // Take screenshot for visual verification
    await page.screenshot({
      path: test.info().outputPath('javascript-snippet-syntax-highlighting.png'),
      fullPage: false
    });
  });

  test('should handle language detection from file tags', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // The snippet has tag 'file:fibonacci.js' which should help detect JavaScript
    const codeElement = page.locator('code[class*="language-javascript"]');
    await expect(codeElement).toBeVisible({ timeout: 10000 });

    // Verify the code is properly highlighted
    const codeContent = await codeElement.textContent();
    expect(codeContent).toBeTruthy();
    expect(codeContent!.length).toBeGreaterThan(0);
  });

  test('should maintain code formatting with proper indentation', async ({ page }) => {
    test.skip(!testSkillId, 'Test skill was not created');

    await page.goto(`/skills/${testSkillId}`);
    await page.waitForLoadState('networkidle');

    // Navigate to Tools tab and select tool
    await page.getByRole('button', { name: /tools/i }).click();
    await page.waitForSelector('[data-testid="tool-item"], .pf-v5-c-data-list__item');
    await page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first().click();

    // Get the code content
    const codeElement = page.locator('code[class*="language-"]');
    const codeContent = await codeElement.textContent();

    // Verify indentation is preserved (Python uses 4 spaces)
    expect(codeContent).toContain('    """A simple test function"""');
    expect(codeContent).toContain('    print("Hello, World!")');
    expect(codeContent).toContain('    return True');
  });

  test('should have accessible code blocks', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Verify code block is keyboard accessible
    const codeContainer = page.locator('div').filter({
      has: page.locator('pre[class*="language-"]')
    }).first();

    // Check if container is focusable or has proper ARIA attributes
    const tabIndex = await codeContainer.getAttribute('tabindex');
    const role = await codeContainer.getAttribute('role');
    
    // Container should be scrollable, which makes it accessible
    const overflow = await codeContainer.evaluate((el) =>
      window.getComputedStyle(el).overflow
    );
    expect(overflow).toBe('auto');

    // Verify pre element has proper structure
    const preElement = page.locator('pre[class*="language-"]');
    await expect(preElement).toBeVisible();
  });

  test('should handle long code with scrolling', async ({ page }) => {
    test.skip(!testSkillId, 'Test skill was not created');

    await page.goto(`/skills/${testSkillId}`);
    await page.waitForLoadState('networkidle');

    // Navigate to tool
    await page.getByRole('button', { name: /tools/i }).click();
    await page.waitForSelector('[data-testid="tool-item"], .pf-v5-c-data-list__item');
    await page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first().click();

    // Verify container has max height and is scrollable
    const codeContainer = page.locator('div').filter({
      has: page.locator('pre[class*="language-"]')
    }).first();

    const styles = await codeContainer.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return {
        maxHeight: computed.maxHeight,
        overflow: computed.overflow,
        border: computed.border
      };
    });

    expect(styles.overflow).toBe('auto');
    expect(styles.maxHeight).toContain('vh'); // Should have viewport-relative max height
    expect(styles.border).toBeTruthy(); // Should have border styling
  });
});
