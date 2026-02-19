import { AgentName, agentConfig } from './agent-config';
import { Thought } from '../store/useChat';

export const logTypeColorMap: Record<Thought['type'], string> = {
  thought: '#94a3b8',
  status: '#94a3b8',
  tool_use: '#4ade80',
  chatroom_send: '#f472b6',
  wait: '#facc15',
  guard_prompt: '#f87171',
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
    backgroundImage: `linear-gradient(135deg, color-mix(in srgb, ${agentColor} 20%, transparent) 0%, color-mix(in srgb, ${logColor} 14%, transparent) 100%)`,
    borderLeft: `3px solid ${agentColor}`,
    borderColor: `color-mix(in srgb, ${logColor} 45%, transparent)`,
    boxShadow: `inset 0 0 28px color-mix(in srgb, ${agentColor} 10%, transparent)`,
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
