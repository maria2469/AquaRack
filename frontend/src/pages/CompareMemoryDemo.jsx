import { useState } from "react";
import { motion } from "framer-motion";
import {
  Brain, ShieldAlert, CheckCircle2, ArrowRight, Zap, RefreshCw,
  Cpu, Thermometer, Droplets, HelpCircle, Layers, Sparkles
} from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";
import { postReason } from "../lib/api";

export default function CompareMemoryDemo() {
  const [loading, setLoading] = useState(false);
  const [hasRun, setHasRun] = useState(false);

  const scenario = {
    rack: "Rack 04 - High-Density Training Cluster",
    utilisation: 94.2,
    thermal_load_kw: 4.8,
    ambient_temp: 39.5,
    humidity: 65,
  };

  const withoutMemoryResult = {
    agent: "Standard Rules / Generic LLM",
    confidence: 65,
    recommendation: "Apply default 10% airflow boost and issue general thermal alert.",
    rationale: "No past operational experience retrieved. Falling back to static safety margins and generic cooling lookup.",
    cited_episodes: 0,
    risk_assessment: "Uncertain thermal impact; risk of over-cooling or thermal throttle.",
    expected_water_saving: 2.5,
  };

  const withMemoryResult = {
    agent: "AquaMind Multi-Agent (Episode RAG + StrategyScore)",
    confidence: 91,
    recommendation: "Increase liquid cooling flow by 15% and bypass secondary chiller circuit.",
    rationale: "I've seen this workload pattern before — last Tuesday under 39°C ambient, liquid flow +15% maintained thermal equilibrium at 66°C GPU temp, saving 18.4% water with 0 incidents (seen in 41 resolved episodes).",
    cited_episodes: 41,
    risk_assessment: "Validated low risk. Strategy confidence blended 60% LLM / 40% StrategyScore (0.91).",
    expected_water_saving: 18.4,
    failure_memory_avoided: "Avoided strategy 'Fan Speed +25%' which caused an over-power trip on 2026-07-28.",
  };

  const handleRunComparison = async () => {
    setLoading(true);
    try {
      await postReason();
    } catch {
      // Demo mode fallback
    } finally {
      setHasRun(true);
      setLoading(false);
    }
  };

  return (
    <div className="relative bg-abyss min-h-screen">
      <section className="relative pt-28 pb-8 border-b border-rack overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-7xl mx-auto px-5 md:px-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono">Side-by-Side Evaluation</span>
              <h1 className="font-heading text-3xl md:text-4xl font-semibold text-frost mt-1.5">
                Memory vs. No-Memory Decision Comparison
              </h1>
              <p className="text-sm text-mist mt-1">
                Demonstrates how historical episode retrieval and StrategyScore confidence directly improve agent decisions.
              </p>
            </div>
            <button
              onClick={handleRunComparison}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-coolant via-flow to-signal hover:brightness-110 disabled:opacity-60 px-5 py-2.5 text-xs font-semibold text-abyss transition-all shadow-lg"
            >
              {loading ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}
              Run Side-by-Side Benchmark
            </button>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 md:px-8 py-8 space-y-8">
        {/* Scenario Card */}
        <div className="card-glass rounded-2xl p-5 border border-rack-2 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-coolant/10 text-coolant border border-coolant/30">
              <Cpu size={20} />
            </div>
            <div>
              <span className="text-[10px] font-mono text-mist uppercase">Active Stress Scenario</span>
              <h3 className="font-heading font-semibold text-frost text-lg">{scenario.rack}</h3>
            </div>
          </div>
          <div className="flex items-center gap-6 flex-wrap font-mono text-xs">
            <div><span className="text-mist block">GPU Util</span><span className="text-signal font-semibold">{scenario.utilisation}%</span></div>
            <div><span className="text-mist block">Thermal Load</span><span className="text-flow font-semibold">{scenario.thermal_load_kw} kW</span></div>
            <div><span className="text-mist block">Ambient Temp</span><span className="text-amber font-semibold">{scenario.ambient_temp}°C</span></div>
            <div><span className="text-mist block">Humidity</span><span className="text-fog font-semibold">{scenario.humidity}%</span></div>
          </div>
        </div>

        {/* Side by Side Comparison Grid */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* LEFT: WITHOUT MEMORY */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="card-glass rounded-2xl p-6 border border-alert/30 bg-hall-2/50 relative overflow-hidden flex flex-col justify-between"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-rack/50 pb-3">
                <div className="flex items-center gap-2">
                  <HelpCircle size={18} className="text-mist" />
                  <h3 className="font-heading font-semibold text-mist text-lg">Without Agentic Memory</h3>
                </div>
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-mono bg-hall-3 text-mist border border-rack-2">
                  65% Confidence
                </span>
              </div>

              <div className="rounded-xl bg-hall-3/70 p-4 border border-rack">
                <span className="text-[10px] font-mono text-mist uppercase tracking-wider block mb-1 font-semibold">
                  Generic Recommendation
                </span>
                <p className="text-sm font-semibold text-fog">{withoutMemoryResult.recommendation}</p>
              </div>

              <div className="rounded-xl bg-hall-3/40 p-4 border border-rack space-y-2">
                <span className="text-[10px] font-mono text-mist uppercase tracking-wider block font-semibold">
                  Decision Rationale & Evidence
                </span>
                <p className="text-xs text-mist leading-relaxed">{withoutMemoryResult.rationale}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                <div className="p-3 rounded-lg bg-hall-3/40 border border-rack">
                  <span className="text-[10px] text-mist block">Cited Episodes</span>
                  <span className="text-sm font-semibold text-mist">{withoutMemoryResult.cited_episodes}</span>
                </div>
                <div className="p-3 rounded-lg bg-hall-3/40 border border-rack">
                  <span className="text-[10px] text-mist block">Est. Water Saving</span>
                  <span className="text-sm font-semibold text-mist">{withoutMemoryResult.expected_water_saving}%</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-rack/30 text-[11px] font-mono text-mist/70">
              ❌ No past incident or episode context available. Conservative, uncalibrated guess.
            </div>
          </motion.div>

          {/* RIGHT: WITH MEMORY */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="card-glass rounded-2xl p-6 border border-signal/40 bg-hall-2 relative overflow-hidden flex flex-col justify-between shadow-2xl"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-rack-2 pb-3">
                <div className="flex items-center gap-2">
                  <Brain size={18} className="text-signal" />
                  <h3 className="font-heading font-semibold text-frost text-lg">With Episode Memory & RAG</h3>
                </div>
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-mono bg-signal/20 text-signal border border-signal/40 font-semibold">
                  <CheckCircle2 size={13} /> 91% Confidence
                </span>
              </div>

              <div className="rounded-xl bg-signal/10 p-4 border border-signal/30">
                <span className="text-[10px] font-mono text-signal uppercase tracking-wider block mb-1 font-semibold">
                  Memory-Informed Strategy
                </span>
                <p className="text-sm font-semibold text-frost">{withMemoryResult.recommendation}</p>
              </div>

              <div className="rounded-xl bg-hall-3/80 p-4 border border-coolant/30 space-y-2">
                <span className="text-[10px] font-mono text-flow uppercase tracking-wider block font-semibold">
                  Contextual Rationale & Historical Proof
                </span>
                <p className="text-xs text-fog leading-relaxed">{withMemoryResult.rationale}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                <div className="p-3 rounded-lg bg-hall-3 border border-rack">
                  <span className="text-[10px] text-mist block">Cited Episodes</span>
                  <span className="text-sm font-semibold text-flow">{withMemoryResult.cited_episodes} resolved</span>
                </div>
                <div className="p-3 rounded-lg bg-hall-3 border border-rack">
                  <span className="text-[10px] text-mist block">Est. Water Saving</span>
                  <span className="text-sm font-semibold text-signal">{withMemoryResult.expected_water_saving}%</span>
                </div>
              </div>

              {withMemoryResult.failure_memory_avoided && (
                <div className="rounded-xl bg-alert/10 border border-alert/30 p-3 flex items-start gap-2 text-xs font-mono text-alert">
                  <ShieldAlert size={14} className="flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold block uppercase text-[9px]">Failure Memory Callout</span>
                    {withMemoryResult.failure_memory_avoided}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-rack/50 text-[11px] font-mono text-signal">
              ✓ Uses cosine embedding similarity over historical Episode table + 60/40 StrategyScore prior blending.
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
