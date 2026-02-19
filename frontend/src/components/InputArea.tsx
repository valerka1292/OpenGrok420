import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  LoaderCircle,
  Send,
  Sparkles,
  Square,
  Trash2,
} from "lucide-react";
import useChat from "../store/useChat";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || "";

const parseNdjsonChunk = (rawLine: string) => {
  const line = rawLine.trim();
  if (!line) return null;

  const payload = line.startsWith("data:") ? line.slice(5).trim() : line;
  if (!payload) return null;

  return JSON.parse(payload);
};

export default function InputArea() {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    addUserMessage,
    startGeneration,
    handleStreamEvent,
    isGenerating,
    stopGeneration,
    temperature,
    currentStatus,
    lastError,
    clearMessages,
    currentConversationId,
    consumeQueuedPrompt,
  } = useChat();

  const canSubmit = useMemo(
    () => input.trim().length > 0 && !isGenerating,
    [input, isGenerating],
  );

  const resizeInput = () => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "44px";
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 264)}px`;
  };

  const handleInputChange = (value: string) => {
    setInput(value);
    resizeInput();
  };

  const handleStop = () => {
    abortControllerRef.current?.abort();
    stopGeneration("Поток остановлен пользователем");
  };

  const sendMessage = async (userMsg: string) => {
    addUserMessage(userMsg);
    startGeneration();

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          message: userMsg,
          temperatures: temperature,
          conversation_id: currentConversationId,
        }),
      });

      if (!response.ok) {
        let details = "";
        try {
          details = await response.text();
        } catch {
          details = "";
        }
        throw new Error(
          `HTTP ${response.status}: ${response.statusText}${details ? ` — ${details}` : ""}`,
        );
      }

      if (!response.body) {
        throw new Error("Пустой поток ответа от сервера");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streamCompleted = false;

      const handleParsedEvent = (line: string) => {
        const event = parseNdjsonChunk(line);
        if (!event) return;

        handleStreamEvent(event);
        if (event.type === "done") {
          streamCompleted = true;
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          try {
            handleParsedEvent(line);
            if (streamCompleted) break;
          } catch {
            // keep stream alive even with malformed lines
          }
        }

        if (streamCompleted) {
          break;
        }
      }

      const tail = buffer.trim();
      if (tail && !streamCompleted) {
        try {
          handleParsedEvent(tail);
        } catch {
          // ignored
        }
      }

      if (!streamCompleted) {
        handleStreamEvent({ type: "done" });
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        handleStreamEvent({ type: "done" });
        return;
      }

      const message =
        error instanceof Error
          ? error.message
          : "Не удалось подключиться к backend";
      handleStreamEvent({ type: "error", content: message });
      handleStreamEvent({ type: "done" });
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleSubmit = async (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    const userMsg = input.trim();
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "44px";
    }

    await sendMessage(userMsg);
  };

  useEffect(() => {
    if (isGenerating) return;
    const queued = consumeQueuedPrompt();
    if (!queued.prompt) return;
    void sendMessage(queued.prompt);
  }, [isGenerating, consumeQueuedPrompt]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "/" && document.activeElement !== textareaRef.current) {
        event.preventDefault();
        textareaRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="px-4 pb-4 pt-2 w-full">
      <div className="max-w-[768px] mx-auto">
        <div className="mb-2 flex items-center justify-between gap-3 text-xs px-1 text-text-tertiary">
          <div className="inline-flex items-center gap-2">
            {isGenerating ? (
              <LoaderCircle size={13} className="animate-spin" />
            ) : (
              <Sparkles size={13} />
            )}
            <span className="truncate">{currentStatus}</span>
          </div>
          <button
            type="button"
            onClick={clearMessages}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md hover:bg-bg-surface-2 text-text-secondary"
          >
            <Trash2 size={12} /> Clear
          </button>
        </div>

        <form
          onSubmit={handleSubmit}
          className="sticky bottom-4 bg-bg-elevated/90 backdrop-blur-xl border border-border-default rounded-2xl shadow-2xl"
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.ctrlKey) {
                e.preventDefault();
                void handleSubmit(e);
              }
            }}
            placeholder="Message your team..."
            className="w-full bg-transparent text-text-primary p-4 focus:outline-none resize-none h-[44px] max-h-[264px] leading-relaxed placeholder:text-text-tertiary"
          />

          <div className="flex items-center justify-between border-t border-border-subtle px-3 py-2">
            <div className="text-xs text-text-tertiary">
              Ctrl+Enter to send • Temp {temperature.Grok?.toFixed(1) ?? "0.7"}
            </div>
            {!isGenerating ? (
              <button
                type="submit"
                disabled={!canSubmit}
                className={`h-9 px-3 inline-flex items-center gap-2 rounded-lg transition-all ${
                  canSubmit
                    ? "bg-agent-grok/20 text-agent-grok border border-agent-grok/40 hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]"
                    : "bg-white/5 text-text-tertiary border border-border-subtle cursor-not-allowed"
                }`}
              >
                <Send size={15} /> Send
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStop}
                className="h-9 px-3 inline-flex items-center gap-2 rounded-lg bg-red-500/20 text-red-300 border border-red-400/40 animate-pulse"
              >
                <Square size={13} fill="currentColor" /> Stop
              </button>
            )}
          </div>
        </form>

        {lastError && (
          <div className="mt-2 inline-flex items-center gap-1 text-xs text-red-200 bg-red-500/10 border border-red-500/30 px-2 py-1 rounded-md">
            <AlertCircle size={12} /> {lastError}
          </div>
        )}
      </div>
    </div>
  );
}
