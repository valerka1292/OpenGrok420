import { useMemo } from 'react';
import useChat from '../../store/useChat';
import Message from './Message';
import EmptyState from './EmptyState';
import ThinkingIndicator from './ThinkingIndicator';
import MarkdownRenderer from './MarkdownRenderer';
import StreamingCursor from './StreamingCursor';

export default function MessageList({ queuePrompt }: { queuePrompt: (text: string) => void }) {
  const { messages, isGenerating, currentResponse, currentThoughts } = useChat();
  const retryPrompt = useMemo(() => {
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
    return lastUser?.content;
  }, [messages]);

  if (!messages.length && !isGenerating) {
    return <EmptyState onPick={queuePrompt} />;
  }

  return (
    <div className="space-y-6" role="log" aria-live="polite">
      {messages.map((message, idx) => <Message key={idx} message={message} onRetry={retryPrompt ? () => queuePrompt(retryPrompt) : undefined} />)}
      {isGenerating ? (
        <div className="border-l-2 border-agent-grok pl-4">
          {!currentResponse ? <ThinkingIndicator agent="Grok" /> : <div><MarkdownRenderer content={currentResponse} /><StreamingCursor /></div>}
        </div>
      ) : null}
      {currentThoughts.length > 0 ? null : null}
    </div>
  );
}
