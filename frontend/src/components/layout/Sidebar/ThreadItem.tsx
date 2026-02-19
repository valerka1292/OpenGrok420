import { ConversationSummary } from '../../../store/useChat';

export default function ThreadItem({ item, active, onOpen, onDelete }: { item: ConversationSummary; active: boolean; onOpen: () => void; onDelete: () => void }) {
  return (
    <div className={`group rounded-md border ${active ? 'bg-bg-surface-2 border-agent-grok/50' : 'border-transparent hover:bg-bg-surface-2'}`}>
      <div className="flex items-center">
        <button className="flex-1 text-left px-2 py-2" onClick={onOpen}>
          <div className="text-sm truncate">{item.title}</div>
          <div className="text-xs text-text-tertiary truncate">{item.last_message || 'No messages yet'}</div>
        </button>
        <button onClick={onDelete} className="px-2 text-text-tertiary opacity-0 group-hover:opacity-100">×</button>
      </div>
    </div>
  );
}
