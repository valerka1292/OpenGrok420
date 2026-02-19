import { useEffect, useState } from 'react';
import { MessageSquarePlus } from 'lucide-react';
import useChat from '../../../store/useChat';
import SearchInput from './SearchInput';
import ThreadList from './ThreadList';

export default function Sidebar() {
  const [query, setQuery] = useState('');
  const { conversations, currentConversationId, createConversation, loadConversation, deleteConversation, loadConversations } = useChat();

  useEffect(() => {
    const t = setTimeout(() => { void loadConversations(query); }, 200);
    return () => clearTimeout(t);
  }, [query, loadConversations]);

  return (
    <nav className="h-full p-3 flex flex-col gap-3" role="navigation">
      <div>
        <div className="text-sm font-semibold">GROK TEAM</div>
        <div className="text-[10px] text-text-tertiary">v3.0 Mission Control</div>
      </div>
      <button onClick={() => void createConversation()} className="new-thread-btn text-sm inline-flex items-center justify-between"><span className="inline-flex items-center gap-2"><MessageSquarePlus size={14} />New Thread</span><span className="text-[10px]">⌘N</span></button>
      <SearchInput value={query} onChange={setQuery} />
      <div className="flex-1 overflow-y-auto">
        <ThreadList items={conversations} activeId={currentConversationId} onOpen={(id) => void loadConversation(id)} onDelete={(id) => void deleteConversation(id)} />
      </div>
    </nav>
  );
}
