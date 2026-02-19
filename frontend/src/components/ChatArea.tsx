import { useEffect, useRef } from 'react';
import { Bot, MessageCircleQuestion, PanelRight, Sparkles } from 'lucide-react';
import useChat from '../store/useChat';
import MarkdownRenderer from './MarkdownRenderer';

interface ChatAreaProps {
    onToggleInspector: () => void;
}

const AGENT_BORDER: Record<string, string> = {
    Grok: 'border-agent-grok',
    Harper: 'border-agent-harper',
    Benjamin: 'border-agent-benjamin',
    Lucas: 'border-agent-lucas',
};

export default function ChatArea({ onToggleInspector }: ChatAreaProps) {
    const { messages, isGenerating, currentResponse, currentThoughts, lastError } = useChat();
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, currentResponse, currentThoughts]);

    const lastThoughtAgent = currentThoughts[currentThoughts.length - 1]?.agent ?? 'Grok';

    return (
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-5">
            <div className="max-w-[768px] mx-auto space-y-7">
                <div className="flex justify-end xl:hidden">
                    <button
                        type="button"
                        onClick={onToggleInspector}
                        className="inline-flex items-center gap-2 text-xs text-text-secondary border border-border-default rounded-md px-2.5 py-1.5 hover:bg-bg-surface-2"
                    >
                        <PanelRight size={13} /> Inspector
                    </button>
                </div>

                {messages.length === 0 && !isGenerating && (
                    <div className="h-full flex flex-col items-center justify-center text-text-secondary min-h-[56vh] select-none text-center">
                        <div className="w-16 h-16 rounded-2xl border border-border-default flex items-center justify-center mb-5 bg-bg-surface-1">
                            <Sparkles size={28} className="text-agent-grok" />
                        </div>
                        <h1 className="text-3xl font-semibold tracking-tight text-text-primary">Welcome to Mission Control</h1>
                        <p className="mt-3 text-sm max-w-xl text-text-secondary">Your AI team is standing by. Start a thread and coordinate agents from a single command center.</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <article key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`w-full ${msg.role === 'user' ? 'max-w-[92%] md:max-w-[86%]' : ''}`}>
                            {msg.role === 'user' ? (
                                <div className="bg-bg-surface-2 text-text-primary px-5 py-3.5 rounded-xl leading-relaxed whitespace-pre-wrap text-[15px] border border-border-subtle ml-8">
                                    {msg.content}
                                </div>
                            ) : (
                                <div className="space-y-2 border-l-2 pl-4 border-agent-grok">
                                    <div className="inline-flex items-center gap-2 text-xs text-text-tertiary">
                                        <Bot size={14} />
                                        <span>Agent response</span>
                                    </div>
                                    <MarkdownRenderer content={msg.content} />
                                </div>
                            )}
                        </div>
                    </article>
                ))}

                {isGenerating && (
                    <div className="flex justify-start">
                        <div className={`w-full border-l-2 pl-4 ${AGENT_BORDER[lastThoughtAgent] ?? 'border-agent-grok'}`}>
                            {!currentResponse ? (
                                <div className="flex items-center gap-2 text-text-secondary">
                                    <MessageCircleQuestion size={14} />
                                    <span className="inline-flex gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-agent-grok animate-pulse" />
                                        <span className="w-1.5 h-1.5 rounded-full bg-agent-grok animate-pulse [animation-delay:200ms]" />
                                        <span className="w-1.5 h-1.5 rounded-full bg-agent-grok animate-pulse [animation-delay:400ms]" />
                                    </span>
                                </div>
                            ) : (
                                <MarkdownRenderer content={`${currentResponse}█`} />
                            )}
                        </div>
                    </div>
                )}

                {lastError && (
                    <div className="rounded-lg border border-red-500/40 bg-red-500/10 text-red-200 px-3 py-2 text-sm">
                        Stream error: {lastError}
                    </div>
                )}

                <div ref={bottomRef} className="h-4" />
            </div>
        </div>
    );
}
