import { X } from 'lucide-react';

interface AgentConfig {
    name: string;
    color: string;
    accent: string;
}

const AGENTS: AgentConfig[] = [
    { name: 'Grok', color: 'text-green-500', accent: 'accent-green-500' },
    { name: 'Harper', color: 'text-purple-500', accent: 'accent-purple-500' },
    { name: 'Benjamin', color: 'text-blue-500', accent: 'accent-blue-500' },
    { name: 'Lucas', color: 'text-red-500', accent: 'accent-red-500' },
];

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    temperatures: Record<string, number>;
    setAgentTemperature: (agent: string, temp: number) => void;
}

export default function SettingsModal({ isOpen, onClose, temperatures, setAgentTemperature }: SettingsModalProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative w-full max-w-sm bg-bg-surface border border-border-subtle rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle bg-bg-hover/50">
                    <h3 className="text-sm font-semibold text-text-primary">Настройки агентов</h3>
                    <button
                        onClick={onClose}
                        className="text-text-secondary hover:text-text-primary transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-5 space-y-6 max-h-[60vh] overflow-y-auto">

                    {AGENTS.map((agent) => (
                        <div key={agent.name} className="space-y-2">
                            <div className="flex items-center justify-between">
                                <label className={`text-sm font-medium ${agent.color}`}>{agent.name}</label>
                                <span className="text-xs font-mono text-text-muted bg-bg-hover px-2 py-0.5 rounded">
                                    {(temperatures[agent.name] ?? 0.7).toFixed(1)}
                                </span>
                            </div>

                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.1"
                                value={temperatures[agent.name] ?? 0.7}
                                onChange={(e) => setAgentTemperature(agent.name, parseFloat(e.target.value))}
                                className={`w-full h-1.5 bg-bg-active rounded-lg appearance-none cursor-pointer hover:opacity-100 opacity-80 transition-opacity focus:outline-none ${agent.accent}`}
                                style={{ accentColor: 'currentColor' }}
                            />

                            <div className="flex justify-between text-[9px] text-text-muted uppercase font-medium tracking-wide">
                                <span>Точный</span>
                                <span>Креативный</span>
                            </div>
                        </div>
                    ))}

                </div>

                {/* Footer */}
                <div className="px-4 py-3 bg-bg-message/30 border-t border-border-subtle flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-4 py-1.5 bg-text-primary text-bg-body text-sm font-medium rounded-lg hover:bg-white/90 transition-colors"
                    >
                        Готово
                    </button>
                </div>

            </div>
        </div>
    );
}
