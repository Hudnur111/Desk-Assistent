// MCP Tool Registry — foundation for Model Context Protocol

export interface MCPToolSchema {
  type: 'object';
  properties: Record<string, { type: string; description: string; required?: boolean }>;
  required?: string[];
}

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: MCPToolSchema;
  execute: (params: Record<string, unknown>) => Promise<unknown>;
}

class MCPRegistry {
  private tools = new Map<string, MCPTool>();

  register(tool: MCPTool) {
    this.tools.set(tool.name, tool);
  }

  get(name: string): MCPTool | undefined {
    return this.tools.get(name);
  }

  list(): MCPTool[] {
    return Array.from(this.tools.values());
  }

  async execute(name: string, params: Record<string, unknown>) {
    const tool = this.tools.get(name);
    if (!tool) throw new Error(`MCP Tool not found: ${name}`);
    return tool.execute(params);
  }

  toAnthropicTools() {
    return this.list().map((t) => ({
      name: t.name,
      description: t.description,
      input_schema: t.inputSchema,
    }));
  }
}

export const mcpRegistry = new MCPRegistry();

// Built-in tools
mcpRegistry.register({
  name: 'get_time',
  description: 'Get the current date and time',
  inputSchema: { type: 'object', properties: {}, required: [] },
  execute: async () => ({
    utc: new Date().toISOString(),
    local: new Date().toLocaleString('de-DE'),
  }),
});

mcpRegistry.register({
  name: 'get_system_info',
  description: 'Get Raspberry Pi system information',
  inputSchema: { type: 'object', properties: {}, required: [] },
  execute: async () => ({
    platform: typeof process !== 'undefined' ? process.platform : 'browser',
    arch: typeof process !== 'undefined' ? process.arch : 'unknown',
  }),
});
