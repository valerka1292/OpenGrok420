import { AgentName } from '../../../lib/agent-config';

const tabs: (AgentName | 'All')[] = ['All', 'Grok', 'Harper', 'Benjamin', 'Lucas'];

export default function AgentFilter({ value, onChange }: { value: AgentName | 'All'; onChange: (v: AgentName | 'All') => void }) {
  return (
    <div className="flex gap-1 flex-wrap rounded-xl border border-border-subtle p-1 bg-bg-surface-2/50">
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-2.5 py-1 text-xs rounded-lg border transition-all ${value === t ? 'border-border-default bg-bg-surface-3 text-text-primary' : 'border-transparent text-text-secondary hover:bg-bg-surface-3/60'}`}
        >
          {t}
        </button>
      ))}
    </div>
  );
}
