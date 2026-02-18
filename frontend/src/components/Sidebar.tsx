import { MessageSquarePlus, History, Search, PanelLeftClose } from 'lucide-react';

interface SidebarProps {
    isOpen: boolean;
    toggle: () => void;
}

export default function Sidebar({ isOpen, toggle }: SidebarProps) {
    return (
        <div className="flex flex-col h-full p-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-8 px-2">
                <div className="flex items-center gap-2 group cursor-pointer">
                    <div className="w-8 h-8 bg-white/10 rounded-full flex items-center justify-center group-hover:bg-white/20 transition-colors">
                        <span className="font-bold font-mono">/</span>
                    </div>
                    {isOpen && <span className="font-semibold tracking-tight">Grok Team</span>}
                </div>
                <button onClick={toggle} className="text-text-muted hover:text-text-primary transition-colors">
                    <PanelLeftClose size={20} />
                </button>
            </div>

            {/* Actions */}
            <div className="space-y-2 mb-8">
                <button className="flex items-center gap-3 w-full px-3 py-2 bg-text-primary text-bg-body rounded-lg hover:opacity-90 transition-opacity font-medium">
                    <MessageSquarePlus size={18} />
                    {isOpen && <span>New Dialog</span>}
                </button>

                <div className="relative group">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-text-primary" />
                    <input
                        type="text"
                        placeholder="Search..."
                        className="w-full bg-bg-surface border border-border-subtle rounded-lg py-1.5 pl-9 pr-3 text-sm focus:outline-none focus:border-text-muted transition-colors placeholder:text-text-muted/50"
                    />
                </div>
            </div>

            {/* Navigation / History */}
            <div className="flex-1 overflow-y-auto -mx-2 px-2 space-y-4">
                <div>
                    <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 px-2">Recent</div>
                    <div className="space-y-0.5">
                        {[1, 2, 3].map((i) => (
                            <button key={i} className="flex items-center gap-3 w-full px-3 py-2 rounded-lg hover:bg-white/5 text-text-secondary hover:text-text-primary text-sm text-left transition-colors group">
                                <History size={16} className="text-text-muted group-hover:text-text-primary" />
                                <span className="truncate">Conversation {i}</span>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="mt-4 pt-4 border-t border-border-subtle">
                <button className="flex items-center gap-3 w-full px-2 py-2 rounded-lg hover:bg-white/5 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-accent-blue to-accent-purple flex items-center justify-center text-xs font-bold text-white">
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
