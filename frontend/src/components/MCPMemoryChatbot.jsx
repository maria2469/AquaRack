import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BrainCircuit, Search, Send, X, Bot, Sparkles, Database,
  ShieldCheck, Droplets, Zap, ChevronRight, RefreshCw, MessageSquare,
  AlertCircle, ChevronDown, Minimize2, Radio, HardDriveDownload
} from "lucide-react";
import { postMemorySearch } from "../lib/api";

const SUGGESTIONS = [
  { icon: Zap, label: "high GPU thermal spike at 39°C" },
  { icon: Droplets, label: "water saving strategy for 95% GPU load" },
  { icon: AlertCircle, label: "root cause of evaporative cooling degradation" },
  { icon: Database, label: "historical memory matches for Rack 1-10" },
];

// FIX: retrieval_method comes back as "cockroach_vector" | "fallback_recent"
// from the backend. Map to a small badge so the UI is honest about whether
// this was a real semantic vector match or just "most recent rows".
function RetrievalBadge({ method, embeddingModel, searchedRecords }) {
  const isVector = method === "cockroach_vector";
  return (
    <div
      className={`flex items-center gap-1.5 text-[10px] font-mono px-2 py-1 rounded-full border ${isVector
          ? "bg-signal/10 border-signal/30 text-signal"
          : "bg-amber/10 border-amber/30 text-amber"
        }`}
      title={`embedding model: ${embeddingModel || "unknown"} · searched ${searchedRecords ?? 0} records`}
    >
      {isVector ? <Radio size={11} /> : <HardDriveDownload size={11} />}
      <span>
        {isVector ? "CockroachDB Vector Search" : "Fallback (most recent)"}
      </span>
    </div>
  );
}

export default function MCPMemoryChatbot({ isOpen, setIsOpen }) {
  const [messages, setMessages] = useState([
    {
      id: "welcome-1",
      sender: "bot",
      text: "👋 Welcome to **CockroachDB Managed MCP Memory Assistant**!",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      detail: "I execute vector similarity searches over our CockroachDB distributed index to retrieve historical thermal incidents, root causes, and water optimization recommendations.",
      suggestions: SUGGESTIONS,
    },
  ]);
  const [input, setInput] = useState("");
  const [searching, setSearching] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen, messages]);

  const handleQuery = async (queryText) => {
    const text = queryText || input;
    if (!text.trim() || searching) return;

    const userMsgId = `user-${Date.now()}`;
    const userMessage = {
      id: userMsgId,
      sender: "user",
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const loadingBotMsgId = `bot-${Date.now()}`;
    const loadingMessage = {
      id: loadingBotMsgId,
      sender: "bot",
      loading: true,
      text: `Executing vector search over CockroachDB distributed index for "${text.trim()}"…`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setInput("");
    setSearching(true);

    try {
      const res = await postMemorySearch(text.trim(), 5);

      // FIX: backend returns { similar_incidents: { matches: [...], retrieval_method, embedding_model, searched_records },
      // previous_recommendations: { matches: [...], ... } } -- these are objects, not arrays.
      // Previously the code did `(res.similar_incidents || []).map(...)`, which silently
      // produced [] via the `|| []` fallback since an object is truthy but has no .map,
      // so it would have actually thrown before ever reaching the .map. Unwrap .matches first.
      const incidentBlock = res.similar_incidents || {};
      const recommendationBlock = res.previous_recommendations || {};

      const incidents = (incidentBlock.matches || []).map((i) => ({
        memory_id: i.incident_id || i.id,
        type: "incident",
        summary_text: i.description || i.summary,
        root_cause: i.root_cause || null, // FIX: no more fake "Thermal spike under load" filler
        similarity: i.similarity, // FIX: no more ?? 0.94 fabricated fallback
        severity: i.severity,
        created_at: i.created_at,
      }));

      const recs = (recommendationBlock.matches || []).map((r) => ({
        memory_id: r.recommendation_id || r.id,
        type: "recommendation",
        summary_text: r.recommendation_text || r.summary || r.text,
        expected_water_saving: r.expected_water_saving ?? null, // FIX: no fabricated 17.8
        confidence: r.confidence ?? null,
        similarity: r.similarity,
        created_at: r.created_at,
      }));

      const memories = [...incidents, ...recs];

      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id === loadingBotMsgId) {
            return {
              ...msg,
              loading: false,
              text: memories.length > 0
                ? `Found **${memories.length} relevant memory matches** in CockroachDB distributed vector index for "${text.trim()}":`
                : `No exact vector matches found for "${text.trim()}".`,
              memories,
              retrieval: {
                incidents: {
                  method: incidentBlock.retrieval_method,
                  model: incidentBlock.embedding_model,
                  searched: incidentBlock.searched_records,
                },
                recommendations: {
                  method: recommendationBlock.retrieval_method,
                  model: recommendationBlock.embedding_model,
                  searched: recommendationBlock.searched_records,
                },
              },
            };
          }
          return msg;
        })
      );
    } catch (err) {
      console.error("MCP Memory Chatbot error:", err);
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id === loadingBotMsgId) {
            return {
              ...msg,
              loading: false,
              error: true,
              text: `Could not reach CockroachDB MCP Memory backend for "${text.trim()}". Please check the connection and try again.`,
              memories: [],
            };
          }
          return msg;
        })
      );
    } finally {
      setSearching(false);
    }
  };

  const handleClear = () => {
    setMessages([
      {
        id: "welcome-1",
        sender: "bot",
        text: "👋 Welcome to **CockroachDB Managed MCP Memory Assistant**!",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        detail: "I execute vector similarity searches over our CockroachDB distributed index to retrieve historical thermal incidents, root causes, and water optimization recommendations.",
        suggestions: SUGGESTIONS,
      },
    ]);
  };

  return (
    <>
      {/* FLOATING ACTION ICON TRIGGER */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.92 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-full bg-gradient-to-r from-coolant via-flow to-signal border border-frost/30 shadow-[0_0_30px_rgba(34,211,238,0.5)] text-abyss font-bold text-xs tracking-wide transition-all group backdrop-blur-md"
            title="Open CockroachDB MCP Memory Chatbot"
          >
            <div className="relative flex items-center justify-center">
              <Bot size={22} className="text-abyss" />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-signal animate-ping" />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-signal" />
            </div>
            <span className="font-heading font-extrabold text-abyss text-xs">MCP Memory AI</span>
          </motion.button>
        )}
      </AnimatePresence>

      {/* OVERLAY BACKDROP & RIGHT-SIDE SLIDE-OVER OVERLAY DRAWER */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* BACKDROP */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 bg-abyss/60 backdrop-blur-sm z-40"
            />

            {/* RIGHT SIDE CHAT OVERLAY PANEL */}
            <motion.div
              initial={{ x: "100%", opacity: 0.5 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "100%", opacity: 0 }}
              transition={{ type: "spring", damping: 28, stiffness: 280 }}
              className="fixed top-0 right-0 h-full w-full sm:w-[440px] md:w-[480px] z-50 bg-abyss/95 border-l border-flow/30 shadow-[0_0_50px_rgba(0,0,0,0.9)] flex flex-col backdrop-blur-2xl"
            >
              {/* CHAT HEADER */}
              <div className="flex items-center justify-between px-5 py-4 bg-hall-2/90 border-b border-rack flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-coolant/15 text-coolant border border-coolant/30 flex-shrink-0">
                    <Bot size={20} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-heading font-semibold text-base text-frost">
                        MCP Memory Assistant
                      </h3>
                    </div>
                    <p className="text-xs text-mist font-mono flex items-center gap-1.5 mt-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
                      CockroachDB Distributed Vector Search
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={handleClear}
                    className="p-2 rounded-lg text-mist hover:text-fog hover:bg-hall-3 transition-colors"
                    title="Clear Conversation"
                  >
                    <RefreshCw size={14} />
                  </button>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-2 rounded-lg text-mist hover:text-frost hover:bg-hall-3 transition-colors"
                    title="Close Overlay"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>

              {/* CHAT MESSAGES BODY */}
              <div className="flex-1 overflow-y-auto p-5 space-y-4 font-sans text-sm">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"
                      }`}
                  >
                    {/* Sender label & time */}
                    <div className="flex items-center gap-1.5 text-[10px] font-mono text-mist mb-1 px-1">
                      {msg.sender === "bot" ? (
                        <>
                          <Sparkles size={11} className="text-coolant" />
                          <span className="text-coolant font-semibold">CockroachDB MCP</span>
                        </>
                      ) : (
                        <span className="text-fog">You</span>
                      )}
                      <span>• {msg.timestamp}</span>
                    </div>

                    {/* Bubble */}
                    <div
                      className={`max-w-[92%] rounded-2xl px-4 py-3 border ${msg.sender === "user"
                          ? "bg-coolant/20 border-coolant/40 text-frost rounded-tr-none"
                          : msg.error
                            ? "bg-red-500/10 border-red-500/40 text-fog rounded-tl-none"
                            : "bg-hall-2/80 border-rack-2 text-fog rounded-tl-none"
                        }`}
                    >
                      <p className="whitespace-pre-wrap leading-relaxed text-xs md:text-sm">
                        {msg.text}
                      </p>

                      {msg.detail && (
                        <p className="text-xs text-mist mt-2 pt-2 border-t border-rack leading-relaxed font-mono">
                          {msg.detail}
                        </p>
                      )}

                      {/* Loading spinner state */}
                      {msg.loading && (
                        <div className="flex items-center gap-2 mt-2 text-xs font-mono text-coolant">
                          <RefreshCw size={13} className="animate-spin" />
                          <span>Querying vector embeddings index...</span>
                        </div>
                      )}

                      {/* Retrieval method badges -- honest about vector vs fallback */}
                      {msg.retrieval && (msg.retrieval.incidents?.method || msg.retrieval.recommendations?.method) && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {msg.retrieval.incidents?.method && (
                            <RetrievalBadge
                              method={msg.retrieval.incidents.method}
                              embeddingModel={msg.retrieval.incidents.model}
                              searchedRecords={msg.retrieval.incidents.searched}
                            />
                          )}
                          {msg.retrieval.recommendations?.method && (
                            <RetrievalBadge
                              method={msg.retrieval.recommendations.method}
                              embeddingModel={msg.retrieval.recommendations.model}
                              searchedRecords={msg.retrieval.recommendations.searched}
                            />
                          )}
                        </div>
                      )}

                      {/* Vector Search Memory Results Cards */}
                      {msg.memories && msg.memories.length > 0 && (
                        <div className="mt-3 space-y-2">
                          {msg.memories.map((m, idx) => (
                            <div
                              key={idx}
                              className="rounded-xl bg-abyss/80 border border-flow/20 p-3 text-xs hover:border-flow/40 transition-colors"
                            >
                              <div className="flex items-center justify-between mb-1.5">
                                <span className="font-mono text-[10px] uppercase font-bold text-flow flex items-center gap-1">
                                  <Database size={11} />
                                  {m.memory_id ? m.memory_id.slice(0, 8) : `Match #${idx + 1}`} ({m.type})
                                </span>
                                {/* FIX: similarity can be null (fallback_recent path) --
                                    show "N/A" instead of a fabricated percentage */}
                                <span
                                  className={`font-mono text-[10px] font-semibold px-2 py-0.5 rounded-full border ${m.similarity == null
                                      ? "text-mist bg-hall-3 border-rack-2"
                                      : "text-signal bg-signal/15 border-signal/30"
                                    }`}
                                >
                                  {m.similarity == null
                                    ? "No similarity score"
                                    : `${Math.round(m.similarity * 100)}% Match`}
                                </span>
                              </div>

                              <p className="text-fog text-xs font-medium">{m.summary_text}</p>

                              {m.severity && (
                                <p className="text-[11px] text-mist mt-1 font-mono">
                                  Severity: {m.severity}
                                </p>
                              )}

                              {m.root_cause && (
                                <p className="text-[11px] text-amber/90 mt-1.5 font-mono">
                                  ⚠ Root Cause: {m.root_cause}
                                </p>
                              )}

                              {m.expected_water_saving != null && (
                                <p className="text-[11px] text-signal mt-1 font-mono flex items-center gap-1">
                                  <Droplets size={11} /> Expected Water Saving: {m.expected_water_saving}%
                                  {m.confidence != null && (
                                    <span className="text-mist"> · Confidence: {Math.round(m.confidence * 100)}%</span>
                                  )}
                                </p>
                              )}

                              {m.created_at && (
                                <p className="text-[10px] text-mist/70 mt-1.5 font-mono">
                                  {new Date(m.created_at).toLocaleString()}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Suggestion buttons if attached */}
                      {msg.suggestions && (
                        <div className="mt-3 pt-3 border-t border-rack/60 space-y-2">
                          <span className="text-[10px] font-mono text-mist uppercase tracking-wider block font-semibold">
                            Quick Vector Queries:
                          </span>
                          <div className="flex flex-col gap-1.5">
                            {msg.suggestions.map((s, idx) => {
                              const Icon = s.icon;
                              return (
                                <button
                                  key={idx}
                                  onClick={() => handleQuery(s.label)}
                                  className="flex items-center gap-2 text-left px-3 py-2 rounded-xl bg-hall-3 hover:bg-hall-3/80 border border-rack-2 hover:border-coolant/40 text-xs text-fog hover:text-frost transition-colors group"
                                >
                                  <Icon size={13} className="text-coolant flex-shrink-0" />
                                  <span className="flex-1 text-xs">{s.label}</span>
                                  <ChevronRight size={13} className="text-mist group-hover:translate-x-0.5 transition-transform" />
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* CHAT INPUT AREA */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleQuery();
                }}
                className="p-4 bg-hall-2/90 border-t border-rack flex items-center gap-2 flex-shrink-0"
              >
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask CockroachDB Memory (e.g. high GPU thermal spike at 39°C)..."
                  className="flex-1 rounded-xl bg-hall-3 border border-rack-2 focus:border-coolant px-4 py-2.5 text-xs md:text-sm text-fog placeholder:text-mist outline-none transition-colors"
                  disabled={searching}
                />
                <button
                  type="submit"
                  disabled={searching || !input.trim()}
                  className="p-3 rounded-xl bg-gradient-to-r from-coolant to-flow hover:brightness-110 disabled:opacity-40 text-abyss font-bold transition-all flex items-center justify-center shadow-lg"
                >
                  {searching ? (
                    <RefreshCw size={16} className="animate-spin" />
                  ) : (
                    <Send size={16} />
                  )}
                </button>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}