import { useState, useEffect } from "react";
import {
  ChevronRight,
  ChevronDown,
  Search,
  Clock,
  MessageSquare,
  Zap,
  ArrowRight,
  Megaphone,
  Lock,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import MarkdownRenderer from "./MarkdownRenderer";
import { Thought } from "../store/useChat";
import {
  getAgentColor,
  getThoughtGradientStyle,
  parseRecipients,
} from "../lib/log-visuals";
import { agentConfig } from "../lib/agent-config";

interface ThoughtsAccordionProps {
  thoughts: Thought[];
  isThinking: boolean;
  duration?: number;
  startTime?: number;
}

export default function ThoughtsAccordion({
  thoughts,
  isThinking,
  duration = 0,
  startTime = 0,
}: ThoughtsAccordionProps) {
  const [isOpen, setIsOpen] = useState(isThinking);
  const [elapsed, setElapsed] = useState(duration);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isThinking && startTime) {
      setElapsed((Date.now() - startTime) / 1000);

      interval = setInterval(() => {
        setElapsed((Date.now() - startTime) / 1000);
      }, 100);
    } else if (!isThinking && duration) {
      setElapsed(duration);
    }
    return () => clearInterval(interval);
  }, [isThinking, startTime, duration]);

  useEffect(() => {
    if (isThinking) setIsOpen(true);
  }, [isThinking]);

  const formatTime = (secs: number) => {
    if (!secs) return "0.0s";
    if (secs < 60) return `${secs.toFixed(1)}s`;
    const m = Math.floor(secs / 60);
    const s = (secs % 60).toFixed(1);
    return `${m}m ${s}s`;
  };

  if (!thoughts.length && !isThinking) return null;

  const activeAgents = [
    ...new Set(thoughts.map((t) => t.agent).filter(Boolean) as string[]),
  ];

  return (
    <div className="mb-6 rounded-lg border border-border-subtle bg-bg-sidebar/30 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 p-3 w-full text-left bg-white/5 hover:bg-white/10 transition-colors"
      >
        <div className="flex -space-x-2">
          {activeAgents.length > 0 ? (
            activeAgents.map((name) => (
              <div
                key={name}
                style={{ backgroundColor: getAgentColor(name) }}
                className="w-5 h-5 rounded-full border border-bg-body flex items-center justify-center text-[9px] text-white font-bold"
              >
                {name[0]}
              </div>
            ))
          ) : (
            <div className="w-5 h-5 rounded-full bg-text-muted flex items-center justify-center text-[9px] text-bg-body font-bold">
              <Zap size={12} fill="currentColor" />
            </div>
          )}
        </div>

        <div className="flex-1 flex items-center justify-between">
          <span className="text-sm font-medium text-text-primary">
            {isThinking
              ? `Агенты думают ${formatTime(elapsed)}`
              : `Размышления на протяжении ${formatTime(elapsed)}`}
          </span>

          <div className="flex items-center gap-3">
            {isThinking && (
              <span className="text-xs text-text-muted font-mono bg-bg-body px-1.5 py-0.5 rounded">
                {formatTime(elapsed)}
              </span>
            )}
            {isOpen ? (
              <ChevronDown size={16} className="text-text-muted" />
            ) : (
              <ChevronRight size={16} className="text-text-muted" />
            )}
          </div>
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="p-4 space-y-4 bg-bg-body/50 text-[13px]">
              {thoughts.map((t, idx) => (
                <div
                  key={idx}
                  className="flex gap-3 animate-in fade-in slide-in-from-top-2 duration-300"
                >
                  <div className="flex-shrink-0 mt-1">
                    <div
                      style={{ backgroundColor: getAgentColor(t.agent) }}
                      className="w-6 h-6 rounded-md flex items-center justify-center text-[10px] font-bold text-white shadow-sm"
                    >
                      {t.agent ? t.agent[0] : "?"}
                    </div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div
                      style={{ color: getAgentColor(t.agent) }}
                      className="text-xs font-bold mb-1"
                    >
                      {t.agent}
                    </div>

                    {t.type === "tool_use" ? (
                      <div
                        style={getThoughtGradientStyle(t.agent, t.type)}
                        className="border rounded-lg p-2.5"
                      >
                        <div className="flex items-center gap-2 text-accent-blue mb-1">
                          <Search size={14} />
                          <span className="font-semibold text-xs">
                            Поиск инструмента
                          </span>
                        </div>
                        <div className="font-mono text-xs text-text-secondary truncate">
                          {t.tool}("{t.query}")
                        </div>
                      </div>
                    ) : t.type === "chatroom_send" ? (
                      <div
                        style={getThoughtGradientStyle(t.agent, t.type)}
                        className="border rounded-lg p-3"
                      >
                        <div className="flex items-center gap-2 text-text-secondary mb-2 pb-2 border-b border-border-subtle/50">
                          <MessageSquare size={14} />
                          {(() => {
                            const { recipients, isBroadcast } = parseRecipients(
                              t.to,
                            );
                            if (isBroadcast) {
                              return (
                                <span className="text-xs inline-flex items-center gap-1.5">
                                  <ArrowRight
                                    size={12}
                                    className="opacity-70"
                                  />
                                  <Megaphone size={12} /> Всем агентам
                                </span>
                              );
                            }

                            if (recipients.length > 1) {
                              return (
                                <span className="text-xs inline-flex items-center gap-1.5 flex-wrap">
                                  <ArrowRight
                                    size={12}
                                    className="opacity-70"
                                  />
                                  {recipients.map((recipient) => (
                                    <span
                                      key={recipient}
                                      className="px-1.5 py-0.5 rounded-full border border-border-default bg-bg-body/60 text-text-primary"
                                    >
                                      {recipient}
                                    </span>
                                  ))}
                                </span>
                              );
                            }

                            const recipient =
                              recipients[0] || t.to || "Unknown";
                            const recipientColor =
                              recipient in agentConfig
                                ? getAgentColor(recipient)
                                : "var(--text-secondary)";
                            return (
                              <span className="text-xs inline-flex items-center gap-1.5">
                                <ArrowRight size={12} className="opacity-70" />
                                <span
                                  style={{ color: recipientColor }}
                                  className="font-bold"
                                >
                                  {recipient}
                                </span>
                                <Lock size={11} className="text-amber-300" />
                              </span>
                            );
                          })()}
                        </div>
                        <div className="text-text-primary/90">
                          <MarkdownRenderer
                            content={t.content || ""}
                            className="text-xs prose-p:my-1"
                          />
                        </div>
                      </div>
                    ) : t.type === "wait" ? (
                      <div
                        style={getThoughtGradientStyle(t.agent, t.type)}
                        className="flex items-center gap-2 text-text-muted italic opacity-70 border rounded-lg p-2.5"
                      >
                        <Clock size={14} />
                        <span>Ожидает ответа...</span>
                      </div>
                    ) : (
                      <div
                        style={getThoughtGradientStyle(t.agent, t.type)}
                        className="text-text-secondary/90 leading-relaxed border rounded-lg p-2.5"
                      >
                        <MarkdownRenderer
                          content={t.content || ""}
                          className="text-xs prose-p:my-1 text-text-secondary/90"
                        />
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isThinking && (
                <div className="flex gap-2 items-center text-xs text-text-muted pl-9 pt-2">
                  <span className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-text-secondary rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-1.5 h-1.5 bg-text-secondary rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-1.5 h-1.5 bg-text-secondary rounded-full animate-bounce" />
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
