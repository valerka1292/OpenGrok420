import { useEffect, useMemo, useRef, useState } from 'react';
import useChat from '../../store/useChat';
import SendButton from './SendButton';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || '';

const parseNdjsonChunk = (rawLine: string) => {
  const line = rawLine.trim();
  if (!line) return null;
  const payload = line.startsWith('data:') ? line.slice(5).trim() : line;
  if (!payload) return null;
  return JSON.parse(payload);
};

export default function FloatingInput() {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const {
    addUserMessage,
    startGeneration,
    handleStreamEvent,
    isGenerating,
    stopGeneration,
    temperature,
    currentConversationId,
    lastError,
    queuedPrompt,
    consumeQueuedPrompt,
  } = useChat();
  const canSend = useMemo(() => input.trim().length > 0 && !isGenerating, [input, isGenerating]);

  const send = async (content: string) => {
    addUserMessage(content);
    startGeneration();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({ message: content, temperatures: temperature, conversation_id: currentConversationId }),
      });
      if (!response.ok || !response.body) throw new Error('Request failed');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let done = false;
      while (!done) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          const event = parseNdjsonChunk(line);
          if (!event) continue;
          handleStreamEvent(event);
          if (event.type === 'done') {
            done = true;
            break;
          }
        }
      }
      if (!done) handleStreamEvent({ type: 'done' });
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      handleStreamEvent({ type: 'error', content: 'Network/API error' });
      handleStreamEvent({ type: 'done' });
    } finally {
      abortRef.current = null;
    }
  };

  useEffect(() => {
    if (!queuedPrompt) return;
    const { prompt, autoSend } = consumeQueuedPrompt();
    if (!prompt) return;
    setInput(prompt);
    if (autoSend) {
      setInput('');
      void send(prompt);
    } else {
      textareaRef.current?.focus();
    }
  }, [queuedPrompt, consumeQueuedPrompt]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!canSend) return;
        const msg = input.trim();
        setInput('');
        void send(msg);
      }}
      className="border-t border-border-subtle bg-bg-surface-1 px-4 py-3"
    >
      <div className="max-w-[900px] mx-auto flex items-end gap-3">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            if (textareaRef.current) {
              textareaRef.current.style.height = '44px';
              textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 220)}px`;
            }
          }}
          placeholder="Введите запрос..."
          className="flex-1 h-[44px] max-h-[220px] resize-none rounded-lg border border-border-subtle bg-bg-global p-3 text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none"
        />
        <SendButton canSend={canSend} isGenerating={isGenerating} hasError={Boolean(lastError)} onStop={() => { abortRef.current?.abort(); stopGeneration('Stopped'); }} />
      </div>
    </form>
  );
}
