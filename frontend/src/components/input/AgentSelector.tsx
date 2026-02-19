import { ChevronDown } from 'lucide-react';
import { AgentName } from '../../lib/agent-config';

export default function AgentSelector({ value, onChange }: { value: AgentName; onChange: (v: AgentName) => void }) {
  return (
    <label className="relative">
      <select value={value} onChange={(e) => onChange(e.target.value as AgentName)} className="appearance-none bg-bg-surface-2/80 text-xs text-text-secondary border border-border-subtle rounded-full pl-3 pr-7 py-1.5 hover:border-border-default transition-colors">
        <option>Grok</option><option>Harper</option><option>Benjamin</option><option>Lucas</option>
      </select>
      <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none" />
    </label>
  );
}
