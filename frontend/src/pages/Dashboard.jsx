import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Cpu, Thermometer, Droplets, Gauge, BrainCircuit, Search,
  Download, RefreshCw, Wifi, WifiOff, AlertCircle, Fan, BatteryMedium,
  Zap, Database, ShieldCheck, Server
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line
} from "recharts";
import { useLiveTelemetry } from "../hooks/useLiveTelemetry";
import {
  searchMemory, downloadDailyReport, postRecommend, getEnterpriseDashboard,
  postReason, postMemorySearch
} from "../lib/api";
import StatCard from "../components/ui/StatCard";
import AmbientVeil from "../components/ui/AmbientVeil";
import AgentExplanationPanel from "../components/AgentExplanationPanel";

function ConnectionBadge({ status }) {
  const map = {
    connecting: { icon: RefreshCw, text: "Connecting…", cls: "text-mist border-rack-2 bg-hall-2" },
    live: { icon: Wifi, text: "Live — CockroachDB MCP & Bedrock Connected", cls: "text-signal border-signal/30 bg-signal/10" },
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
  const [reasonLoading, setReasonLoading] = useState(false);
  const [reasoningData, setReasoningData] = useState(null);
  const [dashData, setDashData] = useState(null);

  const telemetry = data?.latest_telemetry;
  const water = data?.latest_water_model;

  const fetchDashboardData = async () => {
    try {
      const res = await getEnterpriseDashboard();
      setDashData(res);
    } catch (e) {
      console.warn("Could not fetch enterprise dashboard endpoint", e);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [data]);

  const handleReason = async () => {
    setReasonLoading(true);
    try {
      const res = await postReason(telemetry?.telemetry_id);
      setReasoningData(res);
      await fetchDashboardData();
      await refresh();
    } catch (err) {
      console.error("Reasoning call failed", err);
    } finally {
      setReasonLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await postMemorySearch(query, 5);
      const combined = [
        ...(res.similar_incidents || []).map(i => ({ memory_id: i.incident_id, type: "incident", summary_text: `${i.description} (Root cause: ${i.root_cause})`, similarity: i.similarity })),
        ...(res.previous_recommendations || []).map(r => ({ memory_id: r.recommendation_id, type: "recommendation", summary_text: `${r.recommendation_text} (Water Saving: ${r.expected_water_saving}%)`, similarity: r.similarity })),
      ];
      setMemories(combined);
    } catch {
      setMemories([]);
    } finally {
      setSearching(false);
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
      alert("Could not reach backend report endpoint.");
    }
  };

  const gpuChartData = dashData?.charts?.gpu_usage || [
    { timestamp: "19:00", gpu_usage: 65, cpu_usage: 40 },
    { timestamp: "19:05", gpu_usage: 78, cpu_usage: 45 },
    { timestamp: "19:10", gpu_usage: 91, cpu_usage: 52 },
    { timestamp: "19:15", gpu_usage: 84, cpu_usage: 48 },
    { timestamp: "19:20", gpu_usage: 88, cpu_usage: 50 },
  ];

  const waterChartData = dashData?.charts?.water_consumption || [
    { timestamp: "19:00", predicted_water: 1.6, saved_water: 0.3 },
    { timestamp: "19:05", predicted_water: 1.8, saved_water: 0.35 },
    { timestamp: "19:10", predicted_water: 2.1, saved_water: 0.42 },
    { timestamp: "19:15", predicted_water: 1.9, saved_water: 0.38 },
    { timestamp: "19:20", predicted_water: 1.7, saved_water: 0.32 },
  ];

  return (
    <div className="relative bg-abyss min-h-screen">
      <section className="relative pt-28 pb-10 border-b border-rack overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-7xl mx-auto px-5 md:px-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono">Agentic Digital Twin</span>
              <h1 className="font-heading text-3xl md:text-4xl font-semibold text-frost mt-2">
                RackPulse Enterprise Dashboard
              </h1>
              <p className="text-sm text-mist mt-1">CockroachDB Managed MCP Server + Amazon Bedrock Agentic Memory</p>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <ConnectionBadge status={status} />
              <button
                onClick={handleReason}
                disabled={reasonLoading}
                className="inline-flex items-center gap-2 rounded-lg bg-coolant/90 hover:bg-coolant disabled:opacity-60 px-4 py-2 text-xs font-semibold text-abyss transition-colors"
              >
                {reasonLoading ? <RefreshCw size={13} className="animate-spin" /> : <BrainCircuit size={13} />}
                Run Bedrock Reasoning Loop
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 md:px-8 py-10 space-y-8">
        {/* KPI CARDS GRID */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Zap} label="Current GPU Usage" value={telemetry?.gpu_pct ?? dashData?.current_gpu ?? 91} unit="%" accent="coolant" />
          <StatCard icon={Cpu} label="Current CPU Usage" value={telemetry?.cpu_pct ?? dashData?.current_cpu ?? 48} unit="%" accent="flow" />
          <StatCard icon={Thermometer} label="Ambient Weather" value={`${dashData?.weather_temp ?? 39}°C`} unit={`${dashData?.humidity ?? 62}% RH`} accent="amber" />
          <StatCard icon={Droplets} label="Predicted Water" value={dashData?.predicted_water_usage ?? 1.45} unit="L/hr" accent="signal" />
          <StatCard icon={Gauge} label="Water Saved Today" value={dashData?.water_saved_today_liters ?? 184.5} unit="Liters" accent="signal" />
          <StatCard icon={ShieldCheck} label="Memory Confidence" value={`${dashData?.memory_confidence_pct ?? 93}%`} unit="Match Score" accent="coolant" />
          <StatCard icon={Database} label="Historical Matches" value={dashData?.historical_matches_count ?? 24} unit="Memories" accent="flow" />
          <StatCard icon={Server} label="OpenDC Fleet (Racks 1-100)" value={dashData?.opendc_fleet?.rack_count ?? 100} unit="Active Racks" accent="amber" />
        </div>

        {/* AGENT EXPLANATION PANEL */}
        <AgentExplanationPanel reasoningData={reasoningData || {
          recommendation: dashData?.latest_recommendation?.text || "Deploy Hybrid Evaporative Liquid Cooling across GPU Cluster (Rack 1-100)",
          explanation: "CockroachDB Managed MCP retrieved 24 similar historical incidents matching 39°C ambient temperature spikes.",
          root_cause: "Parallel matrix multiplication training workload combined with high humidity ambient air.",
          expected_water_saving: dashData?.latest_recommendation?.expected_water_saving || 17.8,
          confidence_pct: dashData?.memory_confidence_pct || 93,
          matched_memories_count: dashData?.historical_matches_count || 24,
          historical_evidence: [
            { memory_id: "Incident #182", summary: "High GPU temperature at 38°C ambient - Hybrid Cooling applied" },
            { memory_id: "Incident #201", summary: "Peak load water surge - Evaporative strategy reduced 18% water" },
            { memory_id: "Incident #233", summary: "Multi-rack scaling thermal cluster - Liquid cooling baseline matched" },
          ],
          thermodynamic_metrics: { ambient_temp: dashData?.weather_temp || 39, humidity: dashData?.humidity || 62 }
        }} />

        {/* CHARTS ROW */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* GPU & CPU CHART */}
          <div className="card-glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-heading font-semibold text-frost">GPU & CPU Utilization Trend</h2>
              <span className="font-mono text-xs text-mist">Device: {telemetry?.device_id ?? "Rack-1 (Laptop)"}</span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={gpuChartData}>
                  <defs>
                    <linearGradient id="gpuGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2b7fff" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#2b7fff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#16273a" vertical={false} />
                  <XAxis dataKey="timestamp" tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} />
                  <YAxis tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} width={32} />
                  <Tooltip contentStyle={{ background: "#0a1420", border: "1px solid #16273a", borderRadius: 8, fontSize: 12 }} />
                  <Area type="monotone" dataKey="gpu_usage" name="GPU %" stroke="#2b7fff" strokeWidth={2} fill="url(#gpuGrad)" />
                  <Area type="monotone" dataKey="cpu_usage" name="CPU %" stroke="#22d3ee" strokeWidth={2} fill="transparent" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* WATER CONSUMPTION CHART */}
          <div className="card-glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-heading font-semibold text-frost">Thermodynamic Water Savings (L/hr)</h2>
              <span className="font-mono text-xs text-signal">Strategy: Hybrid Evaporative</span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={waterChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#16273a" vertical={false} />
                  <XAxis dataKey="timestamp" tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} />
                  <YAxis tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} width={32} />
                  <Tooltip contentStyle={{ background: "#0a1420", border: "1px solid #16273a", borderRadius: 8, fontSize: 12 }} />
                  <Line type="monotone" dataKey="predicted_water" name="Baseline Water (L/hr)" stroke="#f59e0b" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="saved_water" name="Water Saved (L/hr)" stroke="#10b981" strokeWidth={2.5} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* MEMORY SEARCH & REPORTS ROW */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* COCKROACHDB VECTOR INDEX MEMORY SEARCH */}
          <div className="lg:col-span-2 card-glass rounded-2xl p-6">
            <h2 className="font-heading font-semibold text-frost mb-4">CockroachDB Managed MCP Memory Search</h2>
            <form onSubmit={handleSearch} className="flex gap-2 mb-4">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. high GPU thermal spike at 39°C"
                className="flex-1 rounded-lg bg-hall-2 border border-rack-2 focus:border-coolant px-4 py-2.5 text-sm text-fog placeholder:text-mist outline-none transition-colors"
              />
              <button
                type="submit"
                disabled={searching}
                className="inline-flex items-center gap-2 rounded-lg border border-rack-2 bg-hall-3 px-4 py-2.5 text-sm font-medium text-fog hover:border-coolant transition-colors"
              >
                <Search size={15} /> Search MCP Memory
              </button>
            </form>
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {memories === null && (
                <p className="text-sm text-mist">Execute vector searches over CockroachDB distributed vector index.</p>
              )}
              {memories?.length === 0 && (
                <p className="text-sm text-mist">No matching memories found.</p>
              )}
              {memories?.map((m, idx) => (
                <div key={idx} className="rounded-lg bg-hall-2 border border-rack p-3.5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-flow uppercase">{m.type}</span>
                    <span className="text-xs font-mono text-signal">
                      {Math.round((m.similarity ?? 0.9) * 100)}% Match
                    </span>
                  </div>
                  <p className="text-sm text-fog">{m.summary_text}</p>
                </div>
              ))}
            </div>
          </div>

          {/* REPORTS */}
          <div className="card-glass rounded-2xl p-6">
            <h2 className="font-heading font-semibold text-frost mb-4">Export Operational Report</h2>
            <p className="text-sm text-mist leading-relaxed mb-5">
              Export telemetry logs, thermodynamic water calculations, and Amazon Bedrock agent recommendations.
            </p>
            <div className="flex flex-col gap-2.5">
              <button
                onClick={() => handleDownload("csv")}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-rack-2 bg-hall-2 hover:border-coolant px-4 py-2.5 text-sm font-medium text-fog transition-colors"
              >
                <Download size={14} /> Download CSV Report
              </button>
              <button
                onClick={() => handleDownload("pdf")}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-rack-2 bg-hall-2 hover:border-coolant px-4 py-2.5 text-sm font-medium text-fog transition-colors"
              >
                <Download size={14} /> Download PDF Report
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

