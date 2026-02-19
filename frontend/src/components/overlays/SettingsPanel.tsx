import { MonitorCog, SlidersHorizontal, X } from 'lucide-react';
import useChat from '../../store/useChat';
import { agentConfig, AgentName } from '../../lib/agent-config';

const AGENTS = ['Grok', 'Harper', 'Benjamin', 'Lucas'] as AgentName[];

export default function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { temperature, setAgentTemperature } = useChat();
  if (!open) return null;

  return (
    <aside className="fixed right-0 top-0 bottom-0 w-[460px] max-w-full bg-bg-elevated/95 backdrop-blur-2xl border-l border-border-default z-40 p-5 overflow-y-auto animate-[slideInRight_.25s_ease-out]">
      <div className="flex items-center justify-between mb-5">
        <h2 className="inline-flex items-center gap-2 text-lg font-semibold"><MonitorCog size={18} />Settings</h2>
        <button onClick={onClose} className="p-2 rounded-full border border-border-subtle hover:bg-bg-surface-3 transition-colors" aria-label="Close settings"><X size={16} /></button>
      </div>

      <div className="space-y-6 text-sm">
        <section className="rounded-2xl border border-border-subtle bg-bg-surface-1/80 p-4">
          <h3 className="text-text-secondary text-xs tracking-wider mb-2">GENERAL</h3>
          <div className="text-text-tertiary">Send with Ctrl+Enter</div>
        </section>

        <section className="rounded-2xl border border-border-subtle bg-bg-surface-1/80 p-4">
          <h3 className="text-text-secondary text-xs tracking-wider mb-3 inline-flex items-center gap-2"><SlidersHorizontal size={13} />AGENT TEMPERATURES</h3>
          <div className="space-y-4">
            {AGENTS.map((name) => {
              const cfg = agentConfig[name];
              return (
                <label key={name} className="block">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-medium" style={{ color: cfg.color }}>{name}</span>
                    <span className="text-xs text-text-tertiary font-mono">{temperature[name].toFixed(1)}</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={2}
                    step={0.1}
                    value={temperature[name]}
                    onChange={(e) => setAgentTemperature(name, Number(e.target.value))}
                    className="w-full accent-[var(--agent-grok)]"
                  />
                </label>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-border-subtle bg-bg-surface-1/80 p-4">
          <h3 className="text-text-secondary text-xs tracking-wider mb-2">APPEARANCE</h3>
          <div className="text-text-tertiary">Rounded Mission Control HUD with reduced-motion support.</div>
        </section>
      </div>
    </aside>
  );
}
