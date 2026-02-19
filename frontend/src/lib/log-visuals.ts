import { AgentName, agentConfig } from './agent-config';
import { Thought } from '../store/useChat';

export const logTypeColorMap: Record<Thought['type'], string> = {
  thought: '#64748b',
  status: '#64748b',
  tool_use: '#8b5cf6',
  chatroom_send: '#0ea5e9',
  wait: '#f59e0b',
  guard_prompt: '#ef4444',
};

export function getAgentColor(agent?: string) {
  if (agent && agent in agentConfig) {
    return agentConfig[agent as AgentName].color;
  }
  return 'var(--text-tertiary)';
}

export function getThoughtGradientStyle(agent?: string, type: Thought['type'] = 'thought') {
  const agentColor = getAgentColor(agent);
  const logColor = logTypeColorMap[type] ?? logTypeColorMap.thought;

  return {
    backgroundImage: `linear-gradient(135deg, color-mix(in srgb, ${agentColor} 14%, transparent) 0%, color-mix(in srgb, ${logColor} 10%, transparent) 100%)`,
    borderLeft: `3px solid ${agentColor}`,
    borderColor: `color-mix(in srgb, ${logColor} 24%, transparent)`,
    boxShadow: `inset 0 0 20px color-mix(in srgb, ${agentColor} 5%, transparent)`,
  };
}

export function parseRecipients(to?: string): { recipients: string[]; isBroadcast: boolean } {
  if (!to?.trim()) return { recipients: [], isBroadcast: false };

  const normalized = to.trim();
  if (normalized.toLowerCase() === 'all') {
    return { recipients: [], isBroadcast: true };
  }

  const recipients = normalized
    .split(/[;,]/)
    .map((entry) => entry.trim())
    .filter(Boolean);

  return { recipients, isBroadcast: false };
}
