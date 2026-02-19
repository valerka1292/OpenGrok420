import { PanelRight, PanelRightClose, Settings } from 'lucide-react';
import useChat from '../../store/useChat';

interface Props {
  online: boolean | null;
  onOpenSettings: () => void;
  inspectorOpen: boolean;
  onToggleInspector: () => void;
}

export default function StatusBar({ online, onOpenSettings, inspectorOpen, onToggleInspector }: Props) {
  const { conversations, currentConversationId } = useChat();
  const title = conversations.find((c) => c.id === currentConversationId)?.title || 'New Thread';
  const state = online === null ? ['Reconnecting...', 'bg-yellow-500'] : online ? ['Online', 'bg-emerald-500'] : ['Offline', 'bg-red-500'];

  return (
    <header className="h-12 px-4 border-b border-border-subtle bg-bg-surface-1 flex items-center justify-between gap-3">
      <div className="inline-flex items-center gap-2 text-xs text-text-secondary min-w-0">
        <span className={`w-2 h-2 rounded-full ${state[1]}`} />
        <span>{state[0]}</span>
        <span className="text-text-tertiary">•</span>
        <span className="truncate text-text-primary">{title}</span>
      </div>
      <div className="inline-flex items-center gap-2">
        <button onClick={onToggleInspector} className="p-2 rounded border border-border-subtle hover:bg-bg-surface-2" aria-label="Toggle inspector">
          {inspectorOpen ? <PanelRightClose size={15} /> : <PanelRight size={15} />}
        </button>
        <button aria-label="Settings" onClick={onOpenSettings} className="p-2 rounded border border-border-subtle hover:bg-bg-surface-2">
          <Settings size={15} />
        </button>
      </div>
    </header>
  );
}
