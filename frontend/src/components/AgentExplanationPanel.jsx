import {
  BrainCircuit, ShieldCheck, Zap, Thermometer,
  Droplets, Database, FileText, RefreshCw
} from "lucide-react";
import ReasoningProgressBar from "./ReasoningProgressBar";
import { useReasoningProgress } from "../hooks/useReasoningProgress";

export default function AgentExplanationPanel({
  reasoningData,
  idlePreview,
  isReasoning = false,
  telemetry,
  dashData,
}) {
  const liveGpu = telemetry?.gpu_pct ?? dashData?.current_gpu;
  const liveWeather = reasoningData?.thermodynamic_metrics?.ambient_temp
    ?? idlePreview?.thermodynamic_metrics?.ambient_temp
    ?? dashData?.weather_temp
    ?? telemetry?.weather_temp;
  const liveHumidity = reasoningData?.thermodynamic_metrics?.humidity
    ?? idlePreview?.thermodynamic_metrics?.humidity
    ?? dashData?.humidity
    ?? telemetry?.humidity;
  
  // Real-time progress tracking
  const { activeStage, elapsedSec } = useReasoningProgress(isReasoning);

  if (isReasoning) {
    return (
      <div className="card-glass rounded-2xl p-5 border border-flow/30 shadow-2xl flex flex-col justify-between h-full min-h-[360px]">
        <div className="flex items-center gap-3 pb-4 border-b border-rack-2 mb-4">
          <div className="p-2 rounded-xl bg-flow/10 text-flow border border-flow/30">
            <BrainCircuit size={20} className="animate-pulse" />
          </div>
          <div>
            <h2 className="font-heading font-semibold text-base text-frost">Agent Memory Reasoning</h2>
            <p className="text-[11px] text-mist font-mono">
              {activeStage?.label 
                ? `${activeStage.label} — ${activeStage.hint}`
                : "Ollama local inference in progress…"}
            </p>
          </div>
        </div>
        <ReasoningProgressBar
          active
          phaseLabel={activeStage?.label 
            ? `${activeStage.label} — ${activeStage.hint}`
            : "Running LangGraph pipeline — Predictor & Optimizer agents call Ollama"}
          activeStage={activeStage}
          elapsedSec={elapsedSec}
        />
        <p className="text-[10px] font-mono text-mist/70 mt-3 text-center">
          {activeStage?.label 
            ? `Currently: ${activeStage.label} (${elapsedSec}s elapsed)`
            : "Local Ollama typically takes 30–120s. Agent trace updates live in the console →"}
        </p>
      </div>
    );
  }

  const display = reasoningData ?? idlePreview;

  if (!display) {
    return (
      <div className="card-glass rounded-2xl p-6 flex flex-col items-center justify-center min-h-[360px] text-center">
        <BrainCircuit className="text-coolant mb-3" size={32} />
        <h3 className="font-heading font-semibold text-frost text-base">Awaiting Reasoning Execution</h3>
        <p className="text-xs text-mist font-mono mt-1 max-w-xs mb-4">
          Click the "Run Ollama Reasoning Loop" button above to initiate multi-agent reasoning over CockroachDB vector memory.
        </p>
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
    agent_trace = [],
  } = display;

  const gpuDisplay = liveGpu != null ? `${Number(liveGpu).toFixed(1)}%` : "—";
  const weatherDisplay = liveWeather != null ? `${Number(liveWeather).toFixed(1)}°C` : "—";
  const matchesDisplay = matched_memories_count ?? dashData?.historical_matches_count ?? 0;
  const savingsDisplay = expected_water_saving != null ? `${expected_water_saving}%` : "—";
  const isLiveResult = Boolean(reasoningData);

  return (
    <div className="card-glass rounded-2xl p-5 border border-flow/30 shadow-2xl relative overflow-hidden flex flex-col justify-between h-full">
      <div>
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
                {isLiveResult ? "Live result from POST /api/reason" : "Dashboard preview — run loop for live output"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {confidence_pct != null && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-signal/15 border border-signal/30 text-signal">
                <ShieldCheck size={13} /> {confidence_pct}% Confidence
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
          <div className="rounded-xl bg-hall-2 p-2.5 border border-rack">
            <span className="text-[10px] text-mist font-mono uppercase block mb-0.5">Current GPU</span>
            <span className="text-lg font-heading font-bold text-frost flex items-center gap-1">
              <Zap size={14} className="text-flow" /> {gpuDisplay}
            </span>
          </div>

          <div className="rounded-xl bg-hall-2 p-2.5 border border-rack">
            <span className="text-[10px] text-mist font-mono uppercase block mb-0.5">Live Weather</span>
            <span className="text-lg font-heading font-bold text-frost flex items-center gap-1">
              <Thermometer size={14} className="text-amber" /> {weatherDisplay}
              {liveHumidity != null && (
                <span className="text-xs text-mist font-mono ml-1">{Number(liveHumidity).toFixed(0)}% RH</span>
              )}
            </span>
          </div>

          <div className="rounded-xl bg-hall-2 p-2.5 border border-rack">
            <span className="text-[10px] text-mist font-mono uppercase block mb-0.5">Vector Matches</span>
            <span className="text-lg font-heading font-bold text-frost flex items-center gap-1">
              <Database size={14} className="text-coolant-2" /> {matchesDisplay}
            </span>
          </div>

          <div className="rounded-xl bg-hall-2 p-2.5 border border-rack">
            <span className="text-[10px] text-mist font-mono uppercase block mb-0.5">Water Savings</span>
            <span className="text-lg font-heading font-bold text-signal flex items-center gap-1">
              <Droplets size={14} className="text-signal" /> {savingsDisplay}
            </span>
          </div>
        </div>

        <div className="space-y-3">
          <div className="rounded-xl bg-hall-3/60 border border-flow/25 p-3.5">
            <span className="text-[10px] font-mono text-flow uppercase tracking-wider block mb-1 font-semibold">
              Selected Optimization Strategy
            </span>
            <p className="text-sm text-frost font-semibold leading-snug">{recommendation}</p>
            {explanation && (
              <p className="text-xs text-mist mt-1.5 leading-relaxed">{explanation}</p>
            )}
          </div>

          {root_cause && (
            <div className="rounded-xl bg-hall-2 border border-rack p-3">
              <span className="text-[10px] font-mono text-amber uppercase tracking-wider block mb-0.5 font-semibold">
                Diagnosed Root Cause
              </span>
              <p className="text-xs text-fog">{root_cause}</p>
            </div>
          )}

          {historical_evidence.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-mist uppercase tracking-wider block mb-1.5 font-semibold">
                CockroachDB Vector Matches
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {historical_evidence.slice(0, 3).map((ev, idx) => (
                  <div
                    key={ev.memory_id ?? idx}
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
          )}

          {/* Display Agent Thinking Process */}
          {display.agent_trace && display.agent_trace.length > 0 && (
            <div className="mt-4">
              <span className="text-[10px] font-mono text-flow uppercase tracking-wider block mb-2 font-semibold">
                🧠 Agent Thinking Process
              </span>
              <div className="space-y-2 max-h-64 overflow-y-auto pr-2">
                {display.agent_trace.map((trace, idx) => (
                  <div key={idx} className="rounded-lg bg-hall-2 border border-rack p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[10px] font-mono text-amber font-semibold">
                        {trace.agent}
                      </span>
                      {trace.thinking && (
                        <button
                          onClick={() => {
                            const modal = document.createElement('div');
                            modal.className = 'fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4';
                            modal.innerHTML = `
                              <div class="bg-abyss border border-rack rounded-xl p-4 max-w-2xl max-h-[80vh] overflow-y-auto">
                                <div class="flex justify-between items-center mb-3">
                                  <h3 class="font-heading font-semibold text-frost">${trace.agent} Thinking</h3>
                                  <button onclick="this.parentElement.parentElement.parentElement.remove()" class="text-mist hover:text-frost">✕</button>
                                </div>
                                <pre class="text-xs text-fog font-mono whitespace-pre-wrap">${trace.thinking}</pre>
                              </div>
                            `;
                            document.body.appendChild(modal);
                          }}
                          className="text-[9px] text-flow hover:text-fog cursor-pointer"
                        >
                          🔍 View Details
                        </button>
                      )}
                    </div>
                    
                    {/* Show key decision points */}
                    {trace.predictions && (
                      <div className="text-[11px] text-fog mb-1">
                        <span className="text-amber font-semibold">Risk:</span> {trace.predictions.risk_level}
                        <span className="ml-2 text-mist">|</span>
                        <span className="text-signal">{(trace.predictions.predicted_pue_impact * 100).toFixed(0)}% PUE Impact</span>
                      </div>
                    )}
                    
                    {trace.plan && (
                      <div className="text-[11px] text-fog mb-1">
                        <span className="text-signal font-semibold">Strategy:</span> {trace.plan.recommendation?.substring(0, 60)}...
                        <span className="ml-2 text-mist">|</span>
                        <span className="text-flow">{(trace.plan.confidence * 100).toFixed(0)}% Confidence</span>
                      </div>
                    )}
                    
                    {trace.result && (
                      <div className="text-[11px] text-fog mb-1">
                        <span className="text-coolant font-semibold">Action:</span> {trace.result.guardrail_passed ? '✅ Passed' : '❌ Failed'}
                        <span className="ml-2 text-mist">|</span>
                        <span className="text-flow">{(trace.result.final_confidence * 100).toFixed(0)}% Final Confidence</span>
                      </div>
                    )}
                    
                    {trace.thinking && (
                      <div className="text-[10px] text-mist font-mono mt-2 p-2 bg-hall-3 rounded border border-rack/30">
                        {trace.thinking.split('\n').slice(0, 3).join('\n')}
                        {trace.thinking.split('\n').length > 3 && '...'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
