import { BarChart3, Brain, Code2, Sparkles, Terminal } from 'lucide-react';

export const agentConfig = {
  Grok: { color: 'var(--agent-grok)', dim: 'var(--agent-grok-dim)', Icon: Brain, role: 'Coordinator' },
  Harper: { color: 'var(--agent-harper)', dim: 'var(--agent-harper-dim)', Icon: Sparkles, role: 'Creative' },
  Benjamin: { color: 'var(--agent-benjamin)', dim: 'var(--agent-benjamin-dim)', Icon: BarChart3, role: 'Analyst' },
  Lucas: { color: 'var(--agent-lucas)', dim: 'var(--agent-lucas-dim)', Icon: Code2, role: 'Engineer' },
  System: { color: 'var(--text-tertiary)', dim: 'rgba(107,114,128,.15)', Icon: Terminal, role: 'System' },
} as const;

export type AgentName = keyof typeof agentConfig;
