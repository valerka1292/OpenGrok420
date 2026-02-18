import { create } from 'zustand';

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

export interface ChatState {
    messages: Message[];
    isGenerating: boolean;
    currentThoughts: Thought[];
    currentResponse: string;
    temperature: Record<string, number>;
    startTime: number;

    setAgentTemperature: (agent: string, temp: number) => void;
    addUserMessage: (content: string) => void;
    startGeneration: () => void;
    stopGeneration: () => void;
    handleStreamEvent: (event: any) => void; // Using any for raw JSON event for now, can refine
}

const useChat = create<ChatState>((set, get) => ({
    messages: [],
    isGenerating: false,
    currentThoughts: [],
    currentResponse: "",
    temperature: {
        Grok: 0.7,
        Harper: 0.7,
        Benjamin: 0.7,
        Lucas: 0.7
    },
    startTime: 0,

    setAgentTemperature: (agent, temp) => set((state) => ({
        temperature: { ...state.temperature, [agent]: temp }
    })),

    addUserMessage: (content) => set((state) => ({
        messages: [...state.messages, { role: 'user', content }]
    })),

    startGeneration: () => set({
        isGenerating: true,
        currentThoughts: [],
        currentResponse: "",
        startTime: Date.now()
    }),

    stopGeneration: () => {
        // In a real implementation with fetch, we'd need an AbortController.
        // For now, just resetting state.
        set({ isGenerating: false });
    },

    handleStreamEvent: (event) => {
        const { type } = event;

        if (type === 'thought' || type === 'tool_use' || type === 'chatroom_send' || type === 'wait') {
            set((state) => ({
                currentThoughts: [...state.currentThoughts, event]
            }));
        } else if (type === 'token') {
            set((state) => ({
                currentResponse: state.currentResponse + event.content
            }));
        } else if (type === 'done') {
            const { currentResponse, currentThoughts, startTime } = get();
            const duration = startTime ? (Date.now() - startTime) / 1000 : 0;

            set((state) => ({
                isGenerating: false,
                messages: [...state.messages, {
                    role: 'assistant',
                    content: currentResponse,
                    thoughts: currentThoughts,
                    duration: duration
                }],
                currentResponse: "",
                currentThoughts: [],
                startTime: 0
            }));
        } else if (type === 'status') {
            // Optional: handle status updates
        }
    }
}));

export default useChat;
