import { AgentName, agentConfig } from './agent-config';
import { Thought } from '../store/useChat';

export const logTypeColorMap: Record<Thought['type'], string> = {
  thought: 'rgba(113, 113, 122, 0.5)',
  status: 'rgba(113, 113, 122, 0.5)',
  tool_use: 'rgba(59, 130, 246, 0.65)',
  chatroom_send: 'rgba(34, 211, 238, 0.65)',
  wait: 'rgba(245, 158, 11, 0.65)',
  guard_prompt: 'rgba(239, 68, 68, 0.7)',
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
    backgroundImage: `linear-gradient(90deg, color-mix(in oklab, ${agentColor} 14%, transparent) 0 70%, color-mix(in oklab, ${logColor} 16%, transparent) 70% 100%)`,
    borderLeft: `3px solid color-mix(in oklab, ${agentColor} 88%, white 12%)`,
    borderColor: 'var(--border-subtle)',
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
