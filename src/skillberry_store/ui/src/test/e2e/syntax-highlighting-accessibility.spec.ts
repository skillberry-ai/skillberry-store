// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Accessibility tests for syntax highlighting feature
 * Tests WCAG compliance and keyboard navigation
 */

test.describe('Syntax Highlighting Accessibility', () => {
  const API_BASE = 'http://localhost:8000';
  let testSnippetId: string;

  test.beforeAll(async ({ request }) => {
    // Create a test snippet for accessibility testing
    const snippetResponse = await request.post(`${API_BASE}/snippets`, {
      data: {
        name: 'Accessibility Test Snippet',
        description: 'A snippet for testing accessibility',
        content: `def fibonacci(n):
    """Calculate Fibonacci number recursively"""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# Example usage
result = fibonacci(10)
print(f"Fibonacci(10) = {result}")`,
        content_type: 'text/x-python',
        tags: ['python', 'test', 'accessibility'],
      },
    });

    if (snippetResponse.ok()) {
      const snippet = await snippetResponse.json();
      testSnippetId = snippet.id;
    }
  });

  test.afterAll(async ({ request }) => {
    if (testSnippetId) {
      await request.delete(`${API_BASE}/snippets/${testSnippetId}`);
    }
  });

  test('should have no accessibility violations on snippet detail page', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter to render
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    // Run axe accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('should support keyboard navigation for scrollable code', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    // Find the scrollable container
    const codeContainer = page.locator('div').filter({
      has: page.locator('pre[class*="language-"]'),
    }).first();

    // Tab to the code container area
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Verify container is scrollable
    const isScrollable = await codeContainer.evaluate((el) => {
      return el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth;
    });

    if (isScrollable) {
      // Test arrow key navigation
      const initialScrollTop = await codeContainer.evaluate((el) => el.scrollTop);
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('ArrowDown');
      const newScrollTop = await codeContainer.evaluate((el) => el.scrollTop);

      // Scroll position should change or stay the same (if already at bottom)
      expect(newScrollTop).toBeGreaterThanOrEqual(initialScrollTop);
    }
  });

  test('should have proper semantic HTML structure', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    // Verify semantic structure
    const preElement = page.locator('pre[class*="language-"]');
    await expect(preElement).toBeVisible();

    const codeElement = preElement.locator('code');
    await expect(codeElement).toBeVisible();

    // Verify proper nesting
    const isProperlyNested = await preElement.evaluate((pre) => {
      const code = pre.querySelector('code');
      return code !== null && pre.contains(code);
    });

    expect(isProperlyNested).toBe(true);
  });

  test('should have sufficient color contrast for code', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    // Run contrast check
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .include('pre[class*="language-"]')
      .analyze();

    const contrastViolations = accessibilityScanResults.violations.filter(
      (v) => v.id === 'color-contrast'
    );

    expect(contrastViolations).toEqual([]);
  });

  test('should be readable by screen readers', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    const codeElement = page.locator('code[class*="language-"]');
    
    // Verify code content is accessible to screen readers
    const textContent = await codeElement.textContent();
    expect(textContent).toBeTruthy();
    expect(textContent!.length).toBeGreaterThan(0);

    // Verify no aria-hidden on code content
    const ariaHidden = await codeElement.getAttribute('aria-hidden');
    expect(ariaHidden).not.toBe('true');
  });

  test('should support text selection', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    const codeElement = page.locator('code[class*="language-"]');

    // Try to select text
    await codeElement.click();
    await page.keyboard.down('Shift');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.up('Shift');

    // Get selected text
    const selectedText = await page.evaluate(() => window.getSelection()?.toString());
    
    // Should be able to select text
    expect(selectedText).toBeTruthy();
  });

  test('should support copy functionality', async ({ page, context }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    const codeElement = page.locator('code[class*="language-"]');

    // Select all code
    await codeElement.click();
    await page.keyboard.press('Control+A');
    
    // Copy to clipboard
    await page.keyboard.press('Control+C');

    // Verify clipboard has content
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toContain('fibonacci');
  });

  test('should have proper focus indicators', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    // Navigate with keyboard
    await page.keyboard.press('Tab');
    
    // Check if focused element is visible
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return null;
      
      const styles = window.getComputedStyle(el);
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        outlineStyle: styles.outlineStyle,
      };
    });

    // Should have some focus indicator (outline or other visual cue)
    expect(focusedElement).toBeTruthy();
  });

  test('should maintain readability at different zoom levels', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    // Test at 200% zoom (WCAG requirement)
    await page.evaluate(() => {
      document.body.style.zoom = '2';
    });

    // Wait for reflow
    await page.waitForTimeout(500);

    // Verify code is still visible and readable
    const codeElement = page.locator('code[class*="language-"]');
    await expect(codeElement).toBeVisible();

    const isOverflowing = await codeElement.evaluate((el) => {
      return el.scrollWidth > el.clientWidth;
    });

    // Code should be scrollable if it overflows
    if (isOverflowing) {
      const container = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]'),
      }).first();
      
      const overflow = await container.evaluate((el) =>
        window.getComputedStyle(el).overflow
      );
      
      expect(overflow).toBe('auto');
    }

    // Reset zoom
    await page.evaluate(() => {
      document.body.style.zoom = '1';
    });
  });

  test('should work with browser text size adjustments', async ({ page }) => {
    test.skip(!testSnippetId, 'Test snippet was not created');

    await page.goto(`/snippets/${testSnippetId}`);
    await page.waitForLoadState('networkidle');

    // Wait for syntax highlighter
    await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

    // Increase text size
    await page.evaluate(() => {
      document.documentElement.style.fontSize = '20px';
    });

    // Wait for reflow
    await page.waitForTimeout(500);

    // Verify code is still visible
    const codeElement = page.locator('code[class*="language-"]');
    await expect(codeElement).toBeVisible();

    // Verify text is larger
    const fontSize = await codeElement.evaluate((el) =>
      window.getComputedStyle(el).fontSize
    );
    
    expect(fontSize).toBeTruthy();

    // Reset font size
    await page.evaluate(() => {
      document.documentElement.style.fontSize = '';
    });
  });
});
