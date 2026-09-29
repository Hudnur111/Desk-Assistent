'use client';
import { useAppStore, Message } from '@/stores/appStore';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Square, Copy, Check, RotateCcw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

export function ChatPanel() {
  const {
    conversations, activeConversationId, createConversation, setActiveConversation,
    addMessage, updateLastMessage, activeProvider, ollamaModel, claudeModel, ollamaUrl, claudeApiKey,
  } = useAppStore();

  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const conv = conversations.find((c) => c.id === activeConversationId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conv?.messages]);

  const autoResize = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
  };

  const send = useCallback(async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || streaming) return;

    let convId = activeConversationId;
    if (!convId) {
      convId = createConversation(activeProvider);
      setActiveConversation(convId);
    }

    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    addMessage(convId, { role: 'user', content, provider: activeProvider });

    const assistantMsgId = addMessage(convId, {
      role: 'assistant', content: '', provider: activeProvider,
      model: activeProvider === 'ollama' ? ollamaModel : claudeModel,
      thinking: true,
    });

    setStreaming(true);
    abortRef.current = new AbortController();

    const currentConv = useAppStore.getState().conversations.find((c) => c.id === convId);
    const messages = (currentConv?.messages ?? [])
      .filter((m) => !m.thinking && m.role !== 'tool')
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abortRef.current.signal,
        body: JSON.stringify({
          provider: activeProvider,
          model: activeProvider === 'ollama' ? ollamaModel : claudeModel,
          messages,
          ollamaUrl,
          apiKey: claudeApiKey,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        updateLastMessage(convId, `**Fehler:** ${err.error}`);
        setStreaming(false);
        return;
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let full = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        full += decoder.decode(value, { stream: true });
        updateLastMessage(convId, full);
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        updateLastMessage(convId, `**Verbindungsfehler:** ${e.message}`);
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, streaming, activeConversationId, activeProvider, ollamaModel, claudeModel, ollamaUrl, claudeApiKey, addMessage, updateLastMessage, createConversation, setActiveConversation]);

  const stop = () => {
    abortRef.current?.abort();
    setStreaming(false);
  };

  if (!conv) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8 gap-6">
        <div className="space-y-2">
          <div className="text-4xl">🤖</div>
          <h2 className="text-white text-lg font-medium">Desk Assistant</h2>
          <p className="text-[#969696] text-sm max-w-xs">
            Kombiniert Ollama (lokal) und Claude (Cloud) mit MCP-Tools und Skills.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 w-full max-w-md">
          {['Was ist MCP?', 'Code reviewen', 'Erkläre Raspberry Pi', 'Python Debugging'].map((q) => (
            <button
              key={q}
              onClick={() => { createConversation(activeProvider); send(q); }}
              className="text-left p-3 text-xs text-[#cccccc] bg-[#252526] hover:bg-[#2d2d30] border border-[#3e3e42] hover:border-[#007acc] rounded transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
        <ChatInput
          input={input} setInput={setInput} streaming={streaming}
          onSend={() => send()} onStop={stop}
          textareaRef={textareaRef} onInput={autoResize}
        />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {conv.messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onRetry={() => {}} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[#3e3e42] p-4">
        <ChatInput
          input={input} setInput={setInput} streaming={streaming}
          onSend={() => send()} onStop={stop}
          textareaRef={textareaRef} onInput={autoResize}
        />
      </div>
    </div>
  );
}

function ChatInput({
  input, setInput, streaming, onSend, onStop, textareaRef, onInput,
}: {
  input: string; setInput: (v: string) => void; streaming: boolean;
  onSend: () => void; onStop: () => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  onInput: () => void;
}) {
  return (
    <div className="flex gap-2 items-end bg-[#1e1e1e] border border-[#3e3e42] rounded-lg p-2 focus-within:border-[#007acc] transition-colors">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => { setInput(e.target.value); onInput(); }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); }
        }}
        placeholder="Nachricht eingeben… (Enter senden, Shift+Enter neue Zeile)"
        rows={1}
        className="flex-1 bg-transparent text-[#cccccc] placeholder-[#6a6a6a] resize-none text-sm focus:outline-none leading-relaxed"
        style={{ maxHeight: 200 }}
      />
      {streaming ? (
        <button
          onClick={onStop}
          className="p-1.5 text-[#f48771] hover:text-white transition-colors shrink-0"
          title="Stoppen"
        >
          <Square size={16} fill="currentColor" />
        </button>
      ) : (
        <button
          onClick={onSend}
          disabled={!input.trim()}
          className="p-1.5 text-[#007acc] hover:text-white disabled:text-[#6a6a6a] transition-colors shrink-0"
          title="Senden"
        >
          <Send size={16} />
        </button>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message; onRetry: () => void }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const copyMsg = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[75%] bg-[#007acc] text-white px-4 py-2.5 rounded-lg rounded-tr-sm text-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 animate-fade-in group">
      <div className="w-7 h-7 rounded bg-[#252526] border border-[#3e3e42] flex items-center justify-center shrink-0 mt-0.5 text-xs">
        {message.provider === 'claude' ? '✦' : '🟢'}
      </div>
      <div className="flex-1 min-w-0">
        {message.thinking ? (
          <div className="flex items-center gap-2 text-[#969696] text-sm">
            <span className="animate-pulse-slow">●</span>
            <span className="animate-pulse-slow" style={{ animationDelay: '0.2s' }}>●</span>
            <span className="animate-pulse-slow" style={{ animationDelay: '0.4s' }}>●</span>
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none text-[#cccccc] text-sm leading-relaxed">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className ?? '');
                  const inline = !match;
                  return !inline ? (
                    <div className="relative group/code">
                      <SyntaxHighlighter
                        style={vscDarkPlus as Record<string, React.CSSProperties>}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ borderRadius: 6, fontSize: 12, margin: '8px 0' }}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                      <button
                        className="absolute top-2 right-2 opacity-0 group-hover/code:opacity-100 p-1 bg-[#1e1e1e] rounded text-[#969696] hover:text-white transition-all"
                        onClick={() => navigator.clipboard.writeText(String(children))}
                      >
                        <Copy size={11} />
                      </button>
                    </div>
                  ) : (
                    <code className="bg-[#1e1e1e] px-1.5 py-0.5 rounded font-mono text-[#ce9178] text-[11px]" {...props}>
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => <>{children}</>,
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-2 border-[#007acc] pl-3 text-[#969696] italic">{children}</blockquote>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
        {!message.thinking && message.content && (
          <div className="flex gap-2 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button onClick={copyMsg} className="text-[#6a6a6a] hover:text-[#969696] transition-colors">
              {copied ? <Check size={11} className="text-[#4ec9b0]" /> : <Copy size={11} />}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
