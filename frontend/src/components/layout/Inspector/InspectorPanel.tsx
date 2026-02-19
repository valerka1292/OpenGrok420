import { useMemo, useState } from 'react';
import { SearchCode, X } from 'lucide-react';
import useChat from '../../../store/useChat';
import AgentFilter from './AgentFilter';
import Timeline from './Timeline';
import { AgentName } from '../../../lib/agent-config';

export default function InspectorPanel({ open, onClose, overlay }: { open: boolean; onClose: () => void; overlay: boolean }) {
  const { currentThoughts } = useChat();
  const [filter, setFilter] = useState<AgentName | 'All'>('All');
  const events = useMemo(() => currentThoughts.filter((t) => (filter === 'All' ? true : t.agent === filter)), [currentThoughts, filter]);
  if (!open) return null;

  return (
    <aside role="complementary" className={`${overlay ? 'absolute right-0 top-0 bottom-0 z-30 animate-[slideInRight_.3s_ease-out] shadow-2xl' : 'relative'} w-[360px] max-w-full bg-bg-surface-1 border-l border-border-subtle`}>
      <div className="h-10 border-b border-border-subtle px-3 flex items-center justify-between">
        <span className="text-sm inline-flex items-center gap-2"><SearchCode size={14} />Agent Inspector</span>
        <button onClick={onClose} aria-label="Close inspector" className="p-1.5 rounded-full border border-border-subtle hover:bg-bg-surface-3"><X size={14} /></button>
      </div>
      <div className="p-3 space-y-3 h-[calc(100%-40px)] overflow-y-auto">
        <AgentFilter value={filter} onChange={setFilter} />
        {events.length ? <Timeline events={events} /> : <div className="text-sm text-text-tertiary text-center py-8 rounded-2xl border border-border-subtle bg-bg-surface-2/50">Agents are idle. Start a conversation.</div>}
      </div>
    </aside>
  );
}
