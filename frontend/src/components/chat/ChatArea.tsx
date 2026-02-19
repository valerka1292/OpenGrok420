import MessageList from './MessageList';

export default function ChatArea({ queuePrompt }: { queuePrompt: (text: string) => void }) {
  return (
    <section className="flex-1 overflow-y-auto px-4 md:px-6 pt-4" id="main-content">
      <div className="max-w-[768px] mx-auto pb-8">
        <MessageList queuePrompt={queuePrompt} />
      </div>
    </section>
  );
}
