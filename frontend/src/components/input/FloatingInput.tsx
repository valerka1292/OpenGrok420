import { useEffect, useMemo, useRef, useState } from 'react';
import useChat from '../../store/useChat';
import AgentSelector from './AgentSelector';
import TemperatureSlider from './TemperatureSlider';
import SendButton from './SendButton';
import { AgentName } from '../../lib/agent-config';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || '';
const ALL_AGENTS: AgentName[] = ['Grok', 'Harper', 'Benjamin', 'Lucas'];

const parseNdjsonChunk = (rawLine: string) => {
  const line = rawLine.trim();
  if (!line) return null;
  const payload = line.startsWith('data:') ? line.slice(5).trim() : line;
  if (!payload) return null;
  return JSON.parse(payload);
};

export default function FloatingInput({ queuedPrompt, consumeQueuedPrompt }: { queuedPrompt: string | null; consumeQueuedPrompt: () => void }) {
  const [input, setInput] = useState('');
  const [agent, setAgent] = useState<AgentName>('Grok');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const { addUserMessage, startGeneration, handleStreamEvent, isGenerating, stopGeneration, temperature, setAgentTemperature, currentConversationId, lastError } = useChat();
  const canSend = useMemo(() => input.trim().length > 0 && !isGenerating, [input, isGenerating]);

  useEffect(() => {
    if (queuedPrompt) {
      setInput(queuedPrompt);
      consumeQueuedPrompt();
      textareaRef.current?.focus();
    }
  }, [queuedPrompt, consumeQueuedPrompt]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== textareaRef.current) {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const send = async (content: string) => {
    addUserMessage(content);
    startGeneration();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ message: content, temperatures: temperature, conversation_id: currentConversationId }),
      });
      if (!response.ok || !response.body) throw new Error('Request failed');
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ''; let done = false;
      while (!done) {
        const chunk = await reader.read(); if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const lines = buffer.split('\n'); buffer = lines.pop() ?? '';
        for (const line of lines) {
          const event = parseNdjsonChunk(line); if (!event) continue;
          handleStreamEvent(event); if (event.type === 'done') { done = true; break; }
        }
      }
      if (!done) handleStreamEvent({ type: 'done' });
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      handleStreamEvent({ type: 'error', content: 'Network/API error' });
      handleStreamEvent({ type: 'done' });
    } finally { abortRef.current = null; }
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); if (!canSend) return; const msg = input.trim(); setInput(''); void send(msg); }} className="sticky bottom-4 max-w-[768px] mx-auto w-full bg-bg-elevated/95 backdrop-blur-xl border border-border-default rounded-[20px] shadow-[0_8px_32px_rgba(0,0,0,.6),0_0_40px_rgba(59,130,246,.08)] transition-all focus-within:border-agent-grok/60">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => { setInput(e.target.value); if (textareaRef.current) { textareaRef.current.style.height = '44px'; textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 264)}px`; } }}
        onKeyDown={(e) => { if (e.key === 'Enter' && e.ctrlKey) { e.preventDefault(); if (canSend) { const msg = input.trim(); setInput(''); void send(msg); } } }}
        placeholder="Message your team..."
        className="w-full h-[44px] max-h-[264px] resize-none bg-transparent p-4 text-[15px] md:text-[15px] text-text-primary placeholder:text-text-tertiary focus:outline-none"
      />
      <div className="border-t border-border-subtle px-3 py-2 flex items-center justify-between gap-2 flex-wrap">
        <div className="inline-flex items-center gap-2 flex-wrap">
          <AgentSelector value={agent} onChange={setAgent} />
          <TemperatureSlider value={temperature[agent]} onChange={(v) => setAgentTemperature(agent, v)} />
          {ALL_AGENTS.map((name) => (
            <button key={name} type="button" onClick={() => setAgent(name)} className={`px-2.5 py-1 rounded-full text-[11px] border ${agent === name ? 'border-border-default bg-bg-surface-3 text-text-primary' : 'border-border-subtle text-text-tertiary hover:text-text-secondary'}`}>
              {name}: {temperature[name].toFixed(1)}
            </button>
          ))}
        </div>
        <SendButton canSend={canSend} isGenerating={isGenerating} hasError={Boolean(lastError)} onStop={() => { abortRef.current?.abort(); stopGeneration('Stopped'); }} />
      </div>
      <p className="px-3 pb-3 text-[11px] text-text-tertiary">Grok Team can make mistakes. Verify important info.</p>
    </form>
  );
}
