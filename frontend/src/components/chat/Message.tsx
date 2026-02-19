import { Message as Msg } from '../../store/useChat';
import MarkdownRenderer from './MarkdownRenderer';
import AgentAvatar from '../shared/AgentAvatar';
import MessageActions from './MessageActions';
import { AgentName } from '../../lib/agent-config';

export default function Message({ message, onRetry }: { message: Msg; onRetry?: () => void }) {
  const onCopy = () => navigator.clipboard.writeText(message.content);

  if (message.role === 'user') {
    return (
      <article className="ml-12 bg-bg-surface-2/95 border border-border-subtle rounded-2xl px-4 py-3 fade-in-up group shadow-md">
        <p className="whitespace-pre-wrap text-[15px] leading-7">{message.content}</p>
        <MessageActions onCopy={onCopy} />
      </article>
    );
  }

  const agent = (message.thoughts?.[message.thoughts.length - 1]?.agent || 'Grok') as AgentName;
  const borderColorMap: Record<AgentName, string> = { Grok: 'var(--agent-grok)', Harper: 'var(--agent-harper)', Benjamin: 'var(--agent-benjamin)', Lucas: 'var(--agent-lucas)', System: 'var(--text-tertiary)' };
  return (
    <article className="fade-in-up group border-l-2 pl-4 py-1" style={{ borderColor: borderColorMap[agent] }}>
      <div className="flex items-center gap-2 mb-2 text-xs text-text-secondary"><AgentAvatar agent={agent} size={24} /><span>{agent}</span></div>
      <div className="rounded-2xl border border-border-subtle/70 bg-bg-surface-1/40 p-4">
        <MarkdownRenderer content={message.content} />
      </div>
      <MessageActions onCopy={onCopy} onRetry={onRetry} />
    </article>
  );
}
