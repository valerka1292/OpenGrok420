import { useEffect, useRef } from 'react';
import { Bot, MessageCircleQuestion, Sparkles } from 'lucide-react';
import useChat from '../store/useChat';
import ThoughtsAccordion from './ThoughtsAccordion';
import MarkdownRenderer from './MarkdownRenderer';

export default function ChatArea() {
    const { messages, isGenerating, currentResponse, currentThoughts, startTime, lastError } = useChat();
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, currentResponse, currentThoughts]);

    return (
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scroll-smooth">
            {messages.length === 0 && !isGenerating && (
                <div className="h-full flex flex-col items-center justify-center text-text-muted opacity-60 min-h-[60vh] select-none">
                    <div className="w-16 h-16 rounded-2xl border border-border-subtle flex items-center justify-center mb-6 bg-bg-surface/50 shadow-inner">
                        <Sparkles size={30} className="text-accent-blue" />
                    </div>
                    <h1 className="text-3xl md:text-4xl font-bold text-text-primary tracking-tight">Grok Team</h1>
                    <p className="mt-4 text-sm md:text-base max-w-xl text-center text-text-secondary">
                        Мультиагентная система совместного интеллекта. Опиши задачу как можно подробнее — и команда построит ответ шаг за шагом.
                    </p>
                </div>
            )}

            {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-4xl w-full ${msg.role === 'user' ? 'ml-auto max-w-[92%] md:max-w-[72%]' : ''}`}>
                        {msg.role === 'user' ? (
                            <div className="bg-bg-message text-text-primary px-5 py-3.5 rounded-2xl rounded-tr-sm leading-relaxed whitespace-pre-wrap shadow-sm text-[15px] border border-border-subtle/60">
                                {msg.content}
                            </div>
                        ) : (
                            <div className="space-y-2">
                                <div className="inline-flex items-center gap-2 text-xs text-text-muted px-1.5">
                                    <Bot size={14} />
                                    <span>Ответ команды агентов</span>
                                    {msg.duration ? <span>· {msg.duration.toFixed(1)}s</span> : null}
                                </div>

                                {msg.thoughts && msg.thoughts.length > 0 && (
                                    <ThoughtsAccordion
                                        thoughts={msg.thoughts}
                                        isThinking={false}
                                        duration={msg.duration || 0}
                                    />
                                )}

                                <div className="px-1 pl-2">
                                    <MarkdownRenderer content={msg.content} />
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ))}

            {isGenerating && (
                <div className="flex justify-start">
                    <div className="max-w-4xl w-full space-y-2">
                        <ThoughtsAccordion
                            thoughts={currentThoughts}
                            isThinking
                            startTime={startTime}
                        />

                        <div className="px-1 pl-2 relative">
                            {!currentResponse && (
                                <div className="flex items-center gap-2 text-text-muted animate-pulse">
                                    <MessageCircleQuestion size={14} />
                                    <span className="w-2 h-4 bg-accent-blue block rounded-sm" />
                                </div>
                            )}
                            <MarkdownRenderer content={currentResponse} />
                        </div>
                    </div>
                </div>
            )}

            {lastError && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 px-3 py-2 text-sm max-w-2xl">
                    Ошибка потока: {lastError}
                </div>
            )}

            <div ref={bottomRef} className="h-4" />
        </div>
    );
}
