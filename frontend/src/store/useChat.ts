import { create } from 'zustand';

export type StreamEventType =
    | 'status'
    | 'thought'
    | 'tool_use'
    | 'chatroom_send'
    | 'wait'
    | 'token'
    | 'error'
    | 'conversation'
    | 'conversation_title'
    | 'done';

export interface Thought {
    type: 'thought' | 'tool_use' | 'chatroom_send' | 'wait' | 'status';
    agent?: string;
    content?: string;
    tool?: string;
    query?: string;
    to?: string;
    num_results?: number;
}

export interface Message {
    role: 'user' | 'assistant';
    content: string;
    thoughts?: Thought[];
    duration?: number;
    created_at?: string;
}

export interface ConversationSummary {
    id: string;
    title: string;
    updated_at: string;
    last_message: string;
    message_count: number;
}

export interface StreamEvent {
    type: StreamEventType;
    content?: string;
    conversation_id?: string;
    [key: string]: unknown;
}

interface ConversationPayload {
    id: string;
    title: string;
    messages: Message[];
}

export interface ChatState {
    messages: Message[];
    isGenerating: boolean;
    currentThoughts: Thought[];
    currentResponse: string;
    currentStatus: string;
    lastError: string;
    temperature: Record<string, number>;
    startTime: number;
    conversations: ConversationSummary[];
    currentConversationId: string | null;

    setAgentTemperature: (agent: string, temp: number) => void;
    addUserMessage: (content: string) => void;
    startGeneration: () => void;
    stopGeneration: (errorMessage?: string) => void;
    handleStreamEvent: (event: StreamEvent) => void;
    clearMessages: () => void;

    loadConversations: (query?: string) => Promise<void>;
    loadConversation: (id: string) => Promise<void>;
    createConversation: (title?: string) => Promise<void>;
    deleteConversation: (id: string) => Promise<void>;
    setCurrentConversationId: (id: string | null) => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || '';

const isThoughtEvent = (type: StreamEventType): type is Exclude<Thought['type'], 'status'> => (
    type === 'thought' || type === 'tool_use' || type === 'chatroom_send' || type === 'wait'
);

const useChat = create<ChatState>((set, get) => ({
    messages: [],
    isGenerating: false,
    currentThoughts: [],
    currentResponse: '',
    currentStatus: 'Готов к работе',
    lastError: '',
    conversations: [],
    currentConversationId: null,
    temperature: {
        Grok: 0.7,
        Harper: 0.7,
        Benjamin: 0.7,
        Lucas: 0.7,
    },
    startTime: 0,

    setAgentTemperature: (agent, temp) => set((state) => ({
        temperature: { ...state.temperature, [agent]: temp },
    })),

    setCurrentConversationId: (id) => set({ currentConversationId: id }),

    addUserMessage: (content) => set((state) => ({
        messages: [...state.messages, { role: 'user', content }],
        lastError: '',
    })),

    clearMessages: () => set({
        messages: [],
        currentResponse: '',
        currentThoughts: [],
        currentStatus: 'Диалог очищен',
        lastError: '',
        currentConversationId: null,
    }),

    startGeneration: () => set({
        isGenerating: true,
        currentThoughts: [],
        currentResponse: '',
        currentStatus: 'Генерация ответа…',
        lastError: '',
        startTime: Date.now(),
    }),

    stopGeneration: (errorMessage) => {
        set({
            isGenerating: false,
            currentStatus: errorMessage ? 'Ошибка генерации' : 'Генерация остановлена',
            lastError: errorMessage ?? '',
        });
    },

    handleStreamEvent: (event) => {
        const { type } = event;

        if (isThoughtEvent(type)) {
            set((state) => ({
                currentThoughts: [...state.currentThoughts, event as Thought],
            }));
            return;
        }

        if (type === 'conversation') {
            const conversationId = String(event.conversation_id ?? '');
            if (conversationId) {
                set({ currentConversationId: conversationId });
            }
            return;
        }

        if (type === 'conversation_title') {
            void get().loadConversations();
            return;
        }

        if (type === 'status') {
            set({ currentStatus: String(event.content ?? 'Обработка…') });
            return;
        }

        if (type === 'token') {
            set((state) => ({
                currentResponse: state.currentResponse + String(event.content ?? ''),
            }));
            return;
        }

        if (type === 'error') {
            set({
                lastError: String(event.content ?? 'Неизвестная ошибка потока'),
                currentStatus: 'Ошибка генерации',
            });
            return;
        }

        if (type === 'done') {
            const { currentResponse, currentThoughts, startTime } = get();
            const duration = startTime ? (Date.now() - startTime) / 1000 : 0;

            if (currentResponse.trim()) {
                set((state) => ({
                    isGenerating: false,
                    messages: [
                        ...state.messages,
                        {
                            role: 'assistant',
                            content: currentResponse,
                            thoughts: currentThoughts,
                            duration,
                        },
                    ],
                    currentResponse: '',
                    currentThoughts: [],
                    currentStatus: 'Ответ получен',
                    startTime: 0,
                }));
                void get().loadConversations();
            } else {
                set({
                    isGenerating: false,
                    currentResponse: '',
                    currentThoughts: [],
                    currentStatus: get().lastError ? 'Ошибка генерации' : 'Нет данных от модели',
                    startTime: 0,
                });
            }
        }
    },

    loadConversations: async (query = '') => {
        try {
            const params = new URLSearchParams();
            if (query.trim()) params.set('query', query.trim());
            const suffix = params.toString() ? `?${params.toString()}` : '';
            const response = await fetch(`${API_BASE_URL}/api/conversations${suffix}`);
            if (!response.ok) return;
            const payload = await response.json() as { items: ConversationSummary[] };
            set({ conversations: payload.items || [] });
        } catch {
            // silent in ui
        }
    },

    loadConversation: async (id) => {
        const response = await fetch(`${API_BASE_URL}/api/conversations/${id}`);
        if (!response.ok) return;
        const payload = await response.json() as ConversationPayload;
        set({
            currentConversationId: payload.id,
            messages: payload.messages || [],
            currentThoughts: [],
            currentResponse: '',
            lastError: '',
            currentStatus: 'История загружена',
        });
    },

    createConversation: async (title = 'Новый диалог') => {
        const response = await fetch(`${API_BASE_URL}/api/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title }),
        });
        if (!response.ok) return;
        const payload = await response.json() as ConversationPayload;
        set({
            currentConversationId: payload.id,
            messages: payload.messages || [],
            currentThoughts: [],
            currentResponse: '',
            currentStatus: 'Новый диалог',
            lastError: '',
        });
        await get().loadConversations();
    },

    deleteConversation: async (id) => {
        const response = await fetch(`${API_BASE_URL}/api/conversations/${id}`, {
            method: 'DELETE',
        });
        if (!response.ok) return;

        set((state) => ({
            conversations: state.conversations.filter((c) => c.id !== id),
            ...(state.currentConversationId === id
                ? { currentConversationId: null, messages: [], currentThoughts: [], currentResponse: '' }
                : {}),
        }));
    },
}));

export default useChat;
