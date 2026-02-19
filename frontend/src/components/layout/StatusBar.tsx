import { Settings, Thermometer } from 'lucide-react';
import AgentAvatar from '../shared/AgentAvatar';
import useChat from '../../store/useChat';

export default function StatusBar({ online, onOpenSettings }: { online: boolean | null; onOpenSettings: () => void }) {
  const { conversations, currentConversationId, temperature, setAgentTemperature } = useChat();
  const title = conversations.find((c) => c.id === currentConversationId)?.title || 'New Thread';
  const state = online === null ? ['Reconnecting...', 'bg-yellow-500 animate-pulse'] : online ? ['Online', 'bg-emerald-500'] : ['Offline', 'bg-red-500'];

  return (
    <header className="h-10 px-4 border-b border-border-subtle bg-bg-surface-1/95 backdrop-blur-xl flex items-center justify-between gap-2">
      <div className="inline-flex items-center gap-2 text-xs text-text-secondary min-w-0">
        <span className={`w-1.5 h-1.5 rounded-full ${state[1]}`} />
        <span>{state[0]}</span>
        <span className="truncate">Thread: "{title}"</span>
      </div>
      <div className="inline-flex items-center gap-3">
        <label className="hidden lg:inline-flex items-center gap-1 text-xs text-text-tertiary rounded-full border border-border-subtle px-2 py-1">
          <Thermometer size={12} />
          <input type="range" min={0} max={2} step={0.1} value={temperature.Grok} onChange={(e) => setAgentTemperature('Grok', Number(e.target.value))} className="w-16 accent-[var(--agent-grok)]" />
        </label>
        <div className="hidden sm:flex -space-x-2"><AgentAvatar agent="Grok" size={20} /><AgentAvatar agent="Harper" size={20} /><AgentAvatar agent="Benjamin" size={20} /><AgentAvatar agent="Lucas" size={20} /></div>
        <button aria-label="Settings" onClick={onOpenSettings} className="p-2 rounded-full border border-border-subtle hover:bg-bg-surface-3 transition-all hover:scale-105"><Settings size={14} /></button>
      </div>
    </header>
  );
}
