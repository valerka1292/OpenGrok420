import { useState } from 'react';
import { Message as Msg } from '../../store/useChat';
import MarkdownRenderer from './MarkdownRenderer';
import AgentAvatar from '../shared/AgentAvatar';
import MessageActions from './MessageActions';
import { AgentName } from '../../lib/agent-config';

interface Props {
  message: Msg;
  isActive: boolean;
  canRetry?: boolean;
  onRetry?: () => void;
  onInspect?: () => void;
  onEdit?: () => void;
}

export default function Message({ message, isActive, canRetry, onRetry, onInspect, onEdit }: Props) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (message.role === 'user') {
    return (
      <article className={`ml-auto max-w-[80%] bg-bg-surface-2 border ${isActive ? 'border-agent-benjamin/60' : 'border-border-subtle'} rounded-xl px-4 py-3 group`}>
        <p className="whitespace-pre-wrap text-[14px] leading-6">{message.content}</p>
        <MessageActions copied={copied} onCopy={onCopy} onInspect={onInspect} onEdit={onEdit} />
      </article>
    );
  }

  const agent = (message.thoughts?.[message.thoughts.length - 1]?.agent || 'Grok') as AgentName;
  return (
    <article className={`group rounded-xl px-1 py-2 ${isActive ? 'bg-bg-surface-1 border border-agent-benjamin/60' : ''}`}>
      <div className="flex items-center gap-2 mb-2 text-xs text-text-secondary"><AgentAvatar agent={agent} size={20} /><span>{agent}</span></div>
      {message.error ? (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">Ошибка генерации: {message.error}</div>
      ) : (
        <div className="p-1"><MarkdownRenderer content={message.content} /></div>
      )}
      <MessageActions copied={copied} onCopy={onCopy} canRetry={canRetry} onRetry={onRetry} onInspect={onInspect} />
    </article>
  );
}
