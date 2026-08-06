import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Terminal, Play, Pause, Trash2, ChevronDown, ChevronUp,
  BrainCircuit, Database, ShieldCheck, AlertTriangle, Zap,
  Cpu, Droplets, ArrowRight
} from "lucide-react";

/**
 * Stage → visual config mapping. Each reasoning stage gets a distinct
 * colour and icon so the operator can instantly parse the live feed.
 */
const STAGE_META = {
  input:      { color: "text-flow",    bg: "bg-flow/10",    border: "border-flow/30",    icon: ArrowRight,     label: "INPUT" },
  reasoning:  { color: "text-coolant", bg: "bg-coolant/10", border: "border-coolant/30", icon: BrainCircuit,   label: "REASONING" },
  tool_call:  { color: "text-amber",   bg: "bg-amber/10",   border: "border-amber/30",   icon: Database,       label: "TOOL CALL" },
  decision:   { color: "text-signal",  bg: "bg-signal/10",  border: "border-signal/30",  icon: Zap,            label: "DECISION" },
  guardrail:  { color: "text-coolant-2", bg: "bg-coolant-2/10", border: "border-coolant-2/30", icon: ShieldCheck, label: "GUARDRAIL" },
  error:      { color: "text-alert",   bg: "bg-alert/10",   border: "border-alert/30",   icon: AlertTriangle,  label: "ERROR" },
};

const DEFAULT_META = { color: "text-mist", bg: "bg-hall-3", border: "border-rack-2", icon: Cpu, label: "STEP" };

/**
 * Formats a UNIX timestamp to a compact HH:MM:SS.mmm string.
 */
function formatTs(ts) {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  const ms = String(d.getMilliseconds()).padStart(3, "0");
  return `${hh}:${mm}:${ss}.${ms}`;
}

/**
 * Renders the detail payload as syntax-highlighted key-value lines,
 * collapsible for large payloads.
 */
function DetailBlock({ detail }) {
  const [expanded, setExpanded] = useState(false);
  if (!detail || Object.keys(detail).length === 0) return null;

  const text = JSON.stringify(detail, null, 2);
  const lines = text.split("\n");
  const isLong = lines.length > 5;

  return (
    <div className="mt-1">
      <pre className="text-[10px] leading-[1.4] text-mist font-mono whitespace-pre-wrap break-all">
        {isLong && !expanded ? lines.slice(0, 5).join("\n") + "\n…" : text}
      </pre>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 text-[9px] text-coolant hover:text-coolant-2 mt-0.5 font-mono transition-colors"
        >
          {expanded ? <ChevronUp size={9} /> : <ChevronDown size={9} />}
          {expanded ? "Collapse" : `Expand (${lines.length} lines)`}
        </button>
      )}
    </div>
  );
}

/**
 * A single reasoning event row — compact, colour-coded, animated entry.
 */
function EventRow({ event, index }) {
  const meta = STAGE_META[event.stage] || DEFAULT_META;
  const Icon = meta.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.15, delay: Math.min(index * 0.02, 0.2) }}
      className={`group relative pl-2.5 pr-2 py-1.5 border-l-2 ${meta.border} hover:bg-hall-3/50 transition-colors`}
    >
      {/* Header line */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[9px] font-mono text-mist/70 tabular-nums min-w-[72px]">
          {formatTs(event.ts)}
        </span>
        <span className={`inline-flex items-center gap-1 text-[9px] font-mono font-semibold uppercase px-1.5 py-0.2 rounded ${meta.bg} ${meta.color}`}>
          <Icon size={9} />
          {meta.label}
        </span>
        <span className="text-[10px] font-mono text-fog font-medium">
          {event.agent}
        </span>
        {event.seq && (
          <span className="text-[9px] font-mono text-mist/40 ml-auto">
            #{event.seq}
          </span>
        )}
      </div>

      {/* Quick summary for common patterns */}
      {event.detail?.note && (
        <p className="text-[11px] text-fog/90 mt-0.5 pl-[76px]">{event.detail.note}</p>
      )}
      {event.detail?.recommendation && !event.detail?.note && (
        <p className="text-[11px] text-signal/90 mt-0.5 pl-[76px] line-clamp-2">
          💡 {event.detail.recommendation}
        </p>
      )}
      {event.detail?.error && (
        <p className="text-[11px] text-alert/90 mt-0.5 pl-[76px]">⚠ {event.detail.error}</p>
      )}

      {/* Task 5: Rejected alternatives rendering */}
      {event.detail?.alternative && (
        <div className="mt-1 ml-[76px] p-2 rounded-lg bg-hall-3 border border-rack text-[10px] font-mono text-mist">
          <span className="text-amber font-semibold">Rejected Alternative Strategy:</span>{" "}
          {event.detail.alternative}
        </div>
      )}

      {/* Feature 4: Failure Memory Callout Card */}
      {(event.detail?.failure_memory || (event.detail?.alternative && String(event.detail.alternative).toLowerCase().includes("over-power"))) && (
        <div className="mt-1.5 ml-[76px] p-2 rounded-lg bg-alert/10 border border-alert/30 text-[10px] font-mono text-alert flex items-start gap-1.5 animate-pulse">
          <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold block uppercase text-[9px]">Failure Memory Avoided</span>
            ⚠ Candidate strategy matches past incident failure — avoided trip on historical record.
          </div>
        </div>
      )}

      {/* Full detail (collapsible) */}
      <div className="pl-[76px]">
        <DetailBlock detail={event.detail} />
      </div>
    </motion.div>
  );
}

/**
 * AgentReasoningConsole — live SSE-powered reasoning log viewer.
 */
export default function AgentReasoningConsole() {
  const [events, setEvents] = useState([]);
  const [isLive, setIsLive] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState("connecting"); // connecting | live | error
  const scrollRef = useRef(null);
  const eventSourceRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  // Detect manual scroll-up to disable auto-scroll
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(atBottom);
  }, []);

  // SSE connection management
  const connectSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const baseURL = import.meta.env.VITE_API_BASE_URL || "";
    const es = new EventSource(`${baseURL}/api/v1/agent/trace/stream`);
    eventSourceRef.current = es;
    setConnectionStatus("connecting");

    es.addEventListener("reasoning", (e) => {
      try {
        const evt = JSON.parse(e.data);
        setEvents((prev) => {
          if (!evt || !evt.run_id) return prev;

          // Deduplicate by seq number
          if (prev.some((item) => item.seq === evt.seq)) return prev;

          // Check active run_id in current console state
          const currentRunId = prev.length > 0 ? prev[prev.length - 1].run_id : null;

          // When a new reasoning loop starts (new run_id), clear past loop logs
          if (currentRunId && evt.run_id !== currentRunId) {
            return [evt];
          }

          return [...prev, evt];
        });
        setConnectionStatus("live");
      } catch {
        // ignore malformed events
      }
    });

    es.onopen = () => {
      setConnectionStatus("live");
    };

    es.onerror = () => {
      setConnectionStatus("error");
      es.close();
      reconnectTimerRef.current = setTimeout(() => {
        if (isLive) connectSSE();
      }, 3000);
    };
  }, [isLive]);

  useEffect(() => {
    if (isLive) {
      connectSSE();
    } else {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setConnectionStatus("paused");
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [isLive, connectSSE]);

  const handleClear = () => setEvents([]);
  const toggleLive = () => setIsLive((prev) => !prev);

  const stageCounts = events.reduce((acc, e) => {
    acc[e.stage] = (acc[e.stage] || 0) + 1;
    return acc;
  }, {});

  const latestRunId = events.length > 0 ? events[events.length - 1].run_id : null;

  const statusDot = {
    connecting: "bg-amber animate-pulse",
    live: "bg-signal animate-pulse",
    error: "bg-alert",
    paused: "bg-mist",
  };

  return (
    <div className="card-glass rounded-2xl overflow-hidden h-full flex flex-col justify-between shadow-2xl border border-rack-2">
      {/* Console Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-hall-2/90 border-b border-rack cursor-pointer select-none flex-shrink-0"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-2">
            <Terminal size={16} className="text-coolant" />
            <h2 className="font-heading font-semibold text-frost text-sm">
              Live Reasoning Console
            </h2>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${statusDot[connectionStatus]}`} />
            <span className="text-[10px] font-mono text-mist uppercase">
              {connectionStatus === "live" ? "SSE Live" : connectionStatus}
            </span>
          </div>
          {events.length > 0 && (
            <span className="text-[10px] font-mono text-mist/70 hidden sm:inline">
              {events.length} events
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={toggleLive}
            className={`p-1.5 rounded-md border transition-colors ${
              isLive
                ? "border-signal/30 bg-signal/10 text-signal hover:bg-signal/20"
                : "border-rack-2 bg-hall-3 text-mist hover:text-fog hover:border-rack"
            }`}
            title={isLive ? "Pause live feed" : "Resume live feed"}
          >
            {isLive ? <Pause size={12} /> : <Play size={12} />}
          </button>
          <button
            onClick={handleClear}
            className="p-1.5 rounded-md border border-rack-2 bg-hall-3 text-mist hover:text-alert hover:border-alert/30 transition-colors"
            title="Clear console"
          >
            <Trash2 size={12} />
          </button>
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 rounded-md border border-rack-2 bg-hall-3 text-mist hover:text-fog transition-colors"
          >
            {isCollapsed ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
          </button>
        </div>
      </div>

      {/* Console Body */}
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="flex-1 flex flex-col justify-between"
          >
            <div
              ref={scrollRef}
              onScroll={handleScroll}
              className="max-h-[380px] min-h-[320px] overflow-y-auto bg-abyss/70 scroll-smooth flex-1"
              style={{
                scrollbarWidth: "thin",
                scrollbarColor: "#223850 #070d16",
              }}
            >
              {events.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full py-12 text-center">
                  <BrainCircuit size={32} className="text-rack-2 mb-2 animate-pulse" />
                  <p className="text-xs text-mist font-mono">No active reasoning loop in progress</p>
                  <p className="text-[11px] text-mist/60 mt-1">
                    Click <span className="text-coolant">"Run Reasoning Loop"</span> on the left to stream real-time logs here
                  </p>
                </div>
              ) : (
                <div>
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-hall-3/90 border-b border-rack/50 sticky top-0 z-10 backdrop-blur-sm">
                    <Droplets size={11} className="text-flow animate-pulse" />
                    <span className="text-[10px] font-mono font-semibold text-frost">
                      ACTIVE TRACE:
                    </span>
                    <span className="text-[9px] font-mono text-flow bg-flow/10 border border-flow/20 px-1.5 py-0.2 rounded">
                      RUN {latestRunId?.slice(0, 8)}…
                    </span>
                    <span className="text-[9px] font-mono text-signal ml-auto font-semibold">
                      ● {events.length} Steps Logged
                    </span>
                  </div>

                  <div className="divide-y divide-rack/20">
                    {events.map((evt, i) => (
                      <EventRow key={`${evt.seq}-${evt.ts}`} event={evt} index={i} />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Bottom status bar */}
            {events.length > 0 && (
              <div className="flex items-center justify-between px-3 py-1.5 bg-hall-2/80 border-t border-rack/50 flex-shrink-0">
                <span className="text-[9px] font-mono text-mist/60">
                  Run: {latestRunId?.slice(0, 8)}…
                </span>
                <div className="flex items-center gap-3">
                  {!autoScroll && (
                    <button
                      onClick={() => {
                        setAutoScroll(true);
                        if (scrollRef.current) {
                          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                        }
                      }}
                      className="text-[9px] font-mono text-coolant hover:text-coolant-2 transition-colors"
                    >
                      ↓ Jump to bottom
                    </button>
                  )}
                  <span className="text-[9px] font-mono text-mist/50">
                    {autoScroll ? "Auto-scroll ON" : "Auto-scroll OFF"}
                  </span>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
