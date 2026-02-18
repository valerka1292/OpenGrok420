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
        <div className="flex flex-col h-full p-4">
            <div className="flex items-center justify-between mb-6 px-2">
                <div className="flex items-center gap-2 group cursor-pointer">
                    <div className="w-8 h-8 bg-gradient-to-tr from-accent-blue/80 to-agent-harper/80 rounded-xl flex items-center justify-center group-hover:opacity-90 transition-opacity shadow-lg shadow-accent-blue/20">
                        <span className="font-bold font-mono text-white">GT</span>
                    </div>
                    {isOpen && <span className="font-semibold tracking-tight">Grok Team</span>}
                </div>
                <button onClick={toggle} className="text-text-muted hover:text-text-primary transition-colors" aria-label="Свернуть панель">
                    <PanelLeftClose size={20} />
                </button>
            </div>

            <div className="mb-4 px-2">
                <div
                    className={`inline-flex w-full items-center justify-between rounded-xl border px-3 py-2 text-xs ${isBackendOnline === false
                        ? 'border-red-500/35 bg-red-500/10 text-red-200'
                        : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
                        }`}
                >
                    <span className="font-medium">Backend</span>
                    <span className="inline-flex items-center gap-1.5">
                        {isBackendOnline === false ? <WifiOff size={13} /> : <Wifi size={13} />}
                        {isBackendOnline === null ? 'Проверка…' : isBackendOnline ? 'Online' : 'Offline'}
                    </span>
                </div>
            </div>

            <div className="space-y-2 mb-6">
                <button
                    onClick={() => void createConversation()}
                    className="flex items-center gap-3 w-full px-3 py-2.5 bg-text-primary text-bg-body rounded-xl hover:opacity-90 transition-opacity font-medium"
                >
                    <MessageSquarePlus size={18} />
                    {isOpen && <span>Новый диалог</span>}
                </button>

                <div className="relative group">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-text-primary" />
                    <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        type="text"
                        placeholder="Поиск по истории..."
                        className="w-full bg-bg-surface border border-border-subtle rounded-xl py-2 pl-9 pr-3 text-sm focus:outline-none focus:border-text-muted transition-colors placeholder:text-text-muted/50"
                    />
                </div>
            </div>

            <div className="flex-1 overflow-y-auto -mx-2 px-2 space-y-4">
                <div>
                    <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 px-2">Недавние</div>
                    <div className="space-y-1">
                        {conversations.map((item) => (
                            <div
                                key={item.id}
                                className={`group flex items-center gap-2 w-full px-2 py-2 rounded-xl transition-colors ${currentConversationId === item.id ? 'bg-white/10' : 'hover:bg-white/5'}`}
                            >
                                <button
                                    onClick={() => void loadConversation(item.id)}
                                    className="flex-1 min-w-0 flex items-center gap-3 text-text-secondary hover:text-text-primary text-sm text-left"
                                >
                                    <History size={16} className="text-text-muted group-hover:text-text-primary flex-shrink-0" />
                                    <div className="min-w-0">
                                        <div className="truncate text-text-primary/90">{item.title}</div>
                                        <div className="truncate text-xs text-text-muted mt-0.5">{item.last_message || 'Пока без сообщений'}</div>
                                    </div>
                                </button>
                                <button
                                    onClick={() => void deleteConversation(item.id)}
                                    className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-red-300 transition-opacity p-1"
                                    title="Удалить диалог"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))}
                        {conversations.length === 0 && (
                            <div className="px-3 py-5 text-xs text-text-muted border border-dashed border-border-subtle rounded-xl text-center">
                                История пока пуста. Начните новый диалог.
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="mt-4 pt-4 border-t border-border-subtle">
                <button className="flex items-center gap-3 w-full px-2 py-2 rounded-xl hover:bg-white/5 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-accent-blue to-agent-harper flex items-center justify-center text-xs font-bold text-white">
                        M
                    </div>
                    {isOpen && (
                        <div className="text-left">
                            <div className="text-sm font-medium">MyJoker003</div>
                            <div className="text-xs text-text-muted">Pro Plan</div>
                        </div>
                    )}
                </button>
            </div>
        </div>
    );
}
