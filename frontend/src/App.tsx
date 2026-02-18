import { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import { Menu } from 'lucide-react';

export default function App() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    return (
        <div className="flex h-screen bg-bg-body text-text-primary overflow-hidden font-sans selection:bg-accent-blue/30">
            {/* Mobile Sidebar Overlay */}
            {!isSidebarOpen && (
                <button
                    onClick={() => setIsSidebarOpen(true)}
                    className="fixed top-4 left-4 z-50 p-2 bg-bg-surface rounded-lg md:hidden"
                >
                    <Menu size={20} />
                </button>
            )}

            {/* Sidebar */}
            <div className={`${isSidebarOpen ? 'w-[280px]' : 'w-0'} transition-all duration-300 ease-in-out relative flex-shrink-0 border-r border-border-subtle bg-bg-sidebar hidden md:block`}>
                <Sidebar isOpen={isSidebarOpen} toggle={() => setIsSidebarOpen(!isSidebarOpen)} />
            </div>

            {/* Mobile Drawer */}
            {isSidebarOpen && (
                <div className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={() => setIsSidebarOpen(false)}>
                    <div className="absolute left-0 top-0 bottom-0 w-[280px] bg-bg-sidebar" onClick={e => e.stopPropagation()}>
                        <Sidebar isOpen={isSidebarOpen} toggle={() => setIsSidebarOpen(false)} />
                    </div>
                </div>
            )}

            {/* Main Content */}
            <div className="flex-1 flex flex-col h-full relative min-w-0">
                <ChatArea />
                <InputArea />
            </div>
        </div>
    );
}
