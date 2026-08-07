import { useState, useEffect, useRef } from "react";
import { getRecentTraces } from "../lib/api";

export const REASONING_STAGES = [
  { id: "MonitorAgent", label: "Monitor", hint: "Ingesting telemetry & retrieving context" },
  { id: "PredictorAgent", label: "Predict", hint: "Ollama risk assessment — local inference, 30–90s typical" },
  { id: "OptimizerAgent", label: "Optimize", hint: "Ollama strategy formulation" },
  { id: "ActionAgent", label: "Action", hint: "Guardrail validation & cluster health" },
  { id: "ReflectAgent", label: "Reflect", hint: "Writing episode to CockroachDB" },
  { id: "ExplainerAgent", label: "Explain", hint: "Assembling final recommendation" },
];

function stageIndexForAgent(agentName) {
  if (!agentName) return -1;
  const normalized = agentName.replace(/Agent$/, "");
  const idx = REASONING_STAGES.findIndex(
    (s) => s.id === agentName || s.id.startsWith(normalized) || agentName.startsWith(s.id.replace("Agent", ""))
  );
  if (idx >= 0) return idx;
  const lower = agentName.toLowerCase();
  if (lower.includes("monitor")) return 0;
  if (lower.includes("predict")) return 1;
  if (lower.includes("optim")) return 2;
  if (lower.includes("action")) return 3;
  if (lower.includes("reflect")) return 4;
  if (lower.includes("explain")) return 5;
  return -1;
}

/**
 * Polls GET /api/v1/agent/trace/recent while a long-running reasoning job is active.
 * Surfaces the current LangGraph agent stage for progress UI during slow Ollama calls.
 */
export function useReasoningProgress(active, pollMs = 2000) {
  const [events, setEvents] = useState([]);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [stageIndex, setStageIndex] = useState(-1);
  const [elapsedSec, setElapsedSec] = useState(0);
  const startedAt = useRef(null);

  useEffect(() => {
    if (!active) {
      startedAt.current = null;
      setElapsedSec(0);
      setEvents([]);
      setCurrentAgent(null);
      setStageIndex(-1);
      return;
    }

    startedAt.current = Date.now();
    setElapsedSec(0);

    const poll = async () => {
      try {
        const res = await getRecentTraces(null, 40);
        const list = res?.events ?? res ?? [];
        if (Array.isArray(list) && list.length > 0) {
          setEvents(list);
          const latest = list[list.length - 1];
          const agent = latest?.agent ?? null;
          setCurrentAgent(agent);
          setStageIndex(stageIndexForAgent(agent));
        }
      } catch {
        // Backend may be busy — keep last known stage
      }
    };

    poll();
    const pollId = setInterval(poll, pollMs);
    const clockId = setInterval(() => {
      if (startedAt.current) {
        setElapsedSec(Math.floor((Date.now() - startedAt.current) / 1000));
      }
    }, 1000);

    return () => {
      clearInterval(pollId);
      clearInterval(clockId);
    };
  }, [active, pollMs]);

  const activeStage = stageIndex >= 0 ? REASONING_STAGES[stageIndex] : null;

  return {
    events,
    currentAgent,
    stageIndex,
    activeStage,
    elapsedSec,
    progressPct: stageIndex >= 0 ? Math.round(((stageIndex + 1) / REASONING_STAGES.length) * 100) : 8,
  };
}
