import AgentAvatar from '../shared/AgentAvatar';
import { AgentName } from '../../lib/agent-config';

export default function ThinkingIndicator({ agent }: { agent: AgentName }) {
  return (
    <div className="flex items-center gap-3">
      <AgentAvatar agent={agent} thinking />
      <div className="inline-flex gap-1">
        <span className="w-2 h-2 rounded-full bg-agent-grok [animation:dotPulse_1.4s_ease-in-out_infinite]" />
        <span className="w-2 h-2 rounded-full bg-agent-grok [animation:dotPulse_1.4s_ease-in-out_infinite_0.2s]" />
        <span className="w-2 h-2 rounded-full bg-agent-grok [animation:dotPulse_1.4s_ease-in-out_infinite_0.4s]" />
      </div>
    </div>
  );
}
