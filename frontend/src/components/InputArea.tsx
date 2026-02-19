import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, LoaderCircle, Send, SlidersHorizontal, Sparkles, Square, Trash2 } from 'lucide-react';
import useChat from '../store/useChat';
import SettingsModal from './SettingsModal';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || '';

const parseNdjsonChunk = (rawLine: string) => {
    const line = rawLine.trim();
    if (!line) return null;

    const payload = line.startsWith('data:') ? line.slice(5).trim() : line;
    if (!payload) return null;

    return JSON.parse(payload);
};

export default function InputArea() {
    const [input, setInput] = useState('');
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const {
        addUserMessage,
        startGeneration,
        handleStreamEvent,
        isGenerating,
        stopGeneration,
        temperature,
        setAgentTemperature,
        currentStatus,
        lastError,
        clearMessages,
        currentConversationId,
        consumeQueuedPrompt,
    } = useChat();

    const canSubmit = useMemo(() => input.trim().length > 0 && !isGenerating, [input, isGenerating]);

    const handleInputChange = (value: string) => {
        setInput(value);
        if (!textareaRef.current) return;
        textareaRef.current.style.height = '68px';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 220)}px`;
    };

    const handleStop = () => {
        abortControllerRef.current?.abort();
        stopGeneration('Поток остановлен пользователем');
    };

    const sendMessage = async (userMsg: string) => {
        addUserMessage(userMsg);
        startGeneration();

        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
                body: JSON.stringify({
                    message: userMsg,
                    temperatures: temperature,
                    conversation_id: currentConversationId,
                }),
            });

            if (!response.ok) {
                let details = '';
                try {
                    details = await response.text();
                } catch {
                    details = '';
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}${details ? ` — ${details}` : ''}`);
            }

            if (!response.body) {
                throw new Error('Пустой поток ответа от сервера');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let streamCompleted = false;

            const handleParsedEvent = (line: string) => {
                const event = parseNdjsonChunk(line);
                if (!event) return;

                handleStreamEvent(event);
                if (event.type === 'done') {
                    streamCompleted = true;
                }
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() ?? '';

                for (const line of lines) {
                    try {
                        handleParsedEvent(line);
                        if (streamCompleted) break;
                    } catch {
                        // keep stream alive even with malformed lines
                    }
                }

                if (streamCompleted) {
                    break;
                }
            }

            const tail = buffer.trim();
            if (tail && !streamCompleted) {
                try {
                    handleParsedEvent(tail);
                } catch {
                    // ignored
                }
            }

            if (!streamCompleted) {
                handleStreamEvent({ type: 'done' });
            }
        } catch (error) {
            if (error instanceof DOMException && error.name === 'AbortError') {
                handleStreamEvent({ type: 'done' });
                return;
            }

            const message = error instanceof Error ? error.message : 'Не удалось подключиться к backend';
            handleStreamEvent({ type: 'error', content: message });
            handleStreamEvent({ type: 'done' });
        } finally {
            abortControllerRef.current = null;
        }
    };

    const handleSubmit = async (e: React.FormEvent | React.KeyboardEvent) => {
        e.preventDefault();
        if (!canSubmit) return;

        const userMsg = input.trim();
        setInput('');
        if (textareaRef.current) {
            textareaRef.current.style.height = '68px';
        }

        await sendMessage(userMsg);
    };

    useEffect(() => {
        if (isGenerating) return;
        const queued = consumeQueuedPrompt();
        if (!queued) return;
        void sendMessage(queued);
    }, [isGenerating, consumeQueuedPrompt]);

    return (
        <>
            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                temperatures={temperature}
                setAgentTemperature={setAgentTemperature}
            />

            <div className="p-4 pt-2 bg-gradient-to-t from-bg-body via-bg-body to-transparent z-10 w-full max-w-5xl mx-auto">
                <div className="mb-3 flex items-center justify-between gap-3 text-xs px-2">
                    <div className="inline-flex items-center gap-2 text-text-muted">
                        {isGenerating ? <LoaderCircle size={13} className="animate-spin" /> : <Sparkles size={13} />}
                        <span className="truncate">{currentStatus}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        {lastError && (
                            <span className="inline-flex items-center gap-1 text-red-300 bg-red-500/10 px-2 py-1 rounded-md border border-red-500/30">
                                <AlertCircle size={12} />
                                Ошибка ответа
                            </span>
                        )}
                        <button
                            type="button"
                            onClick={clearMessages}
                            className="inline-flex items-center gap-1 text-text-muted hover:text-text-primary px-2 py-1 rounded-md hover:bg-white/5"
                            title="Очистить диалог"
                        >
                            <Trash2 size={12} />
                            Очистить
                        </button>
                    </div>
                </div>

                <form
                    onSubmit={handleSubmit}
                    className="relative bg-bg-surface/85 backdrop-blur-2xl rounded-2xl border border-border-subtle shadow-xl transition-all duration-300 focus-within:border-accent-blue/35 focus-within:ring-1 focus-within:ring-accent-blue/20 hover:border-text-muted/30"
                >
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => handleInputChange(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                void handleSubmit(e);
                            }
                        }}
                        placeholder="Спросите Grok Team... (Enter — отправить, Shift+Enter — новая строка)"
                        className="w-full bg-transparent text-text-primary p-4 pr-14 pl-12 focus:outline-none resize-none h-[68px] max-h-[220px] leading-relaxed placeholder:text-text-muted/60"
                    />

                    <div className="absolute bottom-3 left-3">
                        <button
                            type="button"
                            onClick={() => setIsSettingsOpen(true)}
                            className="p-2 text-text-muted hover:text-text-primary hover:bg-white/5 rounded-lg transition-colors group"
                            title="Настройки модели"
                        >
                            <SlidersHorizontal size={18} className="group-hover:scale-105 transition-transform" />
                        </button>
                    </div>

                    <div className="absolute bottom-3 right-3 flex items-center gap-2">
                        {!isGenerating ? (
                            <button
                                type="submit"
                                disabled={!canSubmit}
                                className={`w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-200 ${canSubmit
                                    ? 'bg-text-primary text-bg-body hover:bg-white/90 shadow-lg shadow-white/10'
                                    : 'bg-white/5 text-text-muted cursor-not-allowed'
                                    }`}
                            >
                                <Send size={18} className={canSubmit ? 'ml-0.5' : ''} />
                            </button>
                        ) : (
                            <button
                                type="button"
                                onClick={handleStop}
                                className="w-9 h-9 flex items-center justify-center rounded-lg bg-text-primary text-bg-body hover:bg-white/90 shadow-lg shadow-white/10 animate-in zoom-in-50 duration-200"
                            >
                                <Square size={14} fill="currentColor" />
                            </button>
                        )}
                    </div>
                </form>

                <div className="flex items-center justify-center gap-2 mt-4 text-[10px] uppercase tracking-widest text-text-muted font-medium opacity-60">
                    <Sparkles size={10} />
                    <span>Grok 4.20 Beta · Streaming NDJSON</span>
                </div>
            </div>
        </>
    );
}
