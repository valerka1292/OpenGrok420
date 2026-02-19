import { useEffect, useMemo, useState } from 'react';
import { Menu } from 'lucide-react';
import useMediaQuery from '../../hooks/useMediaQuery';
import useKeyboardShortcut from '../../hooks/useKeyboardShortcut';
import useChat from '../../store/useChat';
import StatusBar from './StatusBar';
import Sidebar from './Sidebar/Sidebar';
import ChatArea from '../chat/ChatArea';
import FloatingInput from '../input/FloatingInput';
import InspectorPanel from './Inspector/InspectorPanel';
import CommandPalette from '../overlays/CommandPalette';
import SettingsPanel from '../overlays/SettingsPanel';

const HEALTHCHECK_INTERVAL_MS = 30000;

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [commandOpen, setCommandOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const isTabletOrLess = useMediaQuery('(max-width: 1023px)');
  const isMobile = useMediaQuery('(max-width: 767px)');
  const { loadConversations, isGenerating, createConversation, clearMessages } = useChat();

  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/health');
        if (mounted) setIsBackendOnline(response.ok);
      } catch {
        if (mounted) setIsBackendOnline(false);
      }
    };
    void checkHealth();
    void loadConversations();
    const t = setInterval(() => {
      void checkHealth();
      void loadConversations();
    }, HEALTHCHECK_INTERVAL_MS);
    return () => {
      mounted = false;
      clearInterval(t);
    };
  }, [loadConversations]);

  useEffect(() => {
    if (isGenerating && isTabletOrLess) setInspectorOpen(true);
  }, [isGenerating, isTabletOrLess]);

  useKeyboardShortcut((e) => (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k', () => setCommandOpen(true));
  useKeyboardShortcut((e) => (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b', () => setSidebarOpen((v) => !v));
  useKeyboardShortcut((e) => (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'i', () => setInspectorOpen((v) => !v));
  useKeyboardShortcut((e) => (e.metaKey || e.ctrlKey) && e.key === ',', () => setSettingsOpen(true));

  const commands = useMemo(
    () => [
      { label: 'New Thread', action: () => { void createConversation(); } },
      { label: 'Toggle Sidebar', action: () => setSidebarOpen((v) => !v) },
      { label: 'Toggle Inspector', action: () => setInspectorOpen((v) => !v) },
      { label: 'Settings', action: () => setSettingsOpen(true) },
      { label: 'Clear Thread', action: () => clearMessages() },
    ],
    [createConversation, clearMessages],
  );

  return (
    <div className="h-full flex flex-col bg-bg-global text-text-primary overflow-hidden">
      <a href="#main-content" className="sr-only focus:not-sr-only">Skip to content</a>
      <StatusBar
        online={isBackendOnline}
        onOpenSettings={() => setSettingsOpen(true)}
        inspectorOpen={inspectorOpen}
        onToggleInspector={() => setInspectorOpen((v) => !v)}
      />

      <div className="flex-1 min-h-0 flex">
        {isMobile ? (
          sidebarOpen ? (
            <div className="absolute inset-0 z-30 bg-[var(--bg-overlay)]" onClick={() => setSidebarOpen(false)}>
              <aside className="w-[280px] h-full bg-bg-surface-1 border-r border-border-subtle" onClick={(e) => e.stopPropagation()}><Sidebar /></aside>
            </div>
          ) : (
            <button onClick={() => setSidebarOpen(true)} className="absolute z-20 left-3 top-12 p-2 rounded border border-border-subtle bg-bg-surface-1"><Menu size={16} /></button>
          )
        ) : (
          <aside className={`${sidebarOpen ? 'w-[260px]' : 'w-[48px]'} border-r border-border-subtle bg-bg-surface-1 transition-all overflow-hidden`}>
            {sidebarOpen ? <Sidebar /> : <div className="h-full flex items-start justify-center pt-4"><button onClick={() => setSidebarOpen(true)} className="p-2 rounded border border-border-subtle"><Menu size={16} /></button></div>}
          </aside>
        )}

        <main className="flex-1 min-w-0 flex flex-col">
          <ChatArea />
          <FloatingInput />
        </main>

        {!isTabletOrLess ? (
          inspectorOpen ? <InspectorPanel open overlay={false} onClose={() => setInspectorOpen(false)} /> : null
        ) : (
          <InspectorPanel open={inspectorOpen} overlay onClose={() => setInspectorOpen(false)} />
        )}
      </div>

      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} commands={commands} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
