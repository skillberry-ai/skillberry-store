// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Utility functions for generating OpenAPI specifications from MCP server capabilities
 */

interface MCPTool {
  name: string;
  description?: string;
  inputSchema: any;
}

interface MCPPrompt {
  name: string;
  description?: string;
  arguments?: any[];
}

interface OpenAPISpec {
  openapi: string;
  info: {
    title: string;
    description: string;
    version: string;
  };
  servers: Array<{
    url: string;
    description: string;
  }>;
  paths: Record<string, any>;
  components: {
    schemas: Record<string, any>;
  };
}

/**
 * Recursively down-convert a JSON-Schema-2020-12 (MCP) schema to the
 * OpenAPI 3.0.x dialect so it validates under `openapi: 3.0.3`.
 * 
 * Key transformations:
 * - Sets `nullable: true` on any typed node that has `default: null`
 * - Converts array-form types like `type: ["string", "null"]` to single type with `nullable: true`
 * - Recursively processes nested objects and arrays
 */
function sanitizeFor30x(node: any): any {
  if (Array.isArray(node)) {
    return node.map(sanitizeFor30x);
  }
  
  if (node && typeof node === 'object') {
    const out: any = {};
    
    // Recursively process all properties
    for (const [k, v] of Object.entries(node)) {
      out[k] = sanitizeFor30x(v);
    }

    // Handle default: null - requires nullable: true in OpenAPI 3.0.x
    if (Object.prototype.hasOwnProperty.call(out, 'default') && out.default === null) {
      out.nullable = true;
    }
    
    // Handle array-form type (e.g., type: ["string", "null"])
    // OpenAPI 3.0.x doesn't support array types, convert to single type with nullable
    if (Array.isArray(out.type)) {
      const nonNullTypes = out.type.filter((t: string) => t !== 'null');
      if (out.type.includes('null')) {
        out.nullable = true;
      }
      // Use the first non-null type, or 'object' if only null was present
      out.type = nonNullTypes.length > 0 ? nonNullTypes[0] : 'object';
    }

    return out;
  }
  
  return node;
}

/**
 * Converts MCP tool input schema to OpenAPI request body schema
 */
function convertToolSchemaToOpenAPI(inputSchema: any): any {
  if (!inputSchema) {
    return {
      type: 'object',
      properties: {},
    };
  }

  // MCP tools use JSON Schema 2020-12 format, which needs to be converted
  // to OpenAPI 3.0.3 dialect for proper validation
  const sanitized = sanitizeFor30x(inputSchema);
  
  return {
    ...sanitized,
    // Ensure we have a type
    type: sanitized.type || 'object',
  };
}

/**
 * Converts MCP prompt arguments to OpenAPI parameters
 */
function convertPromptArgumentsToParameters(args?: any[]): any[] {
  if (!args || args.length === 0) {
    return [];
  }

  return args.map((arg) => ({
    name: arg.name,
    in: 'query',
    description: arg.description || `Argument: ${arg.name}`,
    required: arg.required || false,
    schema: {
      type: 'string', // MCP prompt arguments are typically strings
    },
  }));
}

/**
 * Generates an OpenAPI specification from MCP server tools and prompts
 */
export function generateOpenAPISpec(
  serverName: string,
  serverDescription: string,
  serverPort: number,
  tools: MCPTool[],
  prompts: MCPPrompt[]
): OpenAPISpec {
  const spec: OpenAPISpec = {
    openapi: '3.0.3',
    info: {
      title: `${serverName} - Virtual MCP Server API`,
      description: serverDescription || `OpenAPI specification for ${serverName} Virtual MCP Server`,
      version: '1.0.0',
    },
    servers: [
      {
        url: `http://localhost:${serverPort}`,
        description: 'Local Virtual MCP Server',
      },
    ],
    paths: {},
    components: {
      schemas: {},
    },
  };

  // Add tool endpoints
  tools.forEach((tool) => {
    const pathName = `/tools/${tool.name}`;
    const requestBodySchema = convertToolSchemaToOpenAPI(tool.inputSchema);
    
    // Store schema in components if it's complex
    const schemaName = `${tool.name}Request`;
    spec.components.schemas[schemaName] = requestBodySchema;

    spec.paths[pathName] = {
      post: {
        summary: tool.name,
        description: tool.description || `Execute the ${tool.name} tool`,
        operationId: `execute_${tool.name}`,
        tags: ['Tools'],
        requestBody: {
          required: true,
          content: {
            'application/json': {
              schema: {
                $ref: `#/components/schemas/${schemaName}`,
              },
            },
          },
        },
        responses: {
          '200': {
            description: 'Successful tool execution',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  properties: {
                    content: {
                      type: 'array',
                      items: {
                        type: 'object',
                        properties: {
                          type: {
                            type: 'string',
                            enum: ['text', 'image', 'resource'],
                          },
                          text: {
                            type: 'string',
                          },
                          data: {
                            type: 'string',
                          },
                          mimeType: {
                            type: 'string',
                          },
                        },
                      },
                    },
                    isError: {
                      type: 'boolean',
                    },
                  },
                },
              },
            },
          },
          '400': {
            description: 'Bad request - invalid input',
          },
          '500': {
            description: 'Internal server error',
          },
        },
      },
    };
  });

  // Add prompt endpoints
  prompts.forEach((prompt) => {
    const pathName = `/prompts/${prompt.name}`;
    const parameters = convertPromptArgumentsToParameters(prompt.arguments);

    spec.paths[pathName] = {
      get: {
        summary: prompt.name,
        description: prompt.description || `Get the ${prompt.name} prompt`,
        operationId: `get_${prompt.name}`,
        tags: ['Prompts'],
        parameters,
        responses: {
          '200': {
            description: 'Successful prompt retrieval',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  properties: {
                    description: {
                      type: 'string',
                    },
                    messages: {
                      type: 'array',
                      items: {
                        type: 'object',
                        properties: {
                          role: {
                            type: 'string',
                            enum: ['user', 'assistant'],
                          },
                          content: {
                            type: 'object',
                            properties: {
                              type: {
                                type: 'string',
                                enum: ['text', 'image', 'resource'],
                              },
                              text: {
                                type: 'string',
                              },
                              data: {
                                type: 'string',
                              },
                              mimeType: {
                                type: 'string',
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
          '400': {
            description: 'Bad request - invalid arguments',
          },
          '404': {
            description: 'Prompt not found',
          },
          '500': {
            description: 'Internal server error',
          },
        },
      },
    };
  });

  return spec;
}

/**
 * Downloads the OpenAPI specification as a JSON file
 */
export function downloadOpenAPISpec(spec: OpenAPISpec, filename: string): void {
  const jsonString = JSON.stringify(spec, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  
  // Cleanup
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
