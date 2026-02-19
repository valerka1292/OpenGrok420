import { useMemo, useState } from 'react';

interface Cmd { label: string; action: () => void }

export default function CommandPalette({ open, onClose, commands }: { open: boolean; onClose: () => void; commands: Cmd[] }) {
  const [q, setQ] = useState('');
  const filtered = useMemo(() => commands.filter((c) => c.label.toLowerCase().includes(q.toLowerCase())), [commands, q]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-[var(--bg-overlay)] z-40 grid place-items-center" onClick={onClose}>
      <div className="w-full max-w-[560px] bg-bg-elevated border border-border-default rounded-xl" onClick={(e) => e.stopPropagation()}>
        <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Type a command or search..." className="w-full bg-transparent border-b border-border-subtle p-3 focus:outline-none" />
        <div className="max-h-80 overflow-y-auto p-2">{filtered.map((c) => <button key={c.label} onClick={() => { c.action(); onClose(); }} className="block w-full text-left px-2 py-2 rounded hover:bg-bg-surface-3 text-sm">{c.label}</button>)}</div>
      </div>
    </div>
  );
}
