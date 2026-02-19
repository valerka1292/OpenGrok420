import { AlertTriangle, Send, Square } from 'lucide-react';

interface Props { canSend: boolean; isGenerating: boolean; hasError: boolean; onStop: () => void }
export default function SendButton({ canSend, isGenerating, hasError, onStop }: Props) {
  if (isGenerating) return <button type="button" onClick={onStop} className="h-10 px-4 rounded-full bg-red-500/20 text-red-300 border border-red-400/30 inline-flex items-center gap-1.5 animate-pulse"><Square size={13} fill="currentColor" />Stop</button>;
  if (hasError) return <button type="submit" className="h-10 px-4 rounded-full bg-amber-500/20 text-amber-200 border border-amber-500/30 inline-flex items-center gap-1.5"><AlertTriangle size={13} />Retry</button>;
  return <button type="submit" disabled={!canSend} className={`h-10 px-4 rounded-full inline-flex items-center gap-1.5 transition-all duration-150 ${canSend ? 'bg-agent-grok/20 text-agent-grok border border-agent-grok/30 hover:shadow-[0_0_24px_rgba(16,185,129,.35)] hover:-translate-y-0.5' : 'bg-white/5 text-text-tertiary border border-border-subtle'}`}><Send size={14} />Send</button>;
}
