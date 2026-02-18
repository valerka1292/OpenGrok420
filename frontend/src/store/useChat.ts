import { create } from 'zustand';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || '';

export type StreamEventType =
    | 'session'
    | 'status'
    | 'thought'
    | 'tool_use'
    | 'chatroom_send'
    | 'wait'
    | 'token'
    | 'error'
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
    createdAt?: string;
}

export interface ChatSessionSummary {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
    message_count: number;
}

interface SessionDetails extends ChatSessionSummary {
    messages: Array<{
        role: 'user' | 'assistant';
        content: string;
        created_at: string;
        duration?: number;
    }>;
}

export interface StreamEvent {
    type: StreamEventType;
    content?: string;
    session_id?: string;
    [key: string]: unknown;
}

export interface ChatState {
    messages: Message[];
    sessions: ChatSessionSummary[];
    activeSessionId: string;
    isGenerating: boolean;
    currentThoughts: Thought[];
    currentResponse: string;
    currentStatus: string;
    lastError: string;
    temperature: Record<string, number>;
    startTime: number;

    setAgentTemperature: (agent: string, temp: number) => void;
    setActiveSession: (sessionId: string) => Promise<void>;
    createSession: () => Promise<void>;
    loadSessions: () => Promise<void>;
    addUserMessage: (content: string) => void;
    startGeneration: () => void;
    stopGeneration: (errorMessage?: string) => void;
    handleStreamEvent: (event: StreamEvent) => void;
    clearMessages: () => Promise<void>;
}

const isThoughtEvent = (type: StreamEventType): type is Exclude<Thought['type'], 'status'> => (
    type === 'thought' || type === 'tool_use' || type === 'chatroom_send' || type === 'wait'
);

const normalizeSession = (session: ChatSessionSummary): ChatSessionSummary => ({
    ...session,
    title: session.title || 'Новый диалог',
});

const useChat = create<ChatState>((set, get) => ({
    messages: [],
    sessions: [],
    activeSessionId: '',
    isGenerating: false,
    currentThoughts: [],
    currentResponse: '',
    currentStatus: 'Готов к работе',
    lastError: '',
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

    loadSessions: async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/sessions`);
            if (!response.ok) throw new Error('Не удалось загрузить историю сессий');

            const sessions = (await response.json() as ChatSessionSummary[]).map(normalizeSession);
            const activeSessionId = get().activeSessionId || sessions[0]?.id || '';

            set({ sessions, activeSessionId });

            if (activeSessionId) {
                await get().setActiveSession(activeSessionId);
            } else {
                set({ messages: [] });
            }
        } catch (error) {
            set({
                lastError: error instanceof Error ? error.message : 'Ошибка загрузки истории',
            });
        }
    },

    createSession: async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/sessions`, { method: 'POST' });
            if (!response.ok) throw new Error('Не удалось создать сессию');

            const created = normalizeSession(await response.json() as ChatSessionSummary);
            set((state) => ({
                sessions: [created, ...state.sessions.filter((s) => s.id !== created.id)],
                activeSessionId: created.id,
                messages: [],
                currentResponse: '',
                currentThoughts: [],
                currentStatus: 'Новый диалог',
                lastError: '',
                startTime: 0,
            }));
        } catch (error) {
            set({
                lastError: error instanceof Error ? error.message : 'Ошибка создания сессии',
            });
        }
    },

    setActiveSession: async (sessionId) => {
        if (!sessionId) return;

        set({ activeSessionId: sessionId, currentResponse: '', currentThoughts: [], startTime: 0 });

        try {
            const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`);
            if (!response.ok) throw new Error('Не удалось открыть выбранный чат');

            const session = await response.json() as SessionDetails;
            set((state) => ({
                messages: session.messages.map((msg) => ({
                    role: msg.role,
                    content: msg.content,
                    duration: msg.duration,
                    createdAt: msg.created_at,
                })),
                sessions: [
                    normalizeSession({
                        id: session.id,
                        title: session.title,
                        created_at: session.created_at,
                        updated_at: session.updated_at,
                        message_count: session.messages.length,
                    }),
                    ...state.sessions.filter((item) => item.id !== session.id),
                ],
                activeSessionId: session.id,
                currentStatus: `Открыт чат: ${session.title}`,
                lastError: '',
            }));
        } catch (error) {
            set({
                lastError: error instanceof Error ? error.message : 'Ошибка загрузки чата',
            });
        }
    },

    addUserMessage: (content) => set((state) => ({
        messages: [...state.messages, { role: 'user', content }],
        lastError: '',
    })),

    clearMessages: async () => {
        await get().createSession();
    },

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

        if (type === 'session') {
            const sessionId = String(event.session_id ?? '');
            if (!sessionId) return;

            set((state) => {
                const exists = state.sessions.some((item) => item.id === sessionId);
                return {
                    activeSessionId: sessionId,
                    sessions: exists
                        ? state.sessions
                        : [{
                            id: sessionId,
                            title: state.messages[0]?.content?.slice(0, 56) || 'Новый диалог',
                            created_at: new Date().toISOString(),
                            updated_at: new Date().toISOString(),
                            message_count: state.messages.length,
                        }, ...state.sessions],
                };
            });
            return;
        }

        if (isThoughtEvent(type)) {
            set((state) => ({
                currentThoughts: [...state.currentThoughts, event as Thought],
            }));
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
            const { currentResponse, currentThoughts, startTime, activeSessionId } = get();
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
                            createdAt: new Date().toISOString(),
                        },
                    ],
                    currentResponse: '',
                    currentThoughts: [],
                    currentStatus: 'Ответ получен',
                    startTime: 0,
                    sessions: state.sessions.map((session) => (
                        session.id === activeSessionId
                            ? {
                                ...session,
                                updated_at: new Date().toISOString(),
                                message_count: state.messages.length + 1,
                            }
                            : session
                    )),
                }));
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
}));

export default useChat;
