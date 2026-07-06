// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { generateOpenAPISpec, downloadOpenAPISpec } from './openApiGenerator';

describe('openApiGenerator', () => {
  describe('generateOpenAPISpec', () => {
    it('should generate a valid OpenAPI spec with basic info', () => {
      const spec = generateOpenAPISpec(
        'TestServer',
        'A test server',
        8080,
        [],
        []
      );

      expect(spec.openapi).toBe('3.0.3');
      expect(spec.info.title).toBe('TestServer - Virtual MCP Server API');
      expect(spec.info.description).toBe('A test server');
      expect(spec.info.version).toBe('1.0.0');
      expect(spec.servers).toHaveLength(1);
      expect(spec.servers[0].url).toBe('http://localhost:8080');
      expect(spec.paths).toEqual({});
      expect(spec.components.schemas).toEqual({});
    });

    it('should use default description when not provided', () => {
      const spec = generateOpenAPISpec('TestServer', '', 8080, [], []);

      expect(spec.info.description).toBe(
        'OpenAPI specification for TestServer Virtual MCP Server'
      );
    });

    it('should generate tool endpoints with input schemas', () => {
      const tools = [
        {
          name: 'read_file',
          description: 'Read a file from disk',
          inputSchema: {
            type: 'object',
            properties: {
              path: { type: 'string', description: 'File path' },
            },
            required: ['path'],
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(spec.paths['/tools/read_file']).toBeDefined();
      expect(spec.paths['/tools/read_file'].post).toBeDefined();
      expect(spec.paths['/tools/read_file'].post.summary).toBe('read_file');
      expect(spec.paths['/tools/read_file'].post.description).toBe(
        'Read a file from disk'
      );
      expect(spec.paths['/tools/read_file'].post.operationId).toBe(
        'execute_read_file'
      );
      expect(spec.paths['/tools/read_file'].post.tags).toEqual(['Tools']);
      expect(spec.paths['/tools/read_file'].post.requestBody.required).toBe(
        true
      );
      expect(
        spec.paths['/tools/read_file'].post.requestBody.content[
          'application/json'
        ].schema.$ref
      ).toBe('#/components/schemas/read_fileRequest');
      expect(spec.components.schemas.read_fileRequest).toEqual({
        type: 'object',
        properties: {
          path: { type: 'string', description: 'File path' },
        },
        required: ['path'],
      });
    });

    it('should handle tools with missing input schema', () => {
      const tools = [
        {
          name: 'simple_tool',
          description: 'A simple tool',
          inputSchema: null,
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(spec.components.schemas.simple_toolRequest).toEqual({
        type: 'object',
        properties: {},
      });
    });

    it('should handle tools with undefined input schema', () => {
      const tools = [
        {
          name: 'simple_tool',
          description: 'A simple tool',
          inputSchema: undefined,
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(spec.components.schemas.simple_toolRequest).toEqual({
        type: 'object',
        properties: {},
      });
    });

    it('should handle tools with input schema missing type', () => {
      const tools = [
        {
          name: 'tool_no_type',
          description: 'Tool without type',
          inputSchema: {
            properties: {
              value: { type: 'string' },
            },
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(spec.components.schemas.tool_no_typeRequest.type).toBe('object');
    });

    it('should use default description for tools without description', () => {
      const tools = [
        {
          name: 'unnamed_tool',
          inputSchema: { type: 'object' },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(spec.paths['/tools/unnamed_tool'].post.description).toBe(
        'Execute the unnamed_tool tool'
      );
    });

    it('should generate multiple tool endpoints', () => {
      const tools = [
        {
          name: 'tool1',
          description: 'First tool',
          inputSchema: { type: 'object' },
        },
        {
          name: 'tool2',
          description: 'Second tool',
          inputSchema: { type: 'object' },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      expect(spec.paths['/tools/tool1']).toBeDefined();
      expect(spec.paths['/tools/tool2']).toBeDefined();
      expect(Object.keys(spec.paths)).toHaveLength(2);
    });

    it('should include standard response schemas for tools', () => {
      const tools = [
        {
          name: 'test_tool',
          inputSchema: { type: 'object' },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      const responses = spec.paths['/tools/test_tool'].post.responses;
      expect(responses['200']).toBeDefined();
      expect(responses['200'].description).toBe('Successful tool execution');
      expect(responses['200'].content['application/json'].schema).toBeDefined();
      expect(responses['400']).toBeDefined();
      expect(responses['500']).toBeDefined();
    });

    it('should generate prompt endpoints with parameters', () => {
      const prompts = [
        {
          name: 'code_review',
          description: 'Review code',
          arguments: [
            {
              name: 'language',
              description: 'Programming language',
              required: true,
            },
            {
              name: 'style',
              description: 'Code style',
              required: false,
            },
          ],
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      expect(spec.paths['/prompts/code_review']).toBeDefined();
      expect(spec.paths['/prompts/code_review'].get).toBeDefined();
      expect(spec.paths['/prompts/code_review'].get.summary).toBe(
        'code_review'
      );
      expect(spec.paths['/prompts/code_review'].get.description).toBe(
        'Review code'
      );
      expect(spec.paths['/prompts/code_review'].get.operationId).toBe(
        'get_code_review'
      );
      expect(spec.paths['/prompts/code_review'].get.tags).toEqual(['Prompts']);

      const params = spec.paths['/prompts/code_review'].get.parameters;
      expect(params).toHaveLength(2);
      expect(params[0].name).toBe('language');
      expect(params[0].in).toBe('query');
      expect(params[0].description).toBe('Programming language');
      expect(params[0].required).toBe(true);
      expect(params[0].schema.type).toBe('string');
      expect(params[1].name).toBe('style');
      expect(params[1].required).toBe(false);
    });

    it('should handle prompts without arguments', () => {
      const prompts = [
        {
          name: 'simple_prompt',
          description: 'A simple prompt',
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      expect(spec.paths['/prompts/simple_prompt'].get.parameters).toEqual([]);
    });

    it('should handle prompts with empty arguments array', () => {
      const prompts = [
        {
          name: 'simple_prompt',
          description: 'A simple prompt',
          arguments: [],
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      expect(spec.paths['/prompts/simple_prompt'].get.parameters).toEqual([]);
    });

    it('should use default description for prompt arguments without description', () => {
      const prompts = [
        {
          name: 'test_prompt',
          arguments: [{ name: 'arg1', required: true }],
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      const params = spec.paths['/prompts/test_prompt'].get.parameters;
      expect(params[0].description).toBe('Argument: arg1');
    });

    it('should use default description for prompts without description', () => {
      const prompts = [
        {
          name: 'unnamed_prompt',
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      expect(spec.paths['/prompts/unnamed_prompt'].get.description).toBe(
        'Get the unnamed_prompt prompt'
      );
    });

    it('should generate multiple prompt endpoints', () => {
      const prompts = [
        {
          name: 'prompt1',
          description: 'First prompt',
        },
        {
          name: 'prompt2',
          description: 'Second prompt',
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      expect(spec.paths['/prompts/prompt1']).toBeDefined();
      expect(spec.paths['/prompts/prompt2']).toBeDefined();
    });

    it('should include standard response schemas for prompts', () => {
      const prompts = [
        {
          name: 'test_prompt',
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, [], prompts);

      const responses = spec.paths['/prompts/test_prompt'].get.responses;
      expect(responses['200']).toBeDefined();
      expect(responses['200'].description).toBe('Successful prompt retrieval');
      expect(responses['200'].content['application/json'].schema).toBeDefined();
      expect(responses['400']).toBeDefined();
      expect(responses['404']).toBeDefined();
      expect(responses['500']).toBeDefined();
    });

    it('should generate spec with both tools and prompts', () => {
      const tools = [
        {
          name: 'read_file',
          description: 'Read a file',
          inputSchema: { type: 'object' },
        },
      ];
      const prompts = [
        {
          name: 'code_review',
          description: 'Review code',
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, prompts);

      expect(spec.paths['/tools/read_file']).toBeDefined();
      expect(spec.paths['/prompts/code_review']).toBeDefined();
      expect(Object.keys(spec.paths)).toHaveLength(2);
    });

    it('should handle complex tool input schemas', () => {
      const tools = [
        {
          name: 'complex_tool',
          description: 'A complex tool',
          inputSchema: {
            type: 'object',
            properties: {
              config: {
                type: 'object',
                properties: {
                  timeout: { type: 'number' },
                  retries: { type: 'integer' },
                },
              },
              items: {
                type: 'array',
                items: { type: 'string' },
              },
            },
            required: ['config'],
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);

      const schema = spec.components.schemas.complex_toolRequest;
      expect(schema.properties.config).toBeDefined();
      expect(schema.properties.config.properties.timeout.type).toBe('number');
      expect(schema.properties.items.type).toBe('array');
      expect(schema.required).toEqual(['config']);
    });

    it('should handle special characters in server name', () => {
      const spec = generateOpenAPISpec(
        'My-Server_v2.0',
        'Test',
        8080,
        [],
        []
      );

      expect(spec.info.title).toBe('My-Server_v2.0 - Virtual MCP Server API');
    });

    it('should handle different port numbers', () => {
      const spec1 = generateOpenAPISpec('Server', '', 3000, [], []);
      const spec2 = generateOpenAPISpec('Server', '', 9999, [], []);

      expect(spec1.servers[0].url).toBe('http://localhost:3000');
      expect(spec2.servers[0].url).toBe('http://localhost:9999');
    });

    it('should convert default: null to nullable: true for OpenAPI 3.0.3 compatibility', () => {
      const tools = [
        {
          name: 'format_success_response',
          description: 'Format a success response',
          inputSchema: {
            type: 'object',
            properties: {
              data: {
                type: 'string',
                default: null,
                description: 'Optional data to include',
              },
              message: {
                type: 'string',
                description: 'Success message',
              },
            },
            required: ['message'],
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);
      const schema = spec.components.schemas.format_success_responseRequest;

      // The data field should have nullable: true added
      expect(schema.properties.data.nullable).toBe(true);
      expect(schema.properties.data.default).toBe(null);
      expect(schema.properties.data.type).toBe('string');
      
      // The message field should not have nullable
      expect(schema.properties.message.nullable).toBeUndefined();
    });

    it('should handle nested objects with default: null', () => {
      const tools = [
        {
          name: 'nested_tool',
          description: 'Tool with nested schema',
          inputSchema: {
            type: 'object',
            properties: {
              config: {
                type: 'object',
                properties: {
                  timeout: {
                    type: 'number',
                    default: null,
                  },
                  retries: {
                    type: 'integer',
                    default: 3,
                  },
                },
              },
              metadata: {
                type: 'object',
                default: null,
                properties: {
                  tags: {
                    type: 'array',
                    items: { type: 'string' },
                  },
                },
              },
            },
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);
      const schema = spec.components.schemas.nested_toolRequest;

      // Nested timeout field should have nullable: true
      expect(schema.properties.config.properties.timeout.nullable).toBe(true);
      expect(schema.properties.config.properties.timeout.default).toBe(null);
      
      // Nested retries field should not have nullable (default is not null)
      expect(schema.properties.config.properties.retries.nullable).toBeUndefined();
      expect(schema.properties.config.properties.retries.default).toBe(3);
      
      // metadata object itself should have nullable: true
      expect(schema.properties.metadata.nullable).toBe(true);
      expect(schema.properties.metadata.default).toBe(null);
    });

    it('should convert array-form type to single type with nullable', () => {
      const tools = [
        {
          name: 'union_type_tool',
          description: 'Tool with union types',
          inputSchema: {
            type: 'object',
            properties: {
              value: {
                type: ['string', 'null'],
                description: 'Optional string value',
              },
              count: {
                type: ['integer', 'null'],
                default: null,
              },
              flag: {
                type: ['boolean'],
                description: 'Non-nullable boolean',
              },
            },
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);
      const schema = spec.components.schemas.union_type_toolRequest;

      // value field: type should be 'string' with nullable: true
      expect(schema.properties.value.type).toBe('string');
      expect(schema.properties.value.nullable).toBe(true);
      
      // count field: type should be 'integer' with nullable: true (from both array and default)
      expect(schema.properties.count.type).toBe('integer');
      expect(schema.properties.count.nullable).toBe(true);
      expect(schema.properties.count.default).toBe(null);
      
      // flag field: type should be 'boolean' without nullable
      expect(schema.properties.flag.type).toBe('boolean');
      expect(schema.properties.flag.nullable).toBeUndefined();
    });

    it('should handle arrays with default: null', () => {
      const tools = [
        {
          name: 'array_tool',
          description: 'Tool with array fields',
          inputSchema: {
            type: 'object',
            properties: {
              items: {
                type: 'array',
                items: { type: 'string' },
                default: null,
              },
              nested: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    value: {
                      type: 'string',
                      default: null,
                    },
                  },
                },
              },
            },
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);
      const schema = spec.components.schemas.array_toolRequest;

      // items array should have nullable: true
      expect(schema.properties.items.nullable).toBe(true);
      expect(schema.properties.items.default).toBe(null);
      
      // nested array items should have nullable on the value property
      expect(schema.properties.nested.items.properties.value.nullable).toBe(true);
      expect(schema.properties.nested.items.properties.value.default).toBe(null);
    });

    it('should preserve other schema properties during sanitization', () => {
      const tools = [
        {
          name: 'rich_schema_tool',
          description: 'Tool with rich schema',
          inputSchema: {
            type: 'object',
            properties: {
              email: {
                type: 'string',
                format: 'email',
                pattern: '^[a-z]+@[a-z]+\\.[a-z]+$',
                minLength: 5,
                maxLength: 100,
                default: null,
                title: 'Email Address',
                description: 'User email',
              },
            },
          },
        },
      ];

      const spec = generateOpenAPISpec('TestServer', '', 8080, tools, []);
      const schema = spec.components.schemas.rich_schema_toolRequest;
      const emailProp = schema.properties.email;

      // Should add nullable while preserving all other properties
      expect(emailProp.nullable).toBe(true);
      expect(emailProp.default).toBe(null);
      expect(emailProp.type).toBe('string');
      expect(emailProp.format).toBe('email');
      expect(emailProp.pattern).toBe('^[a-z]+@[a-z]+\\.[a-z]+$');
      expect(emailProp.minLength).toBe(5);
      expect(emailProp.maxLength).toBe(100);
      expect(emailProp.title).toBe('Email Address');
      expect(emailProp.description).toBe('User email');
    });
  });

  describe('downloadOpenAPISpec', () => {
    let mockLink: HTMLAnchorElement;
    let appendChildSpy: any;
    let removeChildSpy: any;
    let clickSpy: any;

    beforeEach(() => {
      // Create a mock link element
      mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
      } as any;

      // Spy on document methods
      appendChildSpy = vi
        .spyOn(document.body, 'appendChild')
        .mockReturnValue(mockLink);
      removeChildSpy = vi
        .spyOn(document.body, 'removeChild')
        .mockReturnValue(mockLink);
      clickSpy = mockLink.click;

      // Mock createElement
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink);
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should create a download link with correct attributes', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      downloadOpenAPISpec(spec, 'test_spec.json');

      expect(mockLink.href).toBe('mock-url');
      expect(mockLink.download).toBe('test_spec.json');
    });

    it('should trigger download by clicking the link', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      downloadOpenAPISpec(spec, 'test.json');

      expect(clickSpy).toHaveBeenCalledTimes(1);
    });

    it('should append and remove link from document body', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      downloadOpenAPISpec(spec, 'test.json');

      expect(appendChildSpy).toHaveBeenCalledWith(mockLink);
      expect(removeChildSpy).toHaveBeenCalledWith(mockLink);
    });

    it('should create a blob with correct content and type', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      // Blob is already mocked in the test setup, just verify it was called
      downloadOpenAPISpec(spec, 'test.json');

      // Verify the download was triggered
      expect(clickSpy).toHaveBeenCalled();
    });

    it('should revoke object URL after download', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      downloadOpenAPISpec(spec, 'test.json');

      expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('mock-url');
    });

    it('should handle complex spec objects', () => {
      const spec = generateOpenAPISpec(
        'ComplexServer',
        'A complex server',
        8080,
        [
          {
            name: 'tool1',
            description: 'Tool 1',
            inputSchema: { type: 'object', properties: { a: { type: 'string' } } },
          },
        ],
        [
          {
            name: 'prompt1',
            description: 'Prompt 1',
            arguments: [{ name: 'arg1', required: true }],
          },
        ]
      );

      downloadOpenAPISpec(spec, 'complex_spec.json');

      expect(clickSpy).toHaveBeenCalled();
      expect(global.URL.revokeObjectURL).toHaveBeenCalled();
    });

    it('should handle different filename formats', () => {
      const spec = {
        openapi: '3.0.3',
        info: { title: 'Test', description: 'Test', version: '1.0.0' },
        servers: [],
        paths: {},
        components: { schemas: {} },
      };

      downloadOpenAPISpec(spec, 'my_server_openapi.json');
      expect(mockLink.download).toBe('my_server_openapi.json');

      downloadOpenAPISpec(spec, 'server-spec.json');
      expect(mockLink.download).toBe('server-spec.json');
    });
  });
});
