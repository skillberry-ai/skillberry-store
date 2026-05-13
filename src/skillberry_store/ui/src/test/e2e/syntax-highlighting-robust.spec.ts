// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect, waitForSyntaxHighlighter, verifySyntaxHighlighting, verifyScrollableContainer, getCodeContent } from './fixtures';

/**
 * Robust E2E tests for syntax highlighting feature
 * Uses fixtures for reliable test data creation and cleanup
 */

test.describe('Syntax Highlighting - Robust E2E Tests', () => {
  test('should display Python tool code with proper syntax highlighting', async ({ page, testSkill }) => {
    // Navigate to the test skill
    await page.goto(`/skills/${testSkill.id}`);
    await page.waitForLoadState('networkidle');

    // Navigate to Tools tab
    const toolsTab = page.getByRole('button', { name: /tools/i });
    await expect(toolsTab).toBeVisible();
    await toolsTab.click();

    // Wait for tool list and click the first tool
    await page.waitForSelector('[data-testid="tool-item"], .pf-v5-c-data-list__item', { timeout: 10000 });
    const firstTool = page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first();
    await expect(firstTool).toBeVisible();
    await firstTool.click();

    // Verify syntax highlighting
    await verifySyntaxHighlighting(page, 'python');

    // Verify code content is displayed correctly
    const codeContent = await getCodeContent(page);
    expect(codeContent).toContain('def hello_world');
    expect(codeContent).toContain('def calculate_sum');
    expect(codeContent).toContain('class Calculator');

    // Verify scrollable container
    await verifyScrollableContainer(page);

    // Verify dark theme styling
    const syntaxHighlighter = page.locator('pre[class*="language-"]').first();
    const backgroundColor = await syntaxHighlighter.evaluate((el) => 
      window.getComputedStyle(el).backgroundColor
    );
    // vscDarkPlus theme has dark background
    expect(backgroundColor).toMatch(/rgb\(30, 30, 30\)|rgb\(31, 31, 31\)|#1e1e1e/i);

    // Take screenshot for visual verification
    await page.screenshot({
      path: test.info().outputPath('robust-python-tool-syntax-highlighting.png'),
      fullPage: false
    });
  });

  test('should display JavaScript snippet in skill with proper syntax highlighting', async ({ page, testSkill }) => {
    // Navigate to the test skill
    await page.goto(`/skills/${testSkill.id}`);
    await page.waitForLoadState('networkidle');

    // Navigate to Snippets tab
    const snippetsTab = page.getByRole('button', { name: /snippets/i });
    await expect(snippetsTab).toBeVisible();
    await snippetsTab.click();

    // Wait for snippet list and click the first snippet
    await page.waitForSelector('[data-testid="snippet-item"], .pf-v5-c-data-list__item', { timeout: 10000 });
    const firstSnippet = page.locator('[data-testid="snippet-item"], .pf-v5-c-data-list__item').first();
    await expect(firstSnippet).toBeVisible();
    await firstSnippet.click();

    // Verify syntax highlighting
    await verifySyntaxHighlighting(page, 'javascript');

    // Verify code content
    const codeContent = await getCodeContent(page);
    expect(codeContent).toContain('const greet');
    expect(codeContent).toContain('console.log');

    // Verify scrollable container
    await verifyScrollableContainer(page);
  });

  test('should display Python snippet with proper syntax highlighting', async ({ page, testSnippet }) => {
    // Navigate to the test snippet
    await page.goto(`/snippets/${testSnippet.id}`);
    await page.waitForLoadState('networkidle');

    // Verify syntax highlighting
    await verifySyntaxHighlighting(page, 'python');

    // Verify code content is displayed correctly
    const codeContent = await getCodeContent(page);
    expect(codeContent).toContain('def fibonacci');
    expect(codeContent).toContain('def factorial');
    expect(codeContent).toContain('Fibonacci(10)');
    expect(codeContent).toContain('Factorial(5)');

    // Verify scrollable container
    await verifyScrollableContainer(page);

    // Verify line numbers are present and functional
    const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
    const lineNumberCount = await lineNumbers.count();
    expect(lineNumberCount).toBeGreaterThan(10); // Should have multiple line numbers

    // Take screenshot for visual verification
    await page.screenshot({
      path: test.info().outputPath('robust-python-snippet-syntax-highlighting.png'),
      fullPage: false
    });
  });

  test('should maintain code formatting and indentation', async ({ page, testSnippet }) => {
    await page.goto(`/snippets/${testSnippet.id}`);
    await page.waitForLoadState('networkidle');

    await waitForSyntaxHighlighter(page);

    // Get the code content
    const codeContent = await getCodeContent(page);

    // Verify indentation is preserved (Python uses 4 spaces)
    expect(codeContent).toContain('    """Calculate Fibonacci number recursively"""');
    expect(codeContent).toContain('    if n <= 1:');
    expect(codeContent).toContain('        return n');
    expect(codeContent).toContain('    return fibonacci(n - 1) + fibonacci(n - 2)');
  });

  test('should support text selection and copy', async ({ page, context, testSnippet }) => {
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    await page.goto(`/snippets/${testSnippet.id}`);
    await page.waitForLoadState('networkidle');

    await waitForSyntaxHighlighter(page);

    const codeElement = page.locator('code[class*="language-"]');

    // Select all code
    await codeElement.click();
    await page.keyboard.press('Control+A');
    
    // Copy to clipboard
    await page.keyboard.press('Control+C');

    // Verify clipboard has content
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toContain('fibonacci');
    expect(clipboardText).toContain('factorial');
  });

  test('should handle scrolling for long code', async ({ page, testSkill }) => {
    await page.goto(`/skills/${testSkill.id}`);
    await page.waitForLoadState('networkidle');

    // Navigate to tool with long code
    await page.getByRole('button', { name: /tools/i }).click();
    await page.waitForSelector('[data-testid="tool-item"], .pf-v5-c-data-list__item');
    await page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first().click();

    await waitForSyntaxHighlighter(page);

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

  test('should detect language from file tags', async ({ page, testSnippet }) => {
    // The test snippet has tag 'file:test.py' which should help detect Python
    await page.goto(`/snippets/${testSnippet.id}`);
    await page.waitForLoadState('networkidle');

    await waitForSyntaxHighlighter(page);

    // Verify Python language is detected
    const codeElement = page.locator('code[class*="language-python"]');
    await expect(codeElement).toBeVisible();

    // Verify the code is properly highlighted
    const codeContent = await codeElement.textContent();
    expect(codeContent).toBeTruthy();
    expect(codeContent!.length).toBeGreaterThan(0);
  });

  test('should have proper semantic HTML structure', async ({ page, testSnippet }) => {
    await page.goto(`/snippets/${testSnippet.id}`);
    await page.waitForLoadState('networkidle');

    await waitForSyntaxHighlighter(page);

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

  test('should be accessible to screen readers', async ({ page, testSnippet }) => {
    await page.goto(`/snippets/${testSnippet.id}`);
    await page.waitForLoadState('networkidle');

    await waitForSyntaxHighlighter(page);

    const codeElement = page.locator('code[class*="language-"]');
    
    // Verify code content is accessible to screen readers
    const textContent = await codeElement.textContent();
    expect(textContent).toBeTruthy();
    expect(textContent!.length).toBeGreaterThan(0);

    // Verify no aria-hidden on code content
    const ariaHidden = await codeElement.getAttribute('aria-hidden');
    expect(ariaHidden).not.toBe('true');
  });

  test('should maintain readability at 200% zoom', async ({ page, testSnippet }) => {
    await page.goto(`/snippets/${testSnippet.id}`);
    await page.waitForLoadState('networkidle');

    await waitForSyntaxHighlighter(page);

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
});
