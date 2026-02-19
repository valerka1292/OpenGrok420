import { Settings, Thermometer } from 'lucide-react';
import useChat from '../store/useChat';

interface StatusBarProps {
    isBackendOnline: boolean | null;
    onOpenSettings: () => void;
}

const connectionState = (isBackendOnline: boolean | null) => {
    if (isBackendOnline === null) return { label: 'Checking...', color: 'bg-yellow-400' };
    if (isBackendOnline) return { label: 'Online', color: 'bg-emerald-500' };
    return { label: 'Offline', color: 'bg-red-500' };
};

export default function StatusBar({ isBackendOnline, onOpenSettings }: StatusBarProps) {
    const { currentConversationId, temperature, conversations } = useChat();
    const state = connectionState(isBackendOnline);
    const current = conversations.find((item) => item.id === currentConversationId);

    return (
        <header className="h-10 border-b border-border-subtle bg-bg-surface-1 px-4 flex items-center justify-between gap-3">
            <div className="inline-flex items-center gap-2 text-xs text-text-secondary min-w-0">
                <span className={`w-2 h-2 rounded-full ${state.color}`} />
                <span>{state.label}</span>
                <span className="text-text-tertiary hidden sm:inline">|</span>
                <span className="truncate hidden sm:inline">Thread: {current?.title ?? 'New mission'}</span>
            </div>

            <div className="flex items-center gap-3 text-xs text-text-secondary">
                <span className="inline-flex items-center gap-1">
                    <Thermometer size={13} />
                    {(temperature.Grok ?? 0.7).toFixed(1)}
                </span>
                <button
                    type="button"
                    onClick={onOpenSettings}
                    className="p-1.5 rounded-md hover:bg-bg-surface-3 transition-colors"
                    aria-label="Open settings"
                >
                    <Settings size={14} />
                </button>
            </div>
        </header>
    );
}
