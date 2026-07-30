import { motion } from "framer-motion";
import { BrainCircuit, CheckCircle2, ShieldCheck, Zap, Thermometer, Droplets, Database, FileText } from "lucide-react";

export default function AgentExplanationPanel({ reasoningData }) {
  if (!reasoningData) {
    return (
      <div className="card-glass rounded-2xl p-6 flex items-center justify-center text-mist text-sm">
        <BrainCircuit className="animate-spin mr-2" size={18} />
        Awaiting AI Reasoning Execution...
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
    <div className="card-glass rounded-2xl p-6 border border-flow/30 shadow-2xl relative overflow-hidden">
      <div className="flex items-center justify-between pb-4 border-b border-rack-2 mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-flow/10 text-flow border border-flow/30">
            <BrainCircuit size={22} />
          </div>
          <div>
            <h2 className="font-heading font-semibold text-lg text-frost">Agent Memory Reasoning Explanation</h2>
            <p className="text-xs text-mist font-mono">CockroachDB Managed MCP + Bedrock Titan Vector Search</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-signal/10 border border-signal/30 text-signal">
            <ShieldCheck size={14} /> Confidence: {confidence_pct ?? 93}%
          </span>
        </div>
      </div>

      <div className="grid md:grid-cols-4 gap-4 mb-6">
        <div className="rounded-xl bg-hall-2 p-3.5 border border-rack">
          <span className="text-xs text-mist font-mono uppercase block mb-1">Current GPU</span>
          <span className="text-xl font-heading font-bold text-frost flex items-center gap-1.5">
            <Zap size={16} className="text-flow" /> 91%
          </span>
        </div>

        <div className="rounded-xl bg-hall-2 p-3.5 border border-rack">
          <span className="text-xs text-mist font-mono uppercase block mb-1">Live Weather</span>
          <span className="text-xl font-heading font-bold text-frost flex items-center gap-1.5">
            <Thermometer size={16} className="text-amber" /> {thermodynamic_metrics?.ambient_temp ?? 39}°C ({thermodynamic_metrics?.humidity ?? 62}%)
          </span>
        </div>

        <div className="rounded-xl bg-hall-2 p-3.5 border border-rack">
          <span className="text-xs text-mist font-mono uppercase block mb-1">Matched Memories</span>
          <span className="text-xl font-heading font-bold text-frost flex items-center gap-1.5">
            <Database size={16} className="text-coolant-2" /> {matched_memories_count ?? 24}
          </span>
        </div>

        <div className="rounded-xl bg-hall-2 p-3.5 border border-rack">
          <span className="text-xs text-mist font-mono uppercase block mb-1">Expected Saving</span>
          <span className="text-xl font-heading font-bold text-signal flex items-center gap-1.5">
            <Droplets size={16} className="text-signal" /> {expected_water_saving ?? 17.8}%
          </span>
        </div>
      </div>

      <div className="space-y-4">
        <div className="rounded-xl bg-hall-3/50 border border-flow/20 p-4">
          <span className="text-xs font-mono text-flow uppercase tracking-wider block mb-1">Selected Optimization Strategy</span>
          <p className="text-base text-frost font-semibold">{recommendation}</p>
          <p className="text-xs text-mist mt-2 leading-relaxed">{explanation}</p>
        </div>

        {root_cause && (
          <div className="rounded-xl bg-hall-2 border border-rack p-4">
            <span className="text-xs font-mono text-amber uppercase tracking-wider block mb-1">Diagnosed Root Cause</span>
            <p className="text-sm text-fog">{root_cause}</p>
          </div>
        )}

        <div>
          <span className="text-xs font-mono text-mist uppercase tracking-wider block mb-2">
            Historical Memory Evidence (CockroachDB Vector Matches)
          </span>
          <div className="grid md:grid-cols-3 gap-3">
            {historical_evidence.map((ev, idx) => (
              <div key={idx} className="rounded-lg bg-hall-2 border border-rack p-3 hover:border-coolant transition-colors cursor-pointer">
                <div className="flex items-center gap-1.5 text-xs font-mono text-flow mb-1">
                  <FileText size={13} /> {ev.memory_id}
                </div>
                <p className="text-xs text-fog line-clamp-2">{ev.summary}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
