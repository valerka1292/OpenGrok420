import useChat from '../../store/useChat';
import Message from './Message';
import EmptyState from './EmptyState';
import ThinkingIndicator from './ThinkingIndicator';
import MarkdownRenderer from './MarkdownRenderer';
import StreamingCursor from './StreamingCursor';

export default function MessageList() {
  const {
    messages,
    isGenerating,
    currentResponse,
    selectedMessageIndex,
    setSelectedMessageIndex,
    retryLastAssistant,
    queuePrompt,
  } = useChat();

  const lastAssistantIndex = [...messages].map((m, idx) => ({ m, idx })).reverse().find((item) => item.m.role === 'assistant')?.idx;

  if (!messages.length && !isGenerating) return <EmptyState onPick={(text) => queuePrompt(text)} />;

  return (
    <div className="space-y-4" role="log" aria-live="polite">
      {messages.map((message, idx) => (
        <Message
          key={`${message.created_at ?? 'msg'}-${idx}`}
          message={message}
          isActive={selectedMessageIndex === idx}
          canRetry={idx === lastAssistantIndex}
          onRetry={idx === lastAssistantIndex ? retryLastAssistant : undefined}
          onInspect={() => setSelectedMessageIndex(idx)}
          onEdit={message.role === 'user' ? () => queuePrompt(message.content) : undefined}
        />
      ))}
      {isGenerating ? (
        <div className="border-l-2 border-agent-grok pl-4">
          {!currentResponse ? <ThinkingIndicator agent="Grok" /> : <div><MarkdownRenderer content={currentResponse} /><StreamingCursor /></div>}
        </div>
      ) : null}
    </div>
  );
}
