import { ArrowRightLeft, Brain, Hammer, PauseCircle } from 'lucide-react';
import { Thought } from '../../../store/useChat';

export default function TimelineEvent({ event }: { event: Thought }) {
  const cls = event.type === 'tool_use' ? 'bg-blue-500/10 border-blue-400/30' : event.type === 'chatroom_send' ? 'bg-fuchsia-500/10 border-fuchsia-400/30' : 'bg-bg-surface-2/40 border-border-subtle';
  const Icon = event.type === 'tool_use' ? Hammer : event.type === 'chatroom_send' ? ArrowRightLeft : event.type === 'wait' ? PauseCircle : Brain;
  return (
    <article className={`border rounded-xl p-3 text-xs transition-all hover:translate-x-0.5 ${cls}`}>
      <div className="text-text-tertiary mb-1 font-mono inline-flex items-center gap-1"><Icon size={12} />{event.agent || 'System'} · {event.type.toUpperCase()}</div>
      <div className="text-text-secondary leading-relaxed">{event.content || event.query || event.tool || '...'}</div>
    </article>
  );
}
