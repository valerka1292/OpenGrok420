import { Thermometer } from 'lucide-react';

export default function TemperatureSlider({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <label className="inline-flex items-center gap-2 text-xs text-text-secondary rounded-full border border-border-subtle px-2.5 py-1.5 bg-bg-surface-2/80">
      <Thermometer size={12} /> {value.toFixed(1)}
      <input type="range" min={0} max={2} step={0.1} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-20 accent-[var(--agent-grok)]" />
    </label>
  );
}
