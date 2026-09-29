import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

interface ChatMessage { role: string; content: string; }

async function streamOllama(model: string, messages: ChatMessage[], ollamaUrl: string): Promise<ReadableStream> {
  const res = await fetch(`${ollamaUrl}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, messages, stream: true }),
  });

  if (!res.ok) throw new Error(`Ollama error: ${res.statusText}`);

  const encoder = new TextEncoder();
  return new ReadableStream({
    async start(controller) {
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const lines = decoder.decode(value).split('\n').filter(Boolean);
          for (const line of lines) {
            try {
              const json = JSON.parse(line);
              const token = json.message?.content ?? '';
              if (token) controller.enqueue(encoder.encode(token));
              if (json.done) { controller.close(); return; }
            } catch { /* skip malformed */ }
          }
        }
      } catch (e) {
        controller.error(e);
      } finally {
        controller.close();
      }
    },
  });
}

async function streamClaude(model: string, messages: ChatMessage[], apiKey: string): Promise<ReadableStream> {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model,
      max_tokens: 4096,
      stream: true,
      system: 'You are Desk Assistant, a helpful AI running on Raspberry Pi. Be concise and helpful.',
      messages: messages.filter((m) => m.role !== 'system'),
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Claude error: ${err}`);
  }

  const encoder = new TextEncoder();
  return new ReadableStream({
    async start(controller) {
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const lines = decoder.decode(value).split('\n').filter(Boolean);
          for (const line of lines) {
            if (!line.startsWith('data:')) continue;
            const data = line.slice(5).trim();
            if (data === '[DONE]') { controller.close(); return; }
            try {
              const json = JSON.parse(data);
              if (json.type === 'content_block_delta') {
                const token = json.delta?.text ?? '';
                if (token) controller.enqueue(encoder.encode(token));
              }
              if (json.type === 'message_stop') { controller.close(); return; }
            } catch { /* skip */ }
          }
        }
      } catch (e) {
        controller.error(e);
      } finally {
        controller.close();
      }
    },
  });
}

export async function POST(req: NextRequest) {
  try {
    const { provider, model, messages, ollamaUrl, apiKey } = await req.json();

    let stream: ReadableStream;
    if (provider === 'ollama') {
      stream = await streamOllama(model, messages, ollamaUrl ?? 'http://localhost:11434');
    } else {
      if (!apiKey) return NextResponse.json({ error: 'Claude API key missing' }, { status: 401 });
      stream = await streamClaude(model, messages, apiKey);
    }

    return new NextResponse(stream, {
      headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Transfer-Encoding': 'chunked' },
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
