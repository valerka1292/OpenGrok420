import { ConversationSummary } from '../../../store/useChat';
import ThreadItem from './ThreadItem';

export default function ThreadList({ items, activeId, onOpen, onDelete }: { items: ConversationSummary[]; activeId: string | null; onOpen: (id: string) => void; onDelete: (id: string) => void }) {
  return <div className="space-y-1">{items.map((i) => <ThreadItem key={i.id} item={i} active={activeId === i.id} onOpen={() => onOpen(i.id)} onDelete={() => onDelete(i.id)} />)}</div>;
}
