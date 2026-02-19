import { agentConfig, AgentName } from '../../lib/agent-config';

interface Props { agent: AgentName; thinking?: boolean; size?: number }

export default function AgentAvatar({ agent, thinking = false, size = 32 }: Props) {
  const cfg = agentConfig[agent];
  const Icon = cfg.Icon;
  return (
    <div
      className={thinking ? 'agent-thinking' : undefined}
      style={{ width: size, height: size, borderRadius: 9999, background: cfg.dim, border: `1px solid ${cfg.color}`, display: 'grid', placeItems: 'center', color: cfg.color }}
    >
      <Icon size={size * 0.5} />
    </div>
  );
}
