import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type AIProvider = 'ollama' | 'claude';
export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  provider?: AIProvider;
  model?: string;
  timestamp: number;
  skillUsed?: string;
  thinking?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  provider: AIProvider;
  model: string;
  createdAt: number;
  updatedAt: number;
}

export interface MCPTool {
  name: string;
  description: string;
  schema: Record<string, unknown>;
  enabled: boolean;
}

interface AppState {
  // Setup
  claudeApiKey: string;
  isSetupComplete: boolean;

  // AI Config
  activeProvider: AIProvider;
  ollamaModel: string;
  claudeModel: string;
  ollamaUrl: string;

  // Conversations
  conversations: Conversation[];
  activeConversationId: string | null;

  // UI
  sidebarOpen: boolean;
  skillsPanelOpen: boolean;
  activeTab: 'chat' | 'skills' | 'mcp' | 'sync';

  // MCP Tools
  mcpTools: MCPTool[];

  // Actions
  setClaudeApiKey: (key: string) => void;
  completeSetup: () => void;
  setActiveProvider: (p: AIProvider) => void;
  setOllamaModel: (m: string) => void;
  setClaudeModel: (m: string) => void;
  setOllamaUrl: (url: string) => void;
  createConversation: (provider?: AIProvider) => string;
  setActiveConversation: (id: string) => void;
  addMessage: (convId: string, msg: Omit<Message, 'id' | 'timestamp'>) => void;
  updateLastMessage: (convId: string, content: string) => void;
  setMessageThinking: (convId: string, msgId: string, thinking: boolean) => void;
  deleteConversation: (id: string) => void;
  setSidebarOpen: (v: boolean) => void;
  setSkillsPanelOpen: (v: boolean) => void;
  setActiveTab: (t: AppState['activeTab']) => void;
  toggleMCPTool: (name: string) => void;
}

const generateId = () => Math.random().toString(36).slice(2, 10);

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      claudeApiKey: '',
      isSetupComplete: false,
      activeProvider: 'ollama',
      ollamaModel: 'llama3.2',
      claudeModel: 'claude-haiku-4-5-20251001',
      ollamaUrl: 'http://localhost:11434',
      conversations: [],
      activeConversationId: null,
      sidebarOpen: true,
      skillsPanelOpen: false,
      activeTab: 'chat',
      mcpTools: [
        { name: 'get_time', description: 'Get current date and time', schema: {}, enabled: true },
        { name: 'github_sync', description: 'Sync with GitHub repository', schema: {}, enabled: true },
        { name: 'file_read', description: 'Read a local file', schema: { path: 'string' }, enabled: false },
        { name: 'web_search', description: 'Search the web (requires API)', schema: { query: 'string' }, enabled: false },
        { name: 'run_code', description: 'Execute Python/JS code', schema: { code: 'string', lang: 'string' }, enabled: false },
      ],

      setClaudeApiKey: (key) => set({ claudeApiKey: key }),
      completeSetup: () => set({ isSetupComplete: true }),
      setActiveProvider: (p) => set({ activeProvider: p }),
      setOllamaModel: (m) => set({ ollamaModel: m }),
      setClaudeModel: (m) => set({ claudeModel: m }),
      setOllamaUrl: (url) => set({ ollamaUrl: url }),

      createConversation: (provider) => {
        const id = generateId();
        const p = provider ?? get().activeProvider;
        const conv: Conversation = {
          id,
          title: 'New Chat',
          messages: [],
          provider: p,
          model: p === 'claude' ? get().claudeModel : get().ollamaModel,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        set((s) => ({ conversations: [conv, ...s.conversations], activeConversationId: id }));
        return id;
      },

      setActiveConversation: (id) => set({ activeConversationId: id }),

      addMessage: (convId, msg) => {
        const id = generateId();
        const message: Message = { ...msg, id, timestamp: Date.now() };
        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== convId) return c;
            const msgs = [...c.messages, message];
            const title = msgs.length === 1 && msg.role === 'user'
              ? msg.content.slice(0, 40) + (msg.content.length > 40 ? '…' : '')
              : c.title;
            return { ...c, messages: msgs, title, updatedAt: Date.now() };
          }),
        }));
        return id;
      },

      updateLastMessage: (convId, content) => {
        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== convId) return c;
            const msgs = [...c.messages];
            const last = msgs[msgs.length - 1];
            if (last && last.role === 'assistant') {
              msgs[msgs.length - 1] = { ...last, content, thinking: false };
            }
            return { ...c, messages: msgs, updatedAt: Date.now() };
          }),
        }));
      },

      setMessageThinking: (convId, msgId, thinking) => {
        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== convId) return c;
            return {
              ...c,
              messages: c.messages.map((m) => m.id === msgId ? { ...m, thinking } : m),
            };
          }),
        }));
      },

      deleteConversation: (id) => {
        set((s) => {
          const convs = s.conversations.filter((c) => c.id !== id);
          const activeId = s.activeConversationId === id
            ? (convs[0]?.id ?? null)
            : s.activeConversationId;
          return { conversations: convs, activeConversationId: activeId };
        });
      },

      setSidebarOpen: (v) => set({ sidebarOpen: v }),
      setSkillsPanelOpen: (v) => set({ skillsPanelOpen: v }),
      setActiveTab: (t) => set({ activeTab: t }),
      toggleMCPTool: (name) => {
        set((s) => ({
          mcpTools: s.mcpTools.map((t) => t.name === name ? { ...t, enabled: !t.enabled } : t),
        }));
      },
    }),
    {
      name: 'desk-assistant-store',
      partialize: (s) => ({
        claudeApiKey: s.claudeApiKey,
        isSetupComplete: s.isSetupComplete,
        activeProvider: s.activeProvider,
        ollamaModel: s.ollamaModel,
        claudeModel: s.claudeModel,
        ollamaUrl: s.ollamaUrl,
        conversations: s.conversations,
        activeConversationId: s.activeConversationId,
        mcpTools: s.mcpTools,
      }),
    }
  )
);
