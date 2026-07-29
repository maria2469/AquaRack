import { useState } from "react";
import { motion } from "framer-motion";
import {
  Cpu, Thermometer, Droplets, Gauge, BrainCircuit, Search,
  Download, RefreshCw, Wifi, WifiOff, AlertCircle, Fan, BatteryMedium,
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { useLiveTelemetry } from "../hooks/useLiveTelemetry";
import { searchMemory, downloadDailyReport, postRecommend } from "../lib/api";
import StatCard from "../components/ui/StatCard";
import AmbientVeil from "../components/ui/AmbientVeil";

function ConnectionBadge({ status }) {
  const map = {
    connecting: { icon: RefreshCw, text: "Connecting…", cls: "text-mist border-rack-2 bg-hall-2" },
    live: { icon: Wifi, text: "Live — backend connected", cls: "text-signal border-signal/30 bg-signal/10" },
    mock: { icon: WifiOff, text: "Demo mode — synthetic stream", cls: "text-amber border-amber/30 bg-amber/10" },
    error: { icon: AlertCircle, text: "Backend unreachable — showing demo stream", cls: "text-alert border-alert/30 bg-alert/10" },
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

export default function Dashboard() {
  const { data, status, refresh } = useLiveTelemetry({ intervalMs: 5000 });
  const [query, setQuery] = useState("");
  const [memories, setMemories] = useState(null);
  const [searching, setSearching] = useState(false);
  const [recLoading, setRecLoading] = useState(false);

  const telemetry = data?.latest_telemetry;
  const water = data?.latest_water_model;
  const rec = data?.latest_recommendation;
  const history = data?.telemetry_history || [];
  const openIncidents = data?.open_incidents ?? 0;

  const chartData = history.map((h) => ({
    time: new Date(h.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    cpu: h.cpu_pct,
    ram: h.ram_pct,
  }));

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const results = await searchMemory(query, 5);
      setMemories(results);
    } catch {
      setMemories([]);
    } finally {
      setSearching(false);
    }
  };

  const handleRecommend = async () => {
    setRecLoading(true);
    try {
      await postRecommend(telemetry?.telemetry_id);
      await refresh();
    } catch {
      // handled by useLiveTelemetry fallback on next poll
    } finally {
      setRecLoading(false);
    }
  };

  const handleDownload = async (format) => {
    try {
      const blob = await downloadDailyReport(format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `aquamind_daily_report.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Could not reach the backend to generate the report. Connect the AquaMind API and try again.");
    }
  };

  return (
    <div className="relative bg-abyss min-h-screen">
      <section className="relative pt-28 pb-10 border-b border-rack overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-7xl mx-auto px-5 md:px-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono">Operations</span>
              <h1 className="font-display text-3xl md:text-4xl font-semibold text-frost mt-2">
                Live Digital Twin Dashboard
              </h1>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <ConnectionBadge status={status} />
              <button
                onClick={refresh}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rack-2 bg-hall-2 px-3.5 py-2 text-xs font-medium text-fog hover:border-coolant transition-colors"
              >
                <RefreshCw size={13} /> Refresh
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 md:px-8 py-10 space-y-8">
        {/* STAT ROW */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Cpu} label="CPU Utilisation" value={telemetry?.cpu_pct ?? "—"} unit="%" accent="coolant" />
          <StatCard icon={Thermometer} label="Thermal Load" value={water?.thermal_load_kw ?? "—"} unit="kW" accent="amber" />
          <StatCard icon={Droplets} label="Water Usage" value={water?.water_l_per_hr ?? "—"} unit="L/hr" accent="flow" />
          <StatCard icon={Gauge} label="WUE Factor" value={water?.wue_factor ?? "—"} unit="L/kWh" accent="signal" />
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* TELEMETRY CHART */}
          <div className="lg:col-span-2 card-glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-display font-semibold text-frost">Telemetry Stream</h2>
              <span className="font-mono text-xs text-mist">device: {telemetry?.device_id ?? "—"}</span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2b7fff" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#2b7fff" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="ramGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#16273a" vertical={false} />
                  <XAxis dataKey="time" tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} tickLine={false} minTickGap={40} />
                  <YAxis tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} tickLine={false} width={32} />
                  <Tooltip
                    contentStyle={{ background: "#0a1420", border: "1px solid #16273a", borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: "#b9c7d6" }}
                  />
                  <Area type="monotone" dataKey="cpu" name="CPU %" stroke="#2b7fff" strokeWidth={2} fill="url(#cpuGrad)" />
                  <Area type="monotone" dataKey="ram" name="RAM %" stroke="#22d3ee" strokeWidth={2} fill="url(#ramGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center gap-5 mt-4 text-xs text-mist">
              <span className="flex items-center gap-1.5"><Fan size={13} /> {telemetry?.fan_rpm ?? "—"} RPM</span>
              <span className="flex items-center gap-1.5"><BatteryMedium size={13} /> {telemetry?.battery_pct ?? "—"}%</span>
              <span className="flex items-center gap-1.5">
                <AlertCircle size={13} className={openIncidents > 0 ? "text-alert" : "text-mist"} />
                {openIncidents} open incident{openIncidents === 1 ? "" : "s"}
              </span>
            </div>
          </div>

          {/* AI RECOMMENDATION */}
          <div className="card-glass rounded-2xl p-6 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display font-semibold text-frost flex items-center gap-2">
                <BrainCircuit size={17} className="text-coolant-2" /> AI Recommendation
              </h2>
            </div>
            {rec ? (
              <div className="flex-1 flex flex-col">
                <p className="text-sm text-fog leading-relaxed flex-1">{rec.text}</p>
                {rec.rationale && (
                  <p className="text-xs text-mist mt-3 italic leading-relaxed">{rec.rationale}</p>
                )}
                <div className="mt-5 flex items-center justify-between text-xs">
                  <span className="font-mono text-mist">{rec.agent_name}</span>
                  <span className="font-mono text-signal">
                    {Math.round((rec.confidence ?? 0) * 100)}% confidence
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-mist">No recommendation yet.</p>
            )}
            <button
              onClick={handleRecommend}
              disabled={recLoading}
              className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-coolant/90 hover:bg-coolant disabled:opacity-60 px-4 py-2.5 text-sm font-semibold text-abyss transition-colors"
            >
              {recLoading ? <RefreshCw size={14} className="animate-spin" /> : <BrainCircuit size={14} />}
              Generate New Recommendation
            </button>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* MEMORY SEARCH */}
          <div className="lg:col-span-2 card-glass rounded-2xl p-6">
            <h2 className="font-display font-semibold text-frost mb-4">Memory Search (RAG)</h2>
            <form onSubmit={handleSearch} className="flex gap-2 mb-4">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. high thermal load, rising fan speed"
                className="flex-1 rounded-lg bg-hall-2 border border-rack-2 focus:border-coolant px-4 py-2.5 text-sm text-fog placeholder:text-mist outline-none transition-colors"
              />
              <button
                type="submit"
                disabled={searching}
                className="inline-flex items-center gap-2 rounded-lg border border-rack-2 bg-hall-3 px-4 py-2.5 text-sm font-medium text-fog hover:border-coolant transition-colors"
              >
                <Search size={15} /> Search
              </button>
            </form>
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {memories === null && (
                <p className="text-sm text-mist">Search past events retrieved via vector similarity.</p>
              )}
              {memories?.length === 0 && (
                <p className="text-sm text-mist">No matching memories found.</p>
              )}
              {memories?.map((m) => (
                <div key={m.memory_id} className="rounded-lg bg-hall-2 border border-rack p-3.5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-flow">{m.type}</span>
                    <span className="text-xs font-mono text-mist">
                      {Math.round((m.similarity ?? 0) * 100)}% match
                    </span>
                  </div>
                  <p className="text-sm text-fog">{m.summary_text}</p>
                </div>
              ))}
            </div>
          </div>

          {/* REPORTS */}
          <div className="card-glass rounded-2xl p-6">
            <h2 className="font-display font-semibold text-frost mb-4">Daily Report</h2>
            <p className="text-sm text-mist leading-relaxed mb-5">
              Export the last 24 hours of telemetry, water estimates, and
              recommendations.
            </p>
            <div className="flex flex-col gap-2.5">
              <button
                onClick={() => handleDownload("csv")}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-rack-2 bg-hall-2 hover:border-coolant px-4 py-2.5 text-sm font-medium text-fog transition-colors"
              >
                <Download size={14} /> Download CSV
              </button>
              <button
                onClick={() => handleDownload("pdf")}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-rack-2 bg-hall-2 hover:border-coolant px-4 py-2.5 text-sm font-medium text-fog transition-colors"
              >
                <Download size={14} /> Download PDF
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
