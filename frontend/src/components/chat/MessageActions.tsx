import { Check, Copy, Pencil, RotateCcw, Terminal } from 'lucide-react';

interface Props {
  copied: boolean;
  canRetry?: boolean;
  onCopy: () => void;
  onRetry?: () => void;
  onInspect?: () => void;
  onEdit?: () => void;
}

export default function MessageActions({ copied, canRetry, onCopy, onRetry, onInspect, onEdit }: Props) {
  return (
    <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-150 flex items-center gap-2 text-xs mt-2">
      <button type="button" onClick={onCopy} className="px-2 py-1 rounded border border-border-subtle hover:bg-bg-surface-2 inline-flex items-center gap-1">
        {copied ? <Check size={12} /> : <Copy size={12} />} {copied ? 'Copied' : 'Copy'}
      </button>
      {canRetry && onRetry ? <button type="button" onClick={onRetry} className="px-2 py-1 rounded border border-border-subtle hover:bg-bg-surface-2 inline-flex items-center gap-1"><RotateCcw size={12} />Retry</button> : null}
      {onInspect ? <button type="button" onClick={onInspect} className="px-2 py-1 rounded border border-border-subtle hover:bg-bg-surface-2 inline-flex items-center gap-1"><Terminal size={12} />Logs</button> : null}
      {onEdit ? <button type="button" onClick={onEdit} className="px-2 py-1 rounded border border-border-subtle hover:bg-bg-surface-2 inline-flex items-center gap-1"><Pencil size={12} />Edit</button> : null}
    </div>
  );
}
