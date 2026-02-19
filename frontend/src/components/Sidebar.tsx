import { useEffect, useState } from 'react';
import { History, MessageSquarePlus, PanelLeftClose, Search, Trash2, Wifi, WifiOff } from 'lucide-react';
import useChat from '../store/useChat';

interface SidebarProps {
    isOpen: boolean;
    toggle: () => void;
    isBackendOnline: boolean | null;
}

export default function Sidebar({ isOpen, toggle, isBackendOnline }: SidebarProps) {
    const [query, setQuery] = useState('');
    const {
        conversations,
        currentConversationId,
        createConversation,
        loadConversation,
        deleteConversation,
        loadConversations,
    } = useChat();

    useEffect(() => {
        const timer = window.setTimeout(() => {
            void loadConversations(query);
        }, 200);

        return () => window.clearTimeout(timer);
    }, [query, loadConversations]);


    return (
        <nav className="flex flex-col h-full p-4">
            <div className="flex items-center justify-between mb-5 px-1">
                <div className="flex items-center gap-2 group cursor-pointer">
                    <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-agent-grok/15 border border-agent-grok/30 text-agent-grok font-bold text-xs">GT</div>
                    {isOpen && (
                        <div>
                            <div className="font-semibold tracking-tight">Grok Team</div>
                            <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Mission Control</div>
                        </div>
                    )}
                </div>
                <button onClick={toggle} className="text-text-tertiary hover:text-text-primary transition-colors" aria-label="Свернуть панель">
                    <PanelLeftClose size={20} />
                </button>
            </div>

            <div className="mb-3 px-1">
                <div className={`inline-flex w-full items-center justify-between rounded-lg border px-3 py-2 text-xs ${
                    isBackendOnline === false
                        ? 'border-red-500/35 bg-red-500/10 text-red-200'
                        : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
                }`}>
                    <span>Connection</span>
                    <span className="inline-flex items-center gap-1.5">
                        {isBackendOnline === false ? <WifiOff size={13} /> : <Wifi size={13} />}
                        {isBackendOnline === null ? 'Checking...' : isBackendOnline ? 'Online' : 'Offline'}
                    </span>
                </div>
            </div>

            <div className="space-y-2 mb-4 px-1">
                <button
                    onClick={() => void createConversation()}
                    className="flex items-center justify-between w-full px-3 py-2.5 rounded-lg border border-border-default bg-gradient-to-r from-agent-grok/15 to-agent-benjamin/15 text-sm hover:border-agent-grok"
                >
                    <span className="inline-flex items-center gap-2"><MessageSquarePlus size={16} /> New Thread</span>
                    <span className="text-[10px] text-text-tertiary">⌘N</span>
                </button>

                <label className="relative group block">
                    <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                    <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        type="text"
                        placeholder="Search threads..."
                        className="w-full bg-bg-surface-2 border border-border-subtle rounded-lg py-2 pl-9 pr-3 text-sm focus:outline-none focus:border-border-strong transition-colors placeholder:text-text-tertiary"
                    />
                </label>
            </div>

            <div className="flex-1 overflow-y-auto -mx-1 px-1 space-y-1">
                {conversations.map((item) => (
                    <div
                        key={item.id}
                        className={`group flex items-center gap-2 w-full px-2 py-2 rounded-lg border transition-colors ${
                            currentConversationId === item.id
                                ? 'bg-bg-surface-2 border-agent-grok/40'
                                : 'border-transparent hover:bg-bg-surface-2/60'
                        }`}
                    >
                        <button
                            onClick={() => void loadConversation(item.id)}
                            className="flex-1 min-w-0 flex items-center gap-3 text-left"
                        >
                            <History size={15} className="text-text-tertiary flex-shrink-0" />
                            <div className="min-w-0">
                                <div className="truncate text-sm text-text-primary">{item.title}</div>
                                <div className="truncate text-xs text-text-tertiary mt-0.5">{item.last_message || 'No messages yet'}</div>
                            </div>
                        </button>
                        <button
                            onClick={() => void deleteConversation(item.id)}
                            className="opacity-0 group-hover:opacity-100 text-text-tertiary hover:text-red-300 transition-opacity p-1"
                            title="Удалить диалог"
                        >
                            <Trash2 size={14} />
                        </button>
                    </div>
                ))}
                {conversations.length === 0 && (
                    <div className="px-3 py-5 text-xs text-text-tertiary border border-dashed border-border-subtle rounded-lg text-center">
                        No threads yet.
                    </div>
                )}
            </div>
        </nav>
    );
}
