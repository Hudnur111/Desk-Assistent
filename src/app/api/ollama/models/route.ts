import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const ollamaUrl = req.nextUrl.searchParams.get('url') ?? 'http://localhost:11434';
  try {
    const res = await fetch(`${ollamaUrl}/api/tags`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return NextResponse.json({ models: [], error: 'Ollama unreachable' });
    const data = await res.json();
    const models = (data.models ?? []).map((m: { name: string }) => m.name);
    return NextResponse.json({ models });
  } catch {
    return NextResponse.json({ models: [], error: 'Ollama not running' });
  }
}
