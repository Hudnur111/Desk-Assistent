import { NextRequest, NextResponse } from 'next/server';

// MCP Tool Executor - foundation for future MCP server integration
const toolHandlers: Record<string, (params: Record<string, unknown>) => unknown> = {
  get_time: () => ({
    utc: new Date().toISOString(),
    local: new Date().toLocaleString('de-DE'),
    timestamp: Date.now(),
  }),

  github_sync: async () => {
    // Placeholder - actual sync via scripts/sync.sh
    return { status: 'ok', message: 'GitHub sync triggered via webhook', timestamp: Date.now() };
  },

  get_system_info: () => ({
    platform: process.platform,
    arch: process.arch,
    nodeVersion: process.version,
    memory: process.memoryUsage(),
  }),
};

export async function POST(req: NextRequest) {
  try {
    const { tool, params = {} } = await req.json();
    const handler = toolHandlers[tool];
    if (!handler) {
      return NextResponse.json({ error: `Unknown tool: ${tool}` }, { status: 404 });
    }
    const result = await handler(params as Record<string, unknown>);
    return NextResponse.json({ result });
  } catch (err: unknown) {
    return NextResponse.json({ error: err instanceof Error ? err.message : 'Tool error' }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    tools: Object.keys(toolHandlers).map((name) => ({
      name,
      description: getDescription(name),
    })),
  });
}

function getDescription(name: string) {
  const desc: Record<string, string> = {
    get_time: 'Get current date and time',
    github_sync: 'Sync with GitHub repository',
    get_system_info: 'Get system information',
  };
  return desc[name] ?? name;
}
