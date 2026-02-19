import { Bot, Brain, Code2, Sparkles, BarChart3, TerminalSquare } from 'lucide-react';
import useChat, { Thought } from '../store/useChat';

interface InspectorPanelProps {
    open: boolean;
}

const agentIcon = (agent?: string) => {
    switch (agent) {
        case 'Grok':
            return <Brain size={14} />;
        case 'Harper':
            return <Sparkles size={14} />;
        case 'Benjamin':
            return <BarChart3 size={14} />;
        case 'Lucas':
            return <Code2 size={14} />;
        default:
            return <TerminalSquare size={14} />;
    }
};

const eventTitle = (event: Thought) => {
    if (event.type === 'tool_use') return 'TOOL CALL';
    if (event.type === 'chatroom_send') return 'DELEGATION';
    if (event.type === 'wait') return 'WAIT';
    return 'THOUGHT';
};

export default function InspectorPanel({ open }: InspectorPanelProps) {
    const { currentThoughts, isGenerating } = useChat();

    return (
        <aside className={`${open ? 'translate-x-0' : 'translate-x-full xl:translate-x-0'} w-[340px] border-l border-border-subtle bg-bg-surface-1 transition-transform duration-300 ease-out flex-shrink-0`}>
            <div className="h-10 px-4 border-b border-border-subtle flex items-center gap-2 text-sm text-text-primary">
                <Bot size={14} /> Agent Inspector
            </div>

            <div className="h-[calc(100%-40px)] overflow-y-auto p-3 space-y-2">
                {currentThoughts.length === 0 ? (
                    <div className="h-full min-h-36 flex items-center justify-center text-center text-text-tertiary text-sm px-4">
                        {isGenerating ? 'Collecting agent activity…' : 'Agents are idle. Start a conversation to inspect reasoning.'}
                    </div>
                ) : (
                    currentThoughts.map((event, idx) => (
                        <article key={`${event.type}-${idx}`} className="border border-border-default rounded-lg bg-bg-surface-2 p-3">
                            <div className="flex items-center gap-2 text-xs text-text-secondary mb-2">
                                <span className="text-agent-benjamin">{agentIcon(event.agent)}</span>
                                <span>{event.agent ?? 'System'}</span>
                                <span className="text-text-tertiary">•</span>
                                <span className="font-mono">{eventTitle(event)}</span>
                            </div>
                            <p className="text-xs text-text-secondary leading-relaxed break-words">
                                {event.content || event.query || event.tool || 'No details provided'}
                            </p>
                        </article>
                    ))
                )}
            </div>
        </aside>
    );
}
