import { useEffect, useRef } from 'react';
import useChat from '../store/useChat';
import ThoughtsAccordion from './ThoughtsAccordion';
import MarkdownRenderer from './MarkdownRenderer';

export default function ChatArea() {
    const { messages, isGenerating, currentResponse, currentThoughts, startTime } = useChat();
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, currentResponse, currentThoughts]);

    return (
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scroll-smooth">
            {messages.length === 0 && !isGenerating && (
                <div className="h-full flex flex-col items-center justify-center text-text-muted opacity-30 min-h-[60vh] select-none">
                    <div className="text-6xl mb-6 grayscale text-text-muted">⚡</div>
                    <h1 className="text-4xl font-bold text-text-primary tracking-tight">Grok Team</h1>
                    <p className="mt-4 text-base max-w-md text-center">Мультиагентная система совместного интеллекта</p>
                </div>
            )}

            {/* Message History */}
            {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-4xl w-full ${msg.role === 'user' ? 'ml-auto max-w-[85%] md:max-w-[70%]' : ''}`}>

                        {msg.role === 'user' ? (
                            <div className="bg-bg-message text-text-primary px-5 py-3.5 rounded-2xl rounded-tr-sm leading-relaxed whitespace-pre-wrap shadow-sm text-[15px]">
                                {msg.content}
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {/* Render thoughts for past assistant messages */}
                                {msg.thoughts && msg.thoughts.length > 0 && (
                                    <ThoughtsAccordion
                                        thoughts={msg.thoughts}
                                        isThinking={false}
                                        duration={msg.duration || 0}
                                    />
                                )}

                                {/* Final Answer */}
                                <div className="px-1 pl-2">
                                    <MarkdownRenderer content={msg.content} />
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ))}

            {/* Current Generation */}
            {isGenerating && (
                <div className="flex justify-start">
                    <div className="max-w-4xl w-full space-y-2">
                        <ThoughtsAccordion
                            thoughts={currentThoughts}
                            isThinking={true}
                            startTime={startTime}
                        />

                        <div className="px-1 pl-2 relative">
                            {/* Blinking cursor if no text yet */}
                            {(!currentResponse) && (
                                <div className="flex items-center gap-2 text-text-muted animate-pulse">
                                    <span className="w-2 h-4 bg-accent-blue block" />
                                </div>
                            )}
                            <MarkdownRenderer content={currentResponse} />
                        </div>
                    </div>
                </div>
            )}

            <div ref={bottomRef} className="h-4" />
        </div>
    );
}
