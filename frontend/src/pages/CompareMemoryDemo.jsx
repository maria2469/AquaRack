import { useState } from "react";
import { motion } from "framer-motion";
import {
  Brain, ShieldAlert, CheckCircle2, RefreshCw,
  Cpu, HelpCircle, Sparkles, AlertCircle, Wifi, WifiOff
} from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";
import ReasoningProgressBar from "../components/ReasoningProgressBar";
import { useLiveTelemetry } from "../hooks/useLiveTelemetry";
import { runCompareBenchmark, buildScenarioFromSimulate } from "../lib/api";
import { getGlobalFleetResult } from "../lib/globalState";

function ConnectionBadge({ status }) {
  const map = {
    connecting: { icon: RefreshCw, text: "Connecting…", cls: "text-mist border-rack-2 bg-hall-2" },
    live: { icon: Wifi, text: "Live telemetry", cls: "text-signal border-signal/30 bg-signal/10" },
    mock: { icon: WifiOff, text: "Demo stream — run requires backend", cls: "text-amber border-amber/30 bg-amber/10" },
    error: { icon: AlertCircle, text: "Backend unreachable", cls: "text-alert border-alert/30 bg-alert/10" },
  };
  const s = map[status] || map.connecting;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-mono ${s.cls}`}>
      <Icon size={12} className={status === "connecting" ? "animate-spin" : ""} />
      {s.text}
    </span>
  );
}

function fmt(val, suffix = "") {
  if (val == null) return "—";
  const display = typeof val === "number" ? val.toFixed(1) : val;
  return `${display}${suffix}`;
}

function PlaceholderPanel({ side, loading, phase }) {
  const isMemory = side === "memory";
  if (loading && phase === "baseline" && isMemory) {
    return (
      <div className="rounded-xl border border-dashed border-signal/20 p-6 text-center bg-signal/5">
        <RefreshCw size={20} className="text-signal animate-spin mx-auto mb-2" />
        <p className="text-xs font-mono text-mist">Waiting for baseline run to finish…</p>
      </div>
    );
  }
  if (loading && phase === "memory" && !isMemory) {
    return null; // baseline panel will show partial data
  }
  return (
    <div className={`rounded-xl border border-dashed p-6 text-center ${isMemory ? "border-signal/30 bg-signal/5" : "border-rack bg-hall-3/30"}`}>
      <p className="text-xs font-mono text-mist">
        {isMemory
          ? "Run benchmark — POST /api/reason (use_memory=true) + episode replay"
          : "Run benchmark — POST /api/reason (use_memory=false)"}
      </p>
    </div>
  );
}

export default function CompareMemoryDemo() {
  const { data: dashData, status } = useLiveTelemetry({ intervalMs: 8000 });
  const telemetry = dashData?.latest_telemetry;

  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState(null); // scenario | baseline | baseline_done | memory | done
  const [progressMessage, setProgressMessage] = useState("");
  const [hasRun, setHasRun] = useState(false);
  const [error, setError] = useState(null);
  const [compareData, setCompareData] = useState(null);

  const scenario = compareData?.scenario ?? {
    rack: telemetry?.device_id
      ? `${telemetry.device_id} — Active Cluster`
      : dashData?.opendc_fleet?.rack_count
        ? `OpenDC Fleet (${dashData.opendc_fleet.rack_count} racks) — Live`
        : "Primary Rack — Live Telemetry",
    utilisation: telemetry?.gpu_pct ?? dashData?.current_gpu ?? null,
    thermal_load_kw: null,
    ambient_temp: dashData?.weather_temp ?? telemetry?.weather_temp ?? null,
    humidity: dashData?.humidity ?? telemetry?.humidity ?? null,
  };

  const withoutMemory = compareData?.without_memory;
  const withMemory = compareData?.with_memory;

  const handleRunComparison = async () => {
    if (status !== "live") {
      setError("Connect to the backend to run a live side-by-side comparison.");
      return;
    }

    setLoading(true);
    setError(null);
    setPhase("scenario");
    setCompareData(null);
    setHasRun(false);

    const telemetryId = telemetry?.telemetry_id !== "live" ? telemetry?.telemetry_id : undefined;
    const liveContext = {
      telemetry_id: telemetryId,
      device_id: telemetry?.device_id,
      rack: telemetry?.device_id ? `${telemetry.device_id} — Active Cluster` : undefined,
      utilisation: telemetry?.gpu_pct ?? dashData?.current_gpu,
      ambient_temp: dashData?.weather_temp ?? telemetry?.weather_temp,
      humidity: dashData?.humidity ?? telemetry?.humidity,
      cpu_pct: telemetry?.cpu_pct ?? dashData?.current_cpu,
      gpu_pct: telemetry?.gpu_pct ?? dashData?.current_gpu,
    };

    try {
      const result = await runCompareBenchmark(
        telemetryId,
        ({ phase: p, message, partial }) => {
          setPhase(p);
          setProgressMessage(message);
          if (partial?.without_memory) {
            setCompareData((prev) => ({
              ...(prev ?? {}),
              without_memory: partial.without_memory,
              scenario: buildScenarioFromSimulate(partial.simulateRes, liveContext),
            }));
            setHasRun(true);
          }
        },
        liveContext
      );
      setCompareData(result);
      setHasRun(true);
      setPhase("done");
    } catch (err) {
      console.error("Comparison benchmark failed", err);
      const detail = err?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg).join("; ")
            : err?.message ?? "Benchmark failed — ensure backend and Ollama are running."
      );
    } finally {
      setLoading(false);
    }
  };

  const showBaseline = hasRun && withoutMemory;
  const showMemory = hasRun && withMemory;
  const progressActive = loading && phase !== "scenario";
  
  // Get fleet reasoning results
  const fleetResult = getGlobalFleetResult();

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
                Progressive benchmark: baseline LangGraph (no retrieval) then full episode RAG — same live DB snapshot.
              </p>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <ConnectionBadge status={status} />
              <button
                onClick={handleRunComparison}
                disabled={loading || status !== "live"}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-coolant via-flow to-signal hover:brightness-110 disabled:opacity-60 px-5 py-2.5 text-xs font-semibold text-abyss transition-all shadow-lg"
              >
                {loading ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}
                {loading ? "Running benchmark…" : "Run Side-by-Side Benchmark"}
              </button>
            </div>
          </div>

          {loading && (
            <div className="mt-4">
              <ReasoningProgressBar
                active={progressActive || phase === "baseline" || phase === "memory"}
                phaseLabel={progressMessage || "Initializing benchmark…"}
              />
            </div>
          )}

          {error && (
            <div className="mt-4 rounded-xl border border-alert/30 bg-alert/10 px-4 py-2.5 text-xs font-mono text-alert flex items-center gap-2">
              <AlertCircle size={14} />
              {error}
            </div>
          )}
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
              {compareData?.scenario?.telemetry_id && (
                <p className="text-[10px] font-mono text-mist mt-0.5">
                  telemetry_id: {String(compareData.scenario.telemetry_id).slice(0, 8)}…
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-6 flex-wrap font-mono text-xs">
            <div><span className="text-mist block">GPU Util</span><span className="text-signal font-semibold">{fmt(scenario.utilisation, "%")}</span></div>
            <div><span className="text-mist block">Thermal Load</span><span className="text-flow font-semibold">{fmt(scenario.thermal_load_kw, " kW")}</span></div>
            <div><span className="text-mist block">Ambient Temp</span><span className="text-amber font-semibold">{fmt(scenario.ambient_temp, "°C")}</span></div>
            <div><span className="text-mist block">Humidity</span><span className="text-fog font-semibold">{fmt(scenario.humidity, "%")}</span></div>
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
                {withoutMemory && (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-mono bg-hall-3 text-mist border border-rack-2">
                    {Math.round(withoutMemory.confidence_pct ?? withoutMemory.confidence * 100)}% Confidence
                  </span>
                )}
              </div>

              {!showBaseline ? (
                <PlaceholderPanel side="baseline" loading={loading} phase={phase} />
              ) : (
                <>
                  <div className="rounded-xl bg-hall-3/70 p-4 border border-rack">
                    <span className="text-[10px] font-mono text-mist uppercase tracking-wider block mb-1 font-semibold">
                      Generic Recommendation
                    </span>
                    <p className="text-sm font-semibold text-fog">{withoutMemory.recommendation}</p>
                  </div>

                  <div className="rounded-xl bg-hall-3/40 p-4 border border-rack space-y-2">
                    <span className="text-[10px] font-mono text-mist uppercase tracking-wider block font-semibold">
                      Decision Rationale & Evidence
                    </span>
                    <p className="text-xs text-mist leading-relaxed">{withoutMemory.rationale ?? withoutMemory.explanation}</p>
                    {withoutMemory.risk_assessment && (
                      <p className="text-[11px] text-alert/80 font-mono">{withoutMemory.risk_assessment}</p>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                    <div className="p-3 rounded-lg bg-hall-3/40 border border-rack">
                      <span className="text-[10px] text-mist block">Cited Episodes</span>
                      <span className="text-sm font-semibold text-mist">{withoutMemory.cited_episodes ?? 0}</span>
                    </div>
                    <div className="p-3 rounded-lg bg-hall-3/40 border border-rack">
                      <span className="text-[10px] text-mist block">Est. Water Saving</span>
                      <span className="text-sm font-semibold text-mist">{fmt(withoutMemory.expected_water_saving, "%")}</span>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-rack/30 text-[11px] font-mono text-mist/70">
              {showBaseline
                ? `❌ LangGraph run_id ${withoutMemory?.run_id?.slice(0, 8) ?? "—"} — use_memory=false, no retrieval.`
                : "Server-side baseline: same pipeline, memory retrieval disabled."}
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
                {withMemory && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-mono bg-signal/20 text-signal border border-signal/40 font-semibold">
                    <CheckCircle2 size={13} /> {Math.round(withMemory.confidence_pct ?? withMemory.confidence * 100)}% Confidence
                  </span>
                )}
              </div>

              {!showMemory ? (
                <PlaceholderPanel side="memory" loading={loading} phase={phase} />
              ) : (
                <>
                  <div className="rounded-xl bg-signal/10 p-4 border border-signal/30">
                    <span className="text-[10px] font-mono text-signal uppercase tracking-wider block mb-1 font-semibold">
                      Memory-Informed Strategy
                    </span>
                    <p className="text-sm font-semibold text-frost">{withMemory.recommendation}</p>
                  </div>

                  <div className="rounded-xl bg-hall-3/80 p-4 border border-coolant/30 space-y-2">
                    <span className="text-[10px] font-mono text-flow uppercase tracking-wider block font-semibold">
                      Contextual Rationale & Historical Proof
                    </span>
                    <p className="text-xs text-fog leading-relaxed">
                      {withMemory.explanation ?? withMemory.rationale}
                    </p>
                    {withMemory.historical_evidence?.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {withMemory.historical_evidence.slice(0, 3).map((ep) => (
                          <li key={ep.episode_id ?? ep.memory_id} className="text-[10px] font-mono text-mist truncate">
                            ✓ {ep.action_taken?.slice(0, 55)}{(ep.action_taken?.length ?? 0) > 55 ? "…" : ""}
                            {ep.water_delta_pct != null && (
                              <span className="text-signal ml-1">({ep.water_delta_pct.toFixed(1)}% water)</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                    <div className="p-3 rounded-lg bg-hall-3 border border-rack">
                      <span className="text-[10px] text-mist block">Cited Episodes</span>
                      <span className="text-sm font-semibold text-flow">
                        {withMemory.cited_episodes ?? compareData?.episodes?.success_count ?? 0} resolved
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-hall-3 border border-rack">
                      <span className="text-[10px] text-mist block">Est. Water Saving</span>
                      <span className="text-sm font-semibold text-signal">{fmt(withMemory.expected_water_saving, "%")}</span>
                    </div>
                  </div>

                  {withMemory.failure_memory_avoided && (
                    <div className="rounded-xl bg-alert/10 border border-alert/30 p-3 flex items-start gap-2 text-xs font-mono text-alert">
                      <ShieldAlert size={14} className="flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold block uppercase text-[9px]">Failure Memory Callout</span>
                        {withMemory.failure_memory_avoided}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-rack/50 text-[11px] font-mono text-signal">
              {showMemory
                ? `✓ LangGraph run_id ${withMemory?.run_id?.slice(0, 8) ?? "—"} — ${compareData?.episodes?.success_count ?? 0} success / ${compareData?.episodes?.failure_count ?? 0} failed episodes from DB.`
                : "Full agentic pipeline with vector search + StrategyScore + episode reflect."}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Fleet Reasoning Results Section */}
      {fleetResult && (
        <section className="max-w-7xl mx-auto px-5 md:px-8 py-8">
          <div className="card-glass rounded-2xl p-6 border border-flow/30">
            <h2 className="text-xl font-heading font-semibold text-frost mb-4 flex items-center gap-2">
              <Brain size={20} className="text-flow" />
              Fleet Reasoning Results (100 Racks)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div>
                <div className="text-mist text-sm">Successful Racks</div>
                <div className="text-2xl font-bold text-signal">{fleetResult.successful_racks}/{fleetResult.fleet_size}</div>
              </div>
              <div>
                <div className="text-mist text-sm">Failed Racks</div>
                <div className="text-2xl font-bold text-alert">{fleetResult.failed_racks}</div>
              </div>
              <div>
                <div className="text-mist text-sm">Total Water Savings</div>
                <div className="text-2xl font-bold text-coolant">{fleetResult.total_expected_savings.toFixed(2)} L/hr</div>
              </div>
              <div>
                <div className="text-mist text-sm">Avg Confidence</div>
                <div className="text-2xl font-bold text-flow">{(fleetResult.avg_confidence * 100).toFixed(1)}%</div>
              </div>
            </div>
            <div className="text-xs text-mist font-mono">
              Run the reasoning loop from the Dashboard to generate fleet-wide results.
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
