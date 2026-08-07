import { motion } from "framer-motion";
import { BrainCircuit, RefreshCw, Clock } from "lucide-react";
import { useReasoningProgress, REASONING_STAGES } from "../hooks/useReasoningProgress";

function formatElapsed(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? `${m}m ${String(s).padStart(2, "0")}s` : `${s}s`;
}

/**
 * Live progress indicator for slow Ollama / LangGraph reasoning runs.
 * Polls agent trace events and shows which pipeline stage is active.
 */
export default function ReasoningProgressBar({
  active = false,
  phaseLabel = "Running agentic reasoning pipeline",
  compact = false,
}) {
  const { stageIndex, activeStage, elapsedSec, progressPct, currentAgent, events } =
    useReasoningProgress(active);

  if (!active) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border border-coolant/30 bg-hall-2/90 backdrop-blur-sm ${
        compact ? "p-3" : "p-4"
      }`}
    >
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <BrainCircuit size={compact ? 16 : 18} className="text-coolant animate-pulse flex-shrink-0" />
          <div className="min-w-0">
            <p className="text-xs font-semibold text-frost truncate">{phaseLabel}</p>
            <p className="text-[10px] font-mono text-mist truncate">
              {activeStage?.hint ?? "Waiting for Ollama on localhost — this is normal for local inference"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-mist">
            <Clock size={11} />
            {formatElapsed(elapsedSec)}
          </span>
          <RefreshCw size={13} className="text-flow animate-spin" />
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-hall-3 rounded-full overflow-hidden mb-3">
        <motion.div
          className="h-full bg-gradient-to-r from-coolant via-flow to-signal"
          initial={{ width: "5%" }}
          animate={{ width: `${Math.max(8, progressPct)}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>

      {/* Stage pills */}
      {!compact && (
        <div className="flex flex-wrap gap-1.5">
          {REASONING_STAGES.map((stage, i) => {
            const done = stageIndex > i;
            const current = stageIndex === i;
            return (
              <span
                key={stage.id}
                className={`text-[9px] font-mono px-2 py-0.5 rounded-full border transition-colors ${
                  current
                    ? "bg-coolant/20 border-coolant/50 text-coolant font-semibold"
                    : done
                      ? "bg-signal/10 border-signal/30 text-signal"
                      : "bg-hall-3 border-rack text-mist/60"
                }`}
              >
                {done ? "✓ " : current ? "● " : ""}
                {stage.label}
              </span>
            );
          })}
        </div>
      )}

      {currentAgent && (
        <p className="text-[9px] font-mono text-mist/70 mt-2">
          Latest: {currentAgent}
          {events.length > 0 && ` · ${events.length} trace events`}
        </p>
      )}
    </motion.div>
  );
}
