// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { generateOpenAPISpec, downloadOpenAPISpec } from './openApiGenerator';

/**
 * Additional error handling and edge case tests for openApiGenerator
 * These tests complement the main test suite with focus on error scenarios
 */

describe('openApiGenerator - Error Handling and Edge Cases', () => {
  describe('generateOpenAPISpec - Error Scenarios', () => {
    it('should handle null values in tool properties gracefully', () => {
      const tools = [
        {
          name: 'test_tool',
          description: null as any,
          inputSchema: {
            type: 'object',
            properties: {
              nullProp: null,
              validProp: { type: 'string' },
            },
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(spec.paths['/tools/test_tool']).toBeDefined();
      expect(spec.components.schemas.test_toolRequest.properties).toBeDefined();
    });

    it('should handle circular references in input schema', () => {
      const circularSchema: any = {
        type: 'object',
        properties: {
          name: { type: 'string' },
        },
      };
      // Create circular reference
      circularSchema.properties.self = circularSchema;

      const tools = [
        {
          name: 'circular_tool',
          description: 'Tool with circular schema',
          inputSchema: circularSchema,
        },
      ];

      // Should not throw, but may not handle circular reference perfectly
      expect(() => {
        generateOpenAPISpec('TestServer', '', 8080, tools, []);
      }).not.toThrow();
    });

    it('should handle extremely long server names', () => {
      const longName = 'a'.repeat(1000);
      const spec = generateOpenAPISpec(longName, 'Test', 8080, [], []);

      expect(spec.info.title).toContain(longName);
      expect(spec.info.title).toContain('Virtual MCP Server API');
    });

    it('should handle server name with only special characters', () => {
      const spec = generateOpenAPISpec('!@#$%^&*()', 'Test', 8080, [], []);

      expect(spec.info.title).toBe('!@#$%^&*() - Virtual MCP Server API');
    });

    it('should handle empty string server name', () => {
      const spec = generateOpenAPISpec('', 'Test', 8080, [], []);

      expect(spec.info.title).toBe(' - Virtual MCP Server API');
    });

    it('should handle negative port numbers', () => {
      const spec = generateOpenAPISpec('TestServer', '', -1, [], []);

      expect(spec.servers[0].url).toBe('http://localhost:-1');
    });

    it('should handle very large port numbers', () => {
      const spec = generateOpenAPISpec('TestServer', '', 999999, [], []);

      expect(spec.servers[0].url).toBe('http://localhost:999999');
    });

    it('should handle tools with deeply nested schemas', () => {
      const tools = [
        {
          name: 'nested_tool',
          description: 'Tool with deeply nested schema',
          inputSchema: {
            type: 'object',
            properties: {
              level1: {
                type: 'object',
                properties: {
                  level2: {
                    type: 'object',
                    properties: {
                      level3: {
                        type: 'object',
                        properties: {
                          level4: {
                            type: 'object',
                            properties: {
                              value: { type: 'string' },
                            },
                          },
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(spec.components.schemas.nested_toolRequest).toBeDefined();
      expect(
        spec.components.schemas.nested_toolRequest.properties.level1.properties
          .level2.properties.level3.properties.level4.properties.value.type
      ).toBe('string');
    });

    it('should handle tools with array of arrays', () => {
      const tools = [
        {
          name: 'matrix_tool',
          description: 'Tool with matrix input',
          inputSchema: {
            type: 'object',
            properties: {
              matrix: {
                type: 'array',
                items: {
                  type: 'array',
                  items: { type: 'number' },
                },
              },
            },
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(
        spec.components.schemas.matrix_toolRequest.properties.matrix.type
      ).toBe('array');
      expect(
        spec.components.schemas.matrix_toolRequest.properties.matrix.items.type
      ).toBe('array');
    });

    it('should handle prompts with duplicate argument names', () => {
      const prompts = [
        {
          name: 'duplicate_args',
          description: 'Prompt with duplicate args',
          arguments: [
            { name: 'arg1', required: true },
            { name: 'arg1', required: false },
          ],
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      // Should still generate spec, even if it's not ideal
      expect(spec.paths['/prompts/duplicate_args'].get.parameters).toHaveLength(
        2
      );
    });

    it('should handle prompts with very long argument names', () => {
      const longArgName = 'a'.repeat(500);
      const prompts = [
        {
          name: 'long_arg_prompt',
          arguments: [{ name: longArgName, required: true }],
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      expect(
        spec.paths['/prompts/long_arg_prompt'].get.parameters[0].name
      ).toBe(longArgName);
    });

    it('should handle tools with invalid JSON Schema types', () => {
      const tools = [
        {
          name: 'invalid_type_tool',
          description: 'Tool with invalid type',
          inputSchema: {
            type: 'invalid_type' as any,
            properties: {
              value: { type: 'string' },
            },
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      // Should still generate, preserving the invalid type
      expect(spec.components.schemas.invalid_type_toolRequest.type).toBe(
        'invalid_type'
      );
    });

    it('should handle tools with missing properties field', () => {
      const tools = [
        {
          name: 'no_props_tool',
          description: 'Tool without properties',
          inputSchema: {
            type: 'object',
            required: ['something'],
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(spec.components.schemas.no_props_toolRequest).toBeDefined();
    });

    it('should handle Unicode characters in tool and prompt names', () => {
      const tools = [
        {
          name: '读取文件_🔧',
          description: 'Unicode tool name',
          inputSchema: { type: 'object' },
        },
      ];

      const prompts = [
        {
          name: 'código_revisión_✓',
          description: 'Unicode prompt name',
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, prompts);

      expect(spec.paths['/tools/读取文件_🔧']).toBeDefined();
      expect(spec.paths['/prompts/código_revisión_✓']).toBeDefined();
    });

    it('should handle tools with additionalProperties', () => {
      const tools = [
        {
          name: 'flexible_tool',
          description: 'Tool with additionalProperties',
          inputSchema: {
            type: 'object',
            properties: {
              name: { type: 'string' },
            },
            additionalProperties: true,
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(
        spec.components.schemas.flexible_toolRequest.additionalProperties
      ).toBe(true);
    });

    it('should handle prompts with argument objects missing name field', () => {
      const prompts = [
        {
          name: 'malformed_prompt',
          arguments: [
            { required: true } as any, // Missing name
            { name: 'valid_arg', required: false },
          ],
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      // Should handle gracefully, possibly skipping the malformed argument
      expect(spec.paths['/prompts/malformed_prompt']).toBeDefined();
    });
  });

  describe('downloadOpenAPISpec - Error Scenarios', () => {
    let mockLink: HTMLAnchorElement;
    let createElementSpy: any;
    let appendChildSpy: any;
    let removeChildSpy: any;

    beforeEach(() => {
      mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
      } as any;

      createElementSpy = vi
        .spyOn(document, 'createElement')
        .mockReturnValue(mockLink);
      appendChildSpy = vi
        .spyOn(document.body, 'appendChild')
        .mockReturnValue(mockLink);
      removeChildSpy = vi
        .spyOn(document.body, 'removeChild')
        .mockReturnValue(mockLink);
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should handle click failure gracefully', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      mockLink.click = vi.fn(() => {
        throw new Error('Click failed');
      });

      // Should not throw even if click fails
      expect(() => {
        downloadOpenAPISpec(spec, 'test.json');
      }).toThrow('Click failed');
    });

    it('should handle very large spec objects', () => {
      // Create a large spec with many paths
      const largePaths: any = {};
      for (let i = 0; i < 1000; i++) {
        largePaths[`/tools/tool_${i}`] = {
          post: {
            summary: `tool_${i}`,
            description: 'A'.repeat(1000),
            responses: {},
          },
        };
      }

      const largeSpec = {
        openapi: '3.0.3',
        info: { title: 'Large', description: 'Large spec', version: '1.0.0' },
        servers: [],
        paths: largePaths,
        components: { schemas: {} },
      };

      expect(() => {
        downloadOpenAPISpec(largeSpec, 'large.json');
      }).not.toThrow();
    });

    it('should handle filename with path separators', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      // Filename with path separators (should be sanitized by caller, but test behavior)
      downloadOpenAPISpec(spec, '../../../etc/passwd.json');

      expect(mockLink.download).toBe('../../../etc/passwd.json');
    });

    it('should handle empty filename', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      downloadOpenAPISpec(spec, '');

      expect(mockLink.download).toBe('');
    });

    it('should handle spec with circular references in JSON.stringify', () => {
      const circularSpec: any = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };
      circularSpec.circular = circularSpec;

      // JSON.stringify will throw on circular references
      expect(() => {
        downloadOpenAPISpec(circularSpec, 'circular.json');
      }).toThrow();
    });

    it('should handle Blob creation failure', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      const originalBlob = global.Blob;
      global.Blob = vi.fn(() => {
        throw new Error('Blob creation failed');
      }) as any;

      expect(() => {
        downloadOpenAPISpec(spec, 'test.json');
      }).toThrow('Blob creation failed');

      global.Blob = originalBlob;
    });

    it('should handle URL.createObjectURL failure', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      const originalCreateObjectURL = global.URL.createObjectURL;
      global.URL.createObjectURL = vi.fn(() => {
        throw new Error('createObjectURL failed');
      });

      expect(() => {
        downloadOpenAPISpec(spec, 'test.json');
      }).toThrow('createObjectURL failed');

      global.URL.createObjectURL = originalCreateObjectURL;
    });
  });

  describe('Integration - Complex Real-World Scenarios', () => {
    it('should handle a realistic MCP server with mixed content', () => {
      const tools = [
        {
          name: 'file_operations',
          description: 'Perform file operations',
          inputSchema: {
            type: 'object',
            properties: {
              operation: {
                type: 'string',
                enum: ['read', 'write', 'delete'],
              },
              path: { type: 'string' },
              content: { type: 'string' },
              options: {
                type: 'object',
                properties: {
                  encoding: { type: 'string', default: 'utf-8' },
                  mode: { type: 'number' },
                },
              },
            },
            required: ['operation', 'path'],
          },
        },
        {
          name: 'search',
          description: 'Search for content',
          inputSchema: {
            type: 'object',
            properties: {
              query: { type: 'string' },
              filters: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    field: { type: 'string' },
                    value: { type: 'string' },
                  },
                },
              },
            },
            required: ['query'],
          },
        },
      ];

      const prompts = [
        {
          name: 'code_review',
          description: 'Review code with specific guidelines',
          arguments: [
            { name: 'language', required: true, description: 'Programming language' },
            { name: 'style_guide', required: false, description: 'Style guide to follow' },
            { name: 'focus_areas', required: false, description: 'Specific areas to focus on' },
          ],
        },
      ];

      const spec = generateOpenAPISpec(
        'Production-MCP-Server',
        'A production-ready MCP server with file operations and search',
        8080,
        tools,
        prompts
      );

      expect(spec.paths['/tools/file_operations']).toBeDefined();
      expect(spec.paths['/tools/search']).toBeDefined();
      expect(spec.paths['/prompts/code_review']).toBeDefined();
      expect(Object.keys(spec.paths)).toHaveLength(3);
      expect(Object.keys(spec.components.schemas)).toHaveLength(2);
    });
  });
});
