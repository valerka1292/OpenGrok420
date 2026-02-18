import { useEffect, useState } from 'react';
import { Menu } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import useChat from './store/useChat';

const HEALTHCHECK_INTERVAL_MS = 30000;

export default function App() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
    const { loadConversations } = useChat();

    useEffect(() => {
        let isMounted = true;

        const checkHealth = async () => {
            try {
                const response = await fetch('/api/health');
                if (!isMounted) return;
                setIsBackendOnline(response.ok);
            } catch {
                if (!isMounted) return;
                setIsBackendOnline(false);
            }
        };

        void checkHealth();
        void loadConversations();
        const timer = window.setInterval(() => {
            void checkHealth();
            void loadConversations();
        }, HEALTHCHECK_INTERVAL_MS);

        return () => {
            isMounted = false;
            window.clearInterval(timer);
        };
    }, [loadConversations]);

    return (
        <div className="flex h-screen bg-bg-body text-text-primary overflow-hidden font-sans selection:bg-accent-blue/30">
            {!isSidebarOpen && (
                <button
                    onClick={() => setIsSidebarOpen(true)}
                    className="fixed top-4 left-4 z-50 p-2.5 bg-bg-surface/90 backdrop-blur-lg border border-border-subtle rounded-xl md:hidden shadow-lg"
                    aria-label="Открыть сайдбар"
                >
                    <Menu size={20} />
                </button>
            )}

            <aside className={`${isSidebarOpen ? 'w-[300px]' : 'w-0'} transition-all duration-300 ease-in-out relative flex-shrink-0 border-r border-border-subtle bg-bg-sidebar hidden md:block`}>
                <Sidebar
                    isOpen={isSidebarOpen}
                    toggle={() => setIsSidebarOpen(!isSidebarOpen)}
                    isBackendOnline={isBackendOnline}
                />
            </aside>

            {isSidebarOpen && (
                <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden" onClick={() => setIsSidebarOpen(false)}>
                    <div className="absolute left-0 top-0 bottom-0 w-[300px] bg-bg-sidebar border-r border-border-subtle" onClick={(e) => e.stopPropagation()}>
                        <Sidebar
                            isOpen={isSidebarOpen}
                            toggle={() => setIsSidebarOpen(false)}
                            isBackendOnline={isBackendOnline}
                        />
                    </div>
                </div>
            )}

            <main className="flex-1 flex flex-col h-full relative min-w-0 bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.08),transparent_36%)]">
                <ChatArea />
                <InputArea />
            </main>
        </div>
    );
}
