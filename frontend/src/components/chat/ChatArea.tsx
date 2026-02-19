import MessageList from './MessageList';

export default function ChatArea() {
  return (
    <section className="flex-1 overflow-y-auto px-4 md:px-8 pt-4" id="main-content">
      <div className="max-w-[900px] mx-auto pb-28">
        <MessageList />
      </div>
    </section>
  );
}
