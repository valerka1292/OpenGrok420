import { create } from 'zustand';

export type StreamEventType =
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
}

export interface StreamEvent {
    type: StreamEventType;
    content?: string;
    [key: string]: unknown;
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

    setAgentTemperature: (agent: string, temp: number) => void;
    addUserMessage: (content: string) => void;
    startGeneration: () => void;
    stopGeneration: (errorMessage?: string) => void;
    handleStreamEvent: (event: StreamEvent) => void;
    clearMessages: () => void;
}

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
