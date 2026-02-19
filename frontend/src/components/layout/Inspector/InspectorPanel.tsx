import { useMemo, useState } from 'react';
import { SearchCode, X } from 'lucide-react';
import useChat from '../../../store/useChat';
import AgentFilter from './AgentFilter';
import Timeline from './Timeline';
import { AgentName } from '../../../lib/agent-config';

export default function InspectorPanel({ open, onClose, overlay }: { open: boolean; onClose: () => void; overlay: boolean }) {
  const { currentThoughts, messages, selectedMessageIndex, isGenerating } = useChat();
  const [filter, setFilter] = useState<AgentName | 'All'>('All');

  const sourceThoughts = useMemo(() => {
    if (isGenerating) return currentThoughts;
    if (selectedMessageIndex !== null) return messages[selectedMessageIndex]?.thoughts ?? [];
    const lastAssistant = [...messages].reverse().find((message) => message.role === 'assistant');
    return lastAssistant?.thoughts ?? [];
  }, [isGenerating, currentThoughts, selectedMessageIndex, messages]);

  const events = useMemo(() => sourceThoughts.filter((t) => (filter === 'All' ? true : t.agent === filter)), [sourceThoughts, filter]);
  if (!open) return null;

  return (
    <aside role="complementary" className={`${overlay ? 'absolute right-0 top-0 bottom-0 z-30 shadow-2xl' : 'relative'} w-[320px] max-w-full bg-bg-surface-1 border-l border-border-subtle`}>
      <div className="h-11 border-b border-border-subtle px-3 flex items-center justify-between">
        <span className="text-sm inline-flex items-center gap-2"><SearchCode size={14} />System Logs</span>
        {overlay ? <button onClick={onClose} aria-label="Close inspector" className="p-1.5 rounded border border-border-subtle hover:bg-bg-surface-2"><X size={14} /></button> : null}
      </div>
      <div className="p-3 space-y-3 h-[calc(100%-44px)] overflow-y-auto">
        <AgentFilter value={filter} onChange={setFilter} />
        {events.length ? <Timeline events={events} /> : <div className="text-sm text-text-tertiary text-center py-8 rounded border border-border-subtle">Нет данных для отображения</div>}
      </div>
    </aside>
  );
}
