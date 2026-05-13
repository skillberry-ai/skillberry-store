// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test as base, expect } from '@playwright/test';

/**
 * Test fixtures for E2E tests
 * Provides reusable test data and helper functions
 */

export interface TestFixtures {
  testSkill: {
    id: string;
    name: string;
    cleanup: () => Promise<void>;
  };
  testSnippet: {
    id: string;
    name: string;
    cleanup: () => Promise<void>;
  };
}

const API_BASE = process.env.API_BASE_URL || 'http://localhost:8000';

export const test = base.extend<TestFixtures>({
  testSkill: async ({ request }, use) => {
    // Create a test skill with tools
    const skillResponse = await request.post(`${API_BASE}/api/skills/`, {
      data: {
        name: `E2E Test Skill ${Date.now()}`,
        description: 'A test skill for E2E testing',
        tags: ['test', 'e2e', 'syntax-highlighting'],
        tools: [
          {
            name: 'test_python_tool',
            description: 'A Python tool for testing syntax highlighting',
            programming_language: 'python',
            module: `def hello_world():
    """A simple test function"""
    print("Hello, World!")
    return True

def calculate_sum(a: int, b: int) -> int:
    """Calculate sum of two numbers"""
    result = a + b
    return result

class Calculator:
    """A simple calculator class"""
    
    def __init__(self):
        self.result = 0
    
    def add(self, value: int) -> int:
        """Add a value to the result"""
        self.result += value
        return self.result`,
            tags: ['python', 'test']
          }
        ],
        snippets: [
          {
            name: 'test_snippet_in_skill',
            description: 'A test snippet within the skill',
            content: `const greet = (name) => {
  console.log(\`Hello, \${name}!\`);
};

greet('World');`,
            content_type: 'text/javascript',
            tags: ['javascript', 'test']
          }
        ]
      }
    });

    let skillId = '';
    if (skillResponse.ok()) {
      const skill = await skillResponse.json();
      skillId = skill.id;
    } else {
      throw new Error(`Failed to create test skill: ${skillResponse.status()}`);
    }

    // Provide the skill data to the test
    await use({
      id: skillId,
      name: `E2E Test Skill ${Date.now()}`,
      cleanup: async () => {
        if (skillId) {
          await request.delete(`${API_BASE}/skills/${skillId}`);
        }
      }
    });

    // Cleanup after test
    if (skillId) {
      await request.delete(`${API_BASE}/api/skills/${skillId}`);
    }
  },

  testSnippet: async ({ request }, use) => {
    // Create a test snippet
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `E2E Test Snippet ${Date.now()}`,
        description: 'A test snippet for E2E testing',
        content: `def fibonacci(n):
    """Calculate Fibonacci number recursively"""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def factorial(n):
    """Calculate factorial"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Example usage
print(f"Fibonacci(10) = {fibonacci(10)}")
print(f"Factorial(5) = {factorial(5)}")`,
        content_type: 'text/x-python',
        tags: ['python', 'test', 'e2e', 'file:test.py']
      }
    });

    let snippetId = '';
    if (snippetResponse.ok()) {
      const snippet = await snippetResponse.json();
      snippetId = snippet.id;
    } else {
      throw new Error(`Failed to create test snippet: ${snippetResponse.status()}`);
    }

    // Provide the snippet data to the test
    await use({
      id: snippetId,
      name: `E2E Test Snippet ${Date.now()}`,
      cleanup: async () => {
        if (snippetId) {
          await request.delete(`${API_BASE}/snippets/${snippetId}`);
        }
      }
    });

    // Cleanup after test
    if (snippetId) {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  }
});

export { expect };

/**
 * Helper function to wait for syntax highlighter to render
 */
export async function waitForSyntaxHighlighter(page: any, timeout = 10000) {
  await page.waitForSelector('pre[class*="language-"]', { timeout });
}

/**
 * Helper function to get code content from syntax highlighter
 */
export async function getCodeContent(page: any) {
  const codeElement = page.locator('code[class*="language-"]');
  return await codeElement.textContent();
}

/**
 * Helper function to verify syntax highlighting is applied
 */
export async function verifySyntaxHighlighting(page: any, expectedLanguage?: string) {
  await waitForSyntaxHighlighter(page);
  
  const syntaxHighlighter = page.locator('pre[class*="language-"]');
  await expect(syntaxHighlighter).toBeVisible();
  
  if (expectedLanguage) {
    const codeElement = page.locator(`code[class*="language-${expectedLanguage}"]`);
    await expect(codeElement).toBeVisible();
  }
  
  // Verify line numbers are present
  const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
  const lineNumberCount = await lineNumbers.count();
  expect(lineNumberCount).toBeGreaterThan(0);
}

/**
 * Helper function to verify scrollable container
 */
export async function verifyScrollableContainer(page: any) {
  const codeContainer = page.locator('div').filter({
    has: page.locator('pre[class*="language-"]')
  }).first();
  
  const overflow = await codeContainer.evaluate((el) =>
    window.getComputedStyle(el).overflow
  );
  
  expect(overflow).toBe('auto');
}
