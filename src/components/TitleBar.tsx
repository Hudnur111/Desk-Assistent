'use client';
import { useAppStore } from '@/stores/appStore';
import { Menu, GitBranch, Cpu, Wifi, WifiOff } from 'lucide-react';
import { useState, useEffect } from 'react';

interface GitInfo { branch: string; commit: string; dirty: boolean; }

export function TitleBar() {
  const { sidebarOpen, setSidebarOpen, activeProvider, ollamaModel, claudeModel } = useAppStore();
  const [gitInfo, setGitInfo] = useState<GitInfo | null>(null);
  const [ollamaOnline, setOllamaOnline] = useState<boolean | null>(null);

  useEffect(() => {
    fetch('/api/sync').then(r => r.json()).then(setGitInfo).catch(() => {});
    fetch('/api/ollama/models').then(r => r.json()).then(d => setOllamaOnline(d.models?.length > 0)).catch(() => setOllamaOnline(false));
  }, []);

  const model = activeProvider === 'ollama' ? ollamaModel : claudeModel;

  return (
    <div className="h-[30px] bg-[#3c3c3c] flex items-center px-3 gap-3 shrink-0 select-none border-b border-[#1e1e1e]">
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="text-[#cccccc] hover:text-white p-0.5 rounded"
      >
        <Menu size={14} />
      </button>

      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className="text-[#cccccc] text-xs font-medium">Desk Assistant</span>
        {gitInfo && (
          <div className="flex items-center gap-1 text-[#969696] text-[11px]">
            <GitBranch size={10} />
            <span>{gitInfo.branch}</span>
            {gitInfo.dirty && <span className="text-[#dcdcaa]">●</span>}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-[11px]">
          <Cpu size={10} className={activeProvider === 'ollama' ? 'text-[#4ec9b0]' : 'text-[#c586c0]'} />
          <span className="text-[#969696]">{model}</span>
        </div>
        <div className="flex items-center gap-1">
          {ollamaOnline
            ? <Wifi size={10} className="text-[#4ec9b0]" />
            : <WifiOff size={10} className="text-[#f48771]" />
          }
        </div>
      </div>
    </div>
  );
}
