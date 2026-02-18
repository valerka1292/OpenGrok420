import { useState } from 'react';
import { Send, Square, SlidersHorizontal, Sparkles } from 'lucide-react';
import useChat from '../store/useChat';
import SettingsModal from './SettingsModal';

export default function InputArea() {
    const [input, setInput] = useState("");
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    const {
        addUserMessage,
        startGeneration,
        handleStreamEvent,
        isGenerating,
        stopGeneration,
        temperature,
        setAgentTemperature
    } = useChat();

    const handleSubmit = async (e: React.FormEvent | React.KeyboardEvent) => {
        e.preventDefault();
        if (!input.trim() || isGenerating) return;

        const userMsg = input;
        setInput("");
        addUserMessage(userMsg);
        startGeneration();

        try {
            // Connect to existing backend at /api/chat
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userMsg,
                    temperatures: temperature
                }),
            });

            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        // Parse NDJSON directly
                        const data = JSON.parse(line);
                        handleStreamEvent(data);
                    } catch (err) {
                        console.warn("JSON Parse Error", err, line);
                    }
                }
            }

            // Process remaining buffer
            if (buffer.trim()) {
                try {
                    const data = JSON.parse(buffer);
                    handleStreamEvent(data);
                } catch (e) { }
            }

            handleStreamEvent({ type: 'done' });

        } catch (error) {
            console.error("Stream Error", error);
            handleStreamEvent({ type: 'done' });
        }
    };

    return (
        <>
            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                temperatures={temperature}
                setAgentTemperature={setAgentTemperature}
            />

            <div className="p-4 bg-gradient-to-t from-bg-body via-bg-body to-transparent z-10 w-full max-w-4xl mx-auto">
                <form
                    onSubmit={handleSubmit}
                    className="relative bg-bg-surface/80 backdrop-blur-xl rounded-2xl border border-border-subtle shadow-xl transition-all duration-300 focus-within:border-accent-blue/30 focus-within:ring-1 focus-within:ring-accent-blue/30 hover:border-text-muted/30"
                >
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmit(e);
                            }
                        }}
                        placeholder="Спросите Grok Team..."
                        className="w-full bg-transparent text-text-primary p-4 pr-14 pl-12 focus:outline-none resize-none h-[68px] max-h-[200px] leading-relaxed placeholder:text-text-muted/60"
                    />

                    {/* Left Actions: Settings */}
                    <div className="absolute bottom-3 left-3">
                        <button
                            type="button"
                            onClick={() => setIsSettingsOpen(true)}
                            className="p-2 text-text-muted hover:text-text-primary hover:bg-white/5 rounded-lg transition-colors group"
                            title="Настройки модели"
                        >
                            <SlidersHorizontal size={18} className="group-hover:scale-105 transition-transform" />
                        </button>
                    </div>

                    {/* Right Actions: Send/Stop */}
                    <div className="absolute bottom-3 right-3 flex items-center gap-2">
                        {!isGenerating ? (
                            <button
                                type="submit"
                                disabled={!input.trim()}
                                className={`w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-200 ${input.trim()
                                        ? 'bg-text-primary text-bg-body hover:bg-white/90 shadow-lg shadow-white/10'
                                        : 'bg-white/5 text-text-muted cursor-not-allowed'
                                    }`}
                            >
                                <Send size={18} className={input.trim() ? "ml-0.5" : ""} />
                            </button>
                        ) : (
                            <button
                                type="button"
                                onClick={stopGeneration}
                                className="w-9 h-9 flex items-center justify-center rounded-lg bg-text-primary text-bg-body hover:bg-white/90 shadow-lg shadow-white/10 animate-in zoom-in-50 duration-200"
                            >
                                <Square size={14} fill="currentColor" />
                            </button>
                        )}
                    </div>
                </form>

                <div className="flex items-center justify-center gap-2 mt-4 text-[10px] uppercase tracking-widest text-text-muted font-medium opacity-60">
                    <Sparkles size={10} />
                    <span>Grok 4.20 Beta</span>
                </div>
            </div>
        </>
    );
}
