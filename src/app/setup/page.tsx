'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/appStore';

export default function SetupPage() {
  const router = useRouter();
  const { setClaudeApiKey, completeSetup, setOllamaUrl, ollamaUrl } = useAppStore();
  const [key, setKey] = useState('');
  const [url, setUrl] = useState(ollamaUrl);
  const [step, setStep] = useState<'welcome' | 'ollama' | 'claude' | 'done'>('welcome');
  const [ollamaStatus, setOllamaStatus] = useState<'idle' | 'ok' | 'error'>('idle');
  const [testing, setTesting] = useState(false);

  const testOllama = async () => {
    setTesting(true);
    try {
      const res = await fetch(`/api/ollama/models?url=${encodeURIComponent(url)}`);
      const data = await res.json();
      setOllamaStatus(data.models?.length > 0 ? 'ok' : 'error');
    } catch {
      setOllamaStatus('error');
    }
    setTesting(false);
  };

  const finish = () => {
    if (key) setClaudeApiKey(key);
    setOllamaUrl(url);
    completeSetup();
    router.push('/');
  };

  return (
    <div className="min-h-screen bg-[#1e1e1e] flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[#007acc] flex items-center justify-center">
            <span className="text-2xl">🤖</span>
          </div>
          <h1 className="text-2xl font-semibold text-white">Desk Assistant</h1>
          <p className="text-[#969696] mt-1 text-sm">Setup — einmalig</p>
        </div>

        {/* Steps */}
        <div className="flex gap-2 mb-8 justify-center">
          {(['welcome', 'ollama', 'claude', 'done'] as const).map((s, i) => (
            <div key={s} className={`w-8 h-1 rounded-full transition-colors ${
              ['welcome', 'ollama', 'claude', 'done'].indexOf(step) >= i
                ? 'bg-[#007acc]' : 'bg-[#3e3e42]'
            }`} />
          ))}
        </div>

        <div className="bg-[#252526] border border-[#3e3e42] rounded-lg p-6">
          {step === 'welcome' && (
            <div className="space-y-4">
              <h2 className="text-white font-medium text-lg">Willkommen</h2>
              <p className="text-[#cccccc] text-sm leading-relaxed">
                Desk Assistant kombiniert <span className="text-[#4ec9b0]">Ollama</span> (lokale KI)
                und <span className="text-[#c586c0]">Claude</span> (Cloud-KI) in einer
                professionellen Chat-Oberfläche.
              </p>
              <ul className="space-y-2 text-sm text-[#969696]">
                <li className="flex gap-2"><span className="text-[#007acc]">●</span> VS Code Design</li>
                <li className="flex gap-2"><span className="text-[#007acc]">●</span> MCP Tool-Foundation</li>
                <li className="flex gap-2"><span className="text-[#007acc]">●</span> Skills für beide AIs</li>
                <li className="flex gap-2"><span className="text-[#007acc]">●</span> GitHub Sync</li>
              </ul>
              <button
                onClick={() => setStep('ollama')}
                className="w-full py-2.5 bg-[#007acc] hover:bg-[#1a8fde] text-white rounded transition-colors font-medium"
              >
                Einrichten →
              </button>
            </div>
          )}

          {step === 'ollama' && (
            <div className="space-y-4">
              <h2 className="text-white font-medium text-lg">Ollama konfigurieren</h2>
              <p className="text-[#969696] text-sm">Lokale KI — kostenlos, läuft auf dem Raspberry Pi.</p>
              <div>
                <label className="block text-[#cccccc] text-xs mb-1.5 uppercase tracking-wide">Ollama URL</label>
                <input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="w-full bg-[#1e1e1e] border border-[#3e3e42] text-[#cccccc] px-3 py-2 rounded font-mono text-sm focus:outline-none focus:border-[#007acc]"
                  placeholder="http://localhost:11434"
                />
              </div>
              <button
                onClick={testOllama}
                disabled={testing}
                className="w-full py-2 border border-[#3e3e42] text-[#cccccc] hover:border-[#007acc] rounded transition-colors text-sm"
              >
                {testing ? 'Teste…' : 'Verbindung testen'}
              </button>
              {ollamaStatus === 'ok' && (
                <p className="text-[#4ec9b0] text-sm">✓ Ollama erreichbar</p>
              )}
              {ollamaStatus === 'error' && (
                <p className="text-[#f48771] text-sm">✗ Ollama nicht erreichbar — trotzdem fortfahren?</p>
              )}
              <div className="flex gap-2">
                <button onClick={() => setStep('welcome')} className="flex-1 py-2 border border-[#3e3e42] text-[#969696] rounded text-sm">
                  Zurück
                </button>
                <button onClick={() => setStep('claude')} className="flex-1 py-2 bg-[#007acc] text-white rounded text-sm">
                  Weiter →
                </button>
              </div>
            </div>
          )}

          {step === 'claude' && (
            <div className="space-y-4">
              <h2 className="text-white font-medium text-lg">Claude API Key</h2>
              <p className="text-[#969696] text-sm">
                Optional — ermöglicht Claude als zweite KI.
                Erhältlich auf <span className="text-[#007acc]">console.anthropic.com</span>
              </p>
              <div>
                <label className="block text-[#cccccc] text-xs mb-1.5 uppercase tracking-wide">API Key</label>
                <input
                  type="password"
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                  className="w-full bg-[#1e1e1e] border border-[#3e3e42] text-[#cccccc] px-3 py-2 rounded font-mono text-sm focus:outline-none focus:border-[#007acc]"
                  placeholder="sk-ant-api03-…"
                />
              </div>
              <p className="text-[#6a6a6a] text-xs">Gespeichert nur lokal in deinem Browser (localStorage).</p>
              <div className="flex gap-2">
                <button onClick={() => setStep('ollama')} className="flex-1 py-2 border border-[#3e3e42] text-[#969696] rounded text-sm">
                  Zurück
                </button>
                <button onClick={finish} className="flex-1 py-2 bg-[#007acc] text-white rounded text-sm">
                  Fertigstellen →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
