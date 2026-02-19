import { ArrowRight, Brain, Hammer, Lock, Megaphone, PauseCircle, TriangleAlert } from 'lucide-react';
import { Thought } from '../../../store/useChat';
import { getAgentColor, getThoughtGradientStyle, parseRecipients } from '../../../lib/log-visuals';

function getEventTitle(event: Thought) {
  if (event.type === 'tool_use') return 'TOOL USE';
  if (event.type === 'chatroom_send') return 'CHATROOM SEND';
  if (event.type === 'wait') return 'WAIT';
  if (event.type === 'guard_prompt') return 'GUARD PROMPT';
  return 'THOUGHT';
}

export default function TimelineEvent({ event }: { event: Thought }) {
  const Icon = event.type === 'tool_use'
    ? Hammer
    : event.type === 'chatroom_send'
      ? ArrowRight
      : event.type === 'wait'
        ? PauseCircle
        : event.type === 'guard_prompt'
          ? TriangleAlert
          : Brain;

  const gradientStyle = getThoughtGradientStyle(event.agent, event.type);

  return (
    <article className="border rounded-lg p-2 text-[12px] transition-all hover:translate-x-0.5" style={gradientStyle}>
      <div className="mb-1 font-mono inline-flex items-center gap-1" style={{ color: getAgentColor(event.agent) }}>
        <Icon size={12} />
        {event.agent || 'System'} · {getEventTitle(event)}
      </div>

      {event.type === 'chatroom_send' ? (
        <div className="space-y-1">
          <div className="text-text-secondary font-mono inline-flex items-center gap-1.5 flex-wrap">
            <span>{event.agent || 'System'}</span>
            <ArrowRight size={12} className="opacity-70" />
            {(() => {
              const { recipients, isBroadcast } = parseRecipients(event.to);
              if (isBroadcast) {
                return <span className="inline-flex items-center gap-1"><Megaphone size={12} />Всем агентам</span>;
              }

              if (recipients.length > 1) {
                return recipients.map((recipient) => (
                  <span key={recipient} className="px-1.5 py-0.5 rounded-full border border-border-default bg-bg-body/60 text-text-primary">
                    {recipient}
                  </span>
                ));
              }

              return (
                <span className="inline-flex items-center gap-1" style={{ color: getAgentColor(recipients[0]) }}>
                  {recipients[0] || event.to || 'Unknown'} <Lock size={10} className="text-amber-300" />
                </span>
              );
            })()}
          </div>
          <div className="text-text-primary/90 leading-relaxed font-mono mt-1.5">{event.content || '...'}</div>
        </div>
      ) : (
        <div className="text-text-primary/90 leading-relaxed font-mono mt-1.5">{event.content || event.query || event.tool || '...'}</div>
      )}
    </article>
  );
}
