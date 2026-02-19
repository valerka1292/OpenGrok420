import { Copy, MoreHorizontal, RotateCcw } from 'lucide-react';

interface Props { onCopy: () => void; onRetry?: () => void }

export default function MessageActions({ onCopy, onRetry }: Props) {
  return (
    <div className="opacity-0 group-hover:opacity-100 md:group-hover:opacity-100 transition-opacity duration-150 flex items-center gap-2 text-xs mt-2">
      <button type="button" onClick={onCopy} className="px-2 py-1 rounded-full border border-border-subtle hover:bg-bg-surface-3 inline-flex items-center gap-1"><Copy size={12} />Copy</button>
      {onRetry ? <button type="button" onClick={onRetry} className="px-2 py-1 rounded-full border border-border-subtle hover:bg-bg-surface-3 inline-flex items-center gap-1"><RotateCcw size={12} />Retry</button> : null}
      <button type="button" className="px-2 py-1 rounded-full border border-border-subtle hover:bg-bg-surface-3 inline-flex items-center gap-1"><MoreHorizontal size={12} />More</button>
    </div>
  );
}
