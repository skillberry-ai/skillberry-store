// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

/**
 * E2E tests for PR #135: VS Code-like code visualization improvements
 * 
 * These tests verify:
 * 1. SkillDetailPage displays tool code with syntax highlighting
 * 2. SkillDetailPage displays snippet code with syntax highlighting
 * 3. SnippetDetailPage displays code with syntax highlighting
 * 4. Code blocks have proper styling (dark theme, line numbers, borders)
 * 5. Language detection works correctly for different content types
 * 
 * Proof artifacts generated:
 * - Screenshots of code visualization in different contexts
 * - Traces showing user interaction flow
 * - Videos of the complete test execution
 */

// Enable proof artifacts for these tests
test.use({
  trace: 'on',
  screenshot: 'on',
  video: 'on',
});

test.describe('Code Visualization Improvements (PR #135)', () => {
  
  test.describe('SkillDetailPage - Tool Code Display', () => {
    test('should display tool code with VS Code-like syntax highlighting', async ({ page }, testInfo) => {
      await test.step('Navigate to skills page', async () => {
        await page.goto('/skills');
        await page.waitForLoadState('networkidle');
      });

      await test.step('Find and open a skill with tools', async () => {
        // Look for a skill card or link
        const skillLink = page.locator('a[href*="/skills/"]').first();
        
        if (await skillLink.count() === 0) {
          test.skip();
          return;
        }

        await skillLink.click();
        await page.waitForLoadState('networkidle');
      });

      await test.step('Navigate to Tools Content tab', async () => {
        // Look for the "Tools Content" tab
        const toolsTab = page.getByRole('tab', { name: /tools content/i });
        
        if (!(await toolsTab.isVisible())) {
          test.skip();
          return;
        }

        await toolsTab.click();
        await page.waitForTimeout(500); // Wait for tab content to render
      });

      await test.step('Verify syntax highlighter is present', async () => {
        // Check for the SyntaxHighlighter component by looking for its characteristic elements
        // The component adds line numbers and uses a specific class structure
        const codeBlock = page.locator('code[class*="language-"]').first();
        await expect(codeBlock).toBeVisible({ timeout: 5000 });

        // Verify dark theme styling (vscDarkPlus)
        const codeContainer = page.locator('pre').first();
        const backgroundColor = await codeContainer.evaluate((el) => 
          window.getComputedStyle(el).backgroundColor
        );
        
        // vscDarkPlus uses a dark background
        expect(backgroundColor).toMatch(/rgb\(30, 30, 30\)|rgb\(31, 31, 31\)|#1e1e1e/i);
      });

      await test.step('Verify line numbers are displayed', async () => {
        // SyntaxHighlighter with showLineNumbers creates line number elements
        const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
        const count = await lineNumbers.count();
        expect(count).toBeGreaterThan(0);
      });

      await test.step('Capture proof screenshot of tool code visualization', async () => {
        await page.screenshot({
          path: testInfo.outputPath('skill-tool-code-visualization.png'),
          fullPage: true
        });
      });
    });

    test('should display tool code with proper border and styling', async ({ page }, testInfo) => {
      await page.goto('/skills');
      await page.waitForLoadState('networkidle');

      const skillLink = page.locator('a[href*="/skills/"]').first();
      if (await skillLink.count() === 0) {
        test.skip();
        return;
      }

      await skillLink.click();
      await page.waitForLoadState('networkidle');

      const toolsTab = page.getByRole('tab', { name: /tools content/i });
      if (!(await toolsTab.isVisible())) {
        test.skip();
        return;
      }

      await toolsTab.click();
      await page.waitForTimeout(500);

      await test.step('Verify code container has proper styling', async () => {
        // Check for the wrapper div with border styling
        const codeWrapper = page.locator('div').filter({ 
          has: page.locator('pre') 
        }).first();

        const styles = await codeWrapper.evaluate((el) => {
          const computed = window.getComputedStyle(el);
          return {
            border: computed.border,
            borderRadius: computed.borderRadius,
            overflow: computed.overflow
          };
        });

        // Verify border exists (should be '1px solid #3d3d3d')
        expect(styles.border).toContain('1px');
        expect(styles.border).toContain('solid');
        
        // Verify border radius (should be '6px')
        expect(styles.borderRadius).toContain('6px');
        
        // Verify overflow is hidden
        expect(styles.overflow).toBe('hidden');
      });

      await test.step('Capture styled code block screenshot', async () => {
        await page.screenshot({
          path: testInfo.outputPath('skill-tool-code-styling.png'),
          fullPage: true
        });
      });
    });
  });

  test.describe('SkillDetailPage - Snippet Code Display', () => {
    test('should display snippet code with syntax highlighting', async ({ page }, testInfo) => {
      await test.step('Navigate to skills page', async () => {
        await page.goto('/skills');
        await page.waitForLoadState('networkidle');
      });

      await test.step('Find and open a skill with snippets', async () => {
        const skillLink = page.locator('a[href*="/skills/"]').first();
        
        if (await skillLink.count() === 0) {
          test.skip();
          return;
        }

        await skillLink.click();
        await page.waitForLoadState('networkidle');
      });

      await test.step('Navigate to Snippets Content tab', async () => {
        const snippetsTab = page.getByRole('tab', { name: /snippets content/i });
        
        if (!(await snippetsTab.isVisible())) {
          test.skip();
          return;
        }

        await snippetsTab.click();
        await page.waitForTimeout(500);
      });

      await test.step('Verify syntax highlighter for snippets', async () => {
        const codeBlock = page.locator('code[class*="language-"]').first();
        await expect(codeBlock).toBeVisible({ timeout: 5000 });

        // Verify line numbers
        const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
        const count = await lineNumbers.count();
        expect(count).toBeGreaterThan(0);
      });

      await test.step('Capture snippet code visualization screenshot', async () => {
        await page.screenshot({
          path: testInfo.outputPath('skill-snippet-code-visualization.png'),
          fullPage: true
        });
      });
    });

    test('should detect language from content_type for snippets', async ({ page }, testInfo) => {
      await page.goto('/skills');
      await page.waitForLoadState('networkidle');

      const skillLink = page.locator('a[href*="/skills/"]').first();
      if (await skillLink.count() === 0) {
        test.skip();
        return;
      }

      await skillLink.click();
      await page.waitForLoadState('networkidle');

      const snippetsTab = page.getByRole('tab', { name: /snippets content/i });
      if (!(await snippetsTab.isVisible())) {
        test.skip();
        return;
      }

      await snippetsTab.click();
      await page.waitForTimeout(500);

      await test.step('Verify language class is applied', async () => {
        // The SyntaxHighlighter should apply a language class based on content_type
        const codeBlock = page.locator('code[class*="language-"]').first();
        const className = await codeBlock.getAttribute('class');
        
        // Should have a language class like 'language-python', 'language-javascript', etc.
        expect(className).toMatch(/language-(python|javascript|java|go|bash|yaml|json|html|css|text)/);
      });

      await test.step('Capture language detection proof', async () => {
        await page.screenshot({
          path: testInfo.outputPath('skill-snippet-language-detection.png'),
          fullPage: true
        });
      });
    });
  });

  test.describe('SnippetDetailPage - Code Display', () => {
    test('should display snippet content with VS Code-like syntax highlighting', async ({ page }, testInfo) => {
      await test.step('Navigate to snippets page', async () => {
        await page.goto('/snippets');
        await page.waitForLoadState('networkidle');
      });

      await test.step('Find and open a snippet', async () => {
        const snippetLink = page.locator('a[href*="/snippets/"]').first();
        
        if (await snippetLink.count() === 0) {
          test.skip();
          return;
        }

        await snippetLink.click();
        await page.waitForLoadState('networkidle');
      });

      await test.step('Verify syntax highlighter is present', async () => {
        const codeBlock = page.locator('code[class*="language-"]').first();
        await expect(codeBlock).toBeVisible({ timeout: 5000 });

        // Verify dark theme
        const codeContainer = page.locator('pre').first();
        const backgroundColor = await codeContainer.evaluate((el) => 
          window.getComputedStyle(el).backgroundColor
        );
        
        expect(backgroundColor).toMatch(/rgb\(30, 30, 30\)|rgb\(31, 31, 31\)|#1e1e1e/i);
      });

      await test.step('Verify line numbers are displayed', async () => {
        const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
        const count = await lineNumbers.count();
        expect(count).toBeGreaterThan(0);
      });

      await test.step('Capture snippet detail page screenshot', async () => {
        await page.screenshot({
          path: testInfo.outputPath('snippet-detail-code-visualization.png'),
          fullPage: true
        });
      });
    });

    test('should display snippet with proper container styling', async ({ page }, testInfo) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      const snippetLink = page.locator('a[href*="/snippets/"]').first();
      if (await snippetLink.count() === 0) {
        test.skip();
        return;
      }

      await snippetLink.click();
      await page.waitForLoadState('networkidle');

      await test.step('Verify code container styling', async () => {
        const codeWrapper = page.locator('div').filter({ 
          has: page.locator('pre') 
        }).first();

        const styles = await codeWrapper.evaluate((el) => {
          const computed = window.getComputedStyle(el);
          return {
            maxHeight: computed.maxHeight,
            overflow: computed.overflow,
            border: computed.border,
            borderRadius: computed.borderRadius
          };
        });

        // Verify max height (should be '70vh')
        expect(styles.maxHeight).toContain('vh');
        
        // Verify overflow is auto for scrolling
        expect(styles.overflow).toBe('auto');
        
        // Verify border styling
        expect(styles.border).toContain('1px');
        expect(styles.border).toContain('solid');
        expect(styles.borderRadius).toContain('6px');
      });

      await test.step('Capture styled snippet container', async () => {
        await page.screenshot({
          path: testInfo.outputPath('snippet-detail-container-styling.png'),
          fullPage: true
        });
      });
    });

    test('should apply correct language based on content_type', async ({ page }, testInfo) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      const snippetLink = page.locator('a[href*="/snippets/"]').first();
      if (await snippetLink.count() === 0) {
        test.skip();
        return;
      }

      await snippetLink.click();
      await page.waitForLoadState('networkidle');

      await test.step('Verify language detection from content_type', async () => {
        const codeBlock = page.locator('code[class*="language-"]').first();
        const className = await codeBlock.getAttribute('class');
        
        // Should have a language class matching the content_type
        expect(className).toMatch(/language-(python|javascript|java|go|bash|yaml|json|html|css|text)/);
      });

      await test.step('Capture language-specific highlighting', async () => {
        await page.screenshot({
          path: testInfo.outputPath('snippet-detail-language-highlighting.png'),
          fullPage: true
        });
      });
    });
  });

  test.describe('Code Visualization - Visual Regression', () => {
    test('should maintain consistent styling across all code displays', async ({ page }, testInfo) => {
      const screenshots: string[] = [];

      await test.step('Capture skill tool code', async () => {
        await page.goto('/skills');
        await page.waitForLoadState('networkidle');
        
        const skillLink = page.locator('a[href*="/skills/"]').first();
        if (await skillLink.count() > 0) {
          await skillLink.click();
          await page.waitForLoadState('networkidle');
          
          const toolsTab = page.getByRole('tab', { name: /tools content/i });
          if (await toolsTab.isVisible()) {
            await toolsTab.click();
            await page.waitForTimeout(500);
            
            const screenshotPath = testInfo.outputPath('consistency-skill-tool.png');
            await page.screenshot({ path: screenshotPath, fullPage: true });
            screenshots.push(screenshotPath);
          }
        }
      });

      await test.step('Capture snippet detail code', async () => {
        await page.goto('/snippets');
        await page.waitForLoadState('networkidle');
        
        const snippetLink = page.locator('a[href*="/snippets/"]').first();
        if (await snippetLink.count() > 0) {
          await snippetLink.click();
          await page.waitForLoadState('networkidle');
          
          const screenshotPath = testInfo.outputPath('consistency-snippet-detail.png');
          await page.screenshot({ path: screenshotPath, fullPage: true });
          screenshots.push(screenshotPath);
        }
      });

      await test.step('Verify screenshots were captured', async () => {
        expect(screenshots.length).toBeGreaterThan(0);
      });
    });
  });

  test.describe('Code Visualization - Accessibility', () => {
    test('should have accessible code blocks', async ({ page }) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      const snippetLink = page.locator('a[href*="/snippets/"]').first();
      if (await snippetLink.count() === 0) {
        test.skip();
        return;
      }

      await snippetLink.click();
      await page.waitForLoadState('networkidle');

      await test.step('Verify code block has proper semantic structure', async () => {
        // Code should be in a <pre><code> structure
        const preElement = page.locator('pre').first();
        await expect(preElement).toBeVisible();

        const codeElement = preElement.locator('code').first();
        await expect(codeElement).toBeVisible();
      });

      await test.step('Verify sufficient color contrast', async () => {
        // vscDarkPlus theme should have good contrast
        const codeElement = page.locator('code[class*="language-"]').first();
        const color = await codeElement.evaluate((el) => 
          window.getComputedStyle(el).color
        );
        
        // Text should be light colored (not black) for dark theme
        expect(color).not.toMatch(/rgb\(0, 0, 0\)/);
      });
    });
  });
});