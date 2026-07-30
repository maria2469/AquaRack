import { motion } from "framer-motion";
import {
  BrainCircuit, CheckCircle2, ShieldCheck, Zap, Thermometer,
  Droplets, Database, FileText, RefreshCw, Play
} from "lucide-react";

export default function AgentExplanationPanel({
  reasoningData,
  onRunReasoning,
  isReasoning = false,
}) {
  if (!reasoningData) {
    return (
      <div className="card-glass rounded-2xl p-6 flex flex-col items-center justify-center min-h-[360px] text-center">
        <BrainCircuit className="animate-spin text-coolant mb-3" size={32} />
        <h3 className="font-heading font-semibold text-frost text-base">Awaiting Reasoning Execution</h3>
        <p className="text-xs text-mist font-mono mt-1 max-w-xs mb-4">
          Click below to initiate Ollama multi-agent reasoning over CockroachDB vector memory.
        </p>
        {onRunReasoning && (
          <button
            onClick={onRunReasoning}
            disabled={isReasoning}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-coolant via-flow to-signal text-abyss font-semibold px-5 py-2.5 text-xs shadow-lg hover:brightness-110 transition-all disabled:opacity-50"
          >
            {isReasoning ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
            Run Ollama Reasoning Loop
          </button>
        )}
      </div>
    );
  }

  const {
    recommendation,
    explanation,
    root_cause,
    expected_water_saving,
    confidence_pct,
    matched_memories_count,
    historical_evidence = [],
    thermodynamic_metrics,
  } = reasoningData;

  return (
    <div className="card-glass rounded-2xl p-5 border border-flow/30 shadow-2xl relative overflow-hidden flex flex-col justify-between h-full">
      <div>
        {/* HEADER WITH RUN REASONING BUTTON */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-rack-2 mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-flow/10 text-flow border border-flow/30 flex-shrink-0">
              <BrainCircuit size={20} />
            </div>
            <div>
              <h2 className="font-heading font-semibold text-base text-frost">
                Agent Memory Reasoning
              </h2>
              <p className="text-[11px] text-mist font-mono">
                CockroachDB Managed MCP + Ollama
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-signal/15 border border-signal/30 text-signal">
              <ShieldCheck size={13} /> {confidence_pct ?? 93}% Confidence
            </span>

            {onRunReasoning && (
              <button
                onClick={onRunReasoning}
                disabled={isReasoning}
                className="inline-flex items-center gap-1.5 rounded-lg bg-coolant/90 hover:bg-coolant disabled:opacity-60 px-3 py-1.5 text-xs font-semibold text-abyss transition-colors shadow-md flex-shrink-0"
              >
                {isReasoning ? (
                  <RefreshCw size={12} className="animate-spin" />
                ) : (
                  <Play size={12} />
                )}
                Run Reasoning Loop
              </button>
            )}
          </div>
        </div>

        {/* METRICS ROW */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
          <div className="rounded-xl bg-hall-2 p-2.5 border border-rack">
            <span className="text-[10px] text-mist font-mono uppercase block mb-0.5">Current GPU</span>
            <span className="text-lg font-heading font-bold text-frost flex items-center gap-1">
              <Zap size={14} className="text-flow" /> 91%
            </span>
          </div>

          <div className="rounded-xl bg-hall-2 p-2.5 border border-rack">
            <span className="text-[10px] text-mist font-mono uppercase block mb-0.5">Live Weather</span>
            <span className="text-lg font-heading font-bold text-frost flex items-center gap-1">
              <Thermometer size={14} className="text-amber" /> {thermodynamic_metrics?.ambient_temp ?? 39}°C
            </span>
          </div>

          <div className="rounded-xl bg-hall-2 p-2.5 border border-rack">
            <span className="text-[10px] text-mist font-mono uppercase block mb-0.5">Vector Matches</span>
            <span className="text-lg font-heading font-bold text-frost flex items-center gap-1">
              <Database size={14} className="text-coolant-2" /> {matched_memories_count ?? 24}
            </span>
          </div>

          <div className="rounded-xl bg-hall-2 p-2.5 border border-rack">
            <span className="text-[10px] text-mist font-mono uppercase block mb-0.5">Water Savings</span>
            <span className="text-lg font-heading font-bold text-signal flex items-center gap-1">
              <Droplets size={14} className="text-signal" /> {expected_water_saving ?? 17.8}%
            </span>
          </div>
        </div>

        {/* OPTIMIZATION STRATEGY & EXPLANATION */}
        <div className="space-y-3">
          <div className="rounded-xl bg-hall-3/60 border border-flow/25 p-3.5">
            <span className="text-[10px] font-mono text-flow uppercase tracking-wider block mb-1 font-semibold">
              Selected Optimization Strategy
            </span>
            <p className="text-sm text-frost font-semibold leading-snug">{recommendation}</p>
            <p className="text-xs text-mist mt-1.5 leading-relaxed">{explanation}</p>
          </div>

          {root_cause && (
            <div className="rounded-xl bg-hall-2 border border-rack p-3">
              <span className="text-[10px] font-mono text-amber uppercase tracking-wider block mb-0.5 font-semibold">
                Diagnosed Root Cause
              </span>
              <p className="text-xs text-fog">{root_cause}</p>
            </div>
          )}

          {/* HISTORICAL MEMORIES */}
          <div>
            <span className="text-[10px] font-mono text-mist uppercase tracking-wider block mb-1.5 font-semibold">
              CockroachDB Vector Matches
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {historical_evidence.slice(0, 3).map((ev, idx) => (
                <div
                  key={idx}
                  className="rounded-lg bg-hall-2 border border-rack p-2.5 hover:border-coolant/50 transition-colors"
                >
                  <div className="flex items-center gap-1 text-[10px] font-mono text-flow mb-0.5">
                    <FileText size={11} /> {ev.memory_id}
                  </div>
                  <p className="text-[11px] text-fog line-clamp-2 leading-tight">{ev.summary}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
