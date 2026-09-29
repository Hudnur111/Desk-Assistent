'use client';
import { useAppStore } from '@/stores/appStore';
import { useEffect, useState } from 'react';

export function StatusBar() {
  const { activeProvider, ollamaModel, claudeModel, conversations, activeConversationId } = useAppStore();
  const [time, setTime] = useState('');

  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }));
    update();
    const id = setInterval(update, 10000);
    return () => clearInterval(id);
  }, []);

  const conv = conversations.find((c) => c.id === activeConversationId);
  const model = activeProvider === 'ollama' ? ollamaModel : claudeModel;

  return (
    <div className="h-[22px] bg-[#007acc] flex items-center px-3 gap-4 text-white text-[11px] shrink-0">
      <span className="font-medium">
        {activeProvider === 'ollama' ? '⬡ Ollama' : '✦ Claude'}
      </span>
      <span className="opacity-75">{model}</span>
      {conv && (
        <span className="opacity-60">{conv.messages.length} Nachrichten</span>
      )}
      <span className="ml-auto opacity-75">{time}</span>
      <span className="opacity-60">Raspberry Pi 4B</span>
    </div>
  );
}
