'use client';
import { useAppStore } from '@/stores/appStore';
import { Plus, Trash2, MessageSquare, Cpu, Settings, RefreshCw, Puzzle, Wrench } from 'lucide-react';
import { useState } from 'react';

export function Sidebar() {
  const {
    conversations, activeConversationId, createConversation,
    setActiveConversation, deleteConversation, activeTab, setActiveTab,
    activeProvider, setActiveProvider, ollamaModel, claudeModel, claudeApiKey,
  } = useAppStore();
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');

  const newChat = () => {
    const id = createConversation();
    setActiveConversation(id);
    setActiveTab('chat');
  };

  const syncGit = async () => {
    setSyncing(true);
    setSyncMsg('');
    try {
      const res = await fetch('/api/sync', { method: 'POST' });
      const data = await res.json();
      setSyncMsg(data.status === 'ok' ? '✓ Synced' : '✗ ' + data.output?.slice(0, 40));
    } catch {
      setSyncMsg('✗ Error');
    }
    setSyncing(false);
    setTimeout(() => setSyncMsg(''), 3000);
  };

  const navItems = [
    { id: 'chat' as const, icon: MessageSquare, label: 'Chat' },
    { id: 'skills' as const, icon: Puzzle, label: 'Skills' },
    { id: 'mcp' as const, icon: Wrench, label: 'MCP Tools' },
  ] as const;

  return (
    <div className="w-[260px] bg-[#252526] border-r border-[#3e3e42] flex flex-col h-full shrink-0">
      {/* Nav Icons */}
      <div className="flex border-b border-[#3e3e42]">
        {navItems.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            title={label}
            className={`flex-1 py-2 flex flex-col items-center gap-0.5 text-[10px] transition-colors ${
              activeTab === id
                ? 'text-white border-b border-[#007acc]'
                : 'text-[#969696] hover:text-[#cccccc]'
            }`}
          >
            <Icon size={14} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {activeTab === 'chat' && (
        <>
          {/* Provider Toggle */}
          <div className="p-3 border-b border-[#3e3e42]">
            <div className="flex gap-1 bg-[#1e1e1e] rounded p-0.5">
              <button
                onClick={() => setActiveProvider('ollama')}
                className={`flex-1 py-1 text-xs rounded transition-colors flex items-center justify-center gap-1 ${
                  activeProvider === 'ollama'
                    ? 'bg-[#007acc] text-white'
                    : 'text-[#969696] hover:text-[#cccccc]'
                }`}
              >
                <Cpu size={10} />
                Ollama
              </button>
              <button
                onClick={() => setActiveProvider('claude')}
                disabled={!claudeApiKey}
                title={!claudeApiKey ? 'Claude API Key fehlt' : ''}
                className={`flex-1 py-1 text-xs rounded transition-colors flex items-center justify-center gap-1 ${
                  activeProvider === 'claude'
                    ? 'bg-[#c586c0] text-white'
                    : !claudeApiKey
                    ? 'text-[#6a6a6a] cursor-not-allowed'
                    : 'text-[#969696] hover:text-[#cccccc]'
                }`}
              >
                ✦ Claude
              </button>
            </div>
            <p className="text-[#6a6a6a] text-[10px] mt-1 text-center">
              {activeProvider === 'ollama' ? ollamaModel : claudeModel}
            </p>
          </div>

          {/* New Chat */}
          <button
            onClick={newChat}
            className="mx-3 mt-3 mb-2 flex items-center gap-2 text-[#cccccc] hover:text-white text-xs py-1.5 px-2 rounded border border-[#3e3e42] hover:border-[#007acc] transition-colors"
          >
            <Plus size={12} />
            Neuer Chat
          </button>

          {/* Conversations */}
          <div className="flex-1 overflow-y-auto py-1">
            {conversations.length === 0 && (
              <p className="text-[#6a6a6a] text-xs text-center mt-8">Kein Chat vorhanden</p>
            )}
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => { setActiveConversation(conv.id); setActiveTab('chat'); }}
                className={`group flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
                  activeConversationId === conv.id
                    ? 'bg-[#37373d] text-white'
                    : 'text-[#cccccc] hover:bg-[#2a2d2e]'
                }`}
              >
                <span className="text-[10px]">{conv.provider === 'ollama' ? '🟢' : '✦'}</span>
                <span className="flex-1 text-xs truncate">{conv.title}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                  className="opacity-0 group-hover:opacity-100 text-[#969696] hover:text-[#f48771] transition-opacity"
                >
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
          </div>

          {/* GitHub Sync */}
          <div className="p-3 border-t border-[#3e3e42]">
            <button
              onClick={syncGit}
              disabled={syncing}
              className="w-full flex items-center gap-2 text-xs text-[#969696] hover:text-[#cccccc] py-1.5 px-2 rounded hover:bg-[#2a2d2e] transition-colors"
            >
              <RefreshCw size={11} className={syncing ? 'animate-spin' : ''} />
              {syncMsg || 'GitHub Sync'}
            </button>
          </div>
        </>
      )}

      {activeTab === 'skills' && <SkillsTab />}
      {activeTab === 'mcp' && <MCPTab />}
    </div>
  );
}

function SkillsTab() {
  const skills = [
    { name: 'Code Review', provider: 'both', desc: 'Code analysieren und verbessern', icon: '🔍' },
    { name: 'Zusammenfassung', provider: 'both', desc: 'Text zusammenfassen', icon: '📝' },
    { name: 'Übersetzen', provider: 'both', desc: 'Sprachen übersetzen', icon: '🌐' },
    { name: 'Debugging', provider: 'ollama', desc: 'Fehler finden und beheben', icon: '🐛' },
    { name: 'Brainstorming', provider: 'claude', desc: 'Ideen entwickeln', icon: '💡' },
    { name: 'SQL Generator', provider: 'both', desc: 'SQL-Abfragen erstellen', icon: '🗄️' },
    { name: 'Regex Helper', provider: 'both', desc: 'Reguläre Ausdrücke', icon: '🔤' },
    { name: 'Erklärung', provider: 'claude', desc: 'Konzepte verständlich erklären', icon: '📚' },
  ];
  return (
    <div className="flex-1 overflow-y-auto p-3">
      <p className="text-[#969696] text-[10px] uppercase tracking-wider mb-3">Skills</p>
      <div className="space-y-1">
        {skills.map((s) => (
          <div key={s.name} className="flex items-center gap-2 p-2 rounded hover:bg-[#2a2d2e] cursor-pointer group">
            <span className="text-base">{s.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="text-xs text-[#cccccc] group-hover:text-white">{s.name}</div>
              <div className="text-[10px] text-[#6a6a6a] truncate">{s.desc}</div>
            </div>
            <span className={`text-[9px] px-1.5 py-0.5 rounded ${
              s.provider === 'both' ? 'bg-[#007acc22] text-[#007acc]' :
              s.provider === 'ollama' ? 'bg-[#4ec9b022] text-[#4ec9b0]' :
              'bg-[#c586c022] text-[#c586c0]'
            }`}>
              {s.provider}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MCPTab() {
  const { mcpTools, toggleMCPTool } = useAppStore();
  return (
    <div className="flex-1 overflow-y-auto p-3">
      <p className="text-[#969696] text-[10px] uppercase tracking-wider mb-3">MCP Tools</p>
      <div className="space-y-1">
        {mcpTools.map((t) => (
          <div key={t.name} className="flex items-center gap-2 p-2 rounded hover:bg-[#2a2d2e]">
            <div className="flex-1 min-w-0">
              <div className="text-xs text-[#cccccc] font-mono">{t.name}</div>
              <div className="text-[10px] text-[#6a6a6a] truncate">{t.description}</div>
            </div>
            <button
              onClick={() => toggleMCPTool(t.name)}
              className={`w-8 h-4 rounded-full transition-colors relative ${t.enabled ? 'bg-[#007acc]' : 'bg-[#3e3e42]'}`}
            >
              <span className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-transform ${t.enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
            </button>
          </div>
        ))}
      </div>
      <p className="text-[#6a6a6a] text-[10px] mt-4 leading-relaxed">
        MCP = Model Context Protocol. Tools erweitern die KI mit echten Fähigkeiten.
      </p>
    </div>
  );
}

// Settings sub-component (used inline)
export function SettingsIcon() {
  return <Settings size={14} />;
}
