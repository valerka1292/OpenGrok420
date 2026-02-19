import { Search } from 'lucide-react';

export default function SearchInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <label className="relative block">
      <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder="Search threads..." className="w-full bg-bg-surface-2 border border-border-subtle rounded-md py-2 pl-8 pr-3 text-sm focus:outline-none focus:border-border-default" />
    </label>
  );
}
