import { useState } from "react";

import { motion } from "framer-motion";
import {
  Cpu, Thermometer, Droplets, Gauge, BrainCircuit,
  Download, RefreshCw, Wifi, WifiOff, AlertCircle,
  Zap, Database, ShieldCheck, Server, Bot, FileText
} from "lucide-react";

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line
} from "recharts";
import { useLiveTelemetry } from "../hooks/useLiveTelemetry";
import { downloadDailyReport, postReason } from "../lib/api";

import StatCard from "../components/ui/StatCard";
import AmbientVeil from "../components/ui/AmbientVeil";
import AgentExplanationPanel from "../components/AgentExplanationPanel";
import AgentReasoningConsole from "../components/AgentReasoningConsole";
import MCPMemoryChatbot from "../components/MCPMemoryChatbot";

function ConnectionBadge({ status }) {
  const map = {
    connecting: { icon: RefreshCw, text: "Connecting…", cls: "text-mist border-rack-2 bg-hall-2" },
    live: { icon: Wifi, text: "Live — CockroachDB + Ollama Connected", cls: "text-signal border-signal/30 bg-signal/10" },
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
  const [reasonLoading, setReasonLoading] = useState(false);
  const [reasoningData, setReasoningData] = useState(null);
  const [isChatbotOpen, setIsChatbotOpen] = useState(false);

  // useLiveTelemetry now fetches /api/dashboard and exposes the full dashboard
  // shape including charts and latest_telemetry — use it directly.
  const dashData = data;
  const telemetry = data?.latest_telemetry;

  const handleReason = async () => {
    setReasonLoading(true);
    try {
      const res = await postReason(telemetry?.telemetry_id);
      setReasoningData(res);
      await refresh();
    } catch (err) {
      console.error("Reasoning call failed", err);
    } finally {
      setReasonLoading(false);
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

  const defaultExplanation = {
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
  };

  return (
    <div className="relative bg-abyss min-h-screen">
      <section className="relative pt-28 pb-8 border-b border-rack overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-7xl mx-auto px-5 md:px-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono">Agentic Digital Twin</span>
              <h1 className="font-heading text-3xl md:text-4xl font-semibold text-frost mt-1.5">
                AquaRack Enterprise Dashboard
              </h1>
              <p className="text-sm text-mist mt-1">CockroachDB Managed MCP Server + Ollama Agentic Memory</p>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <ConnectionBadge status={status} />
              <button
                onClick={handleReason}
                disabled={reasonLoading}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-coolant via-flow to-signal hover:brightness-110 disabled:opacity-60 px-4 py-2 text-xs font-semibold text-abyss transition-all shadow-lg"
              >
                {reasonLoading ? <RefreshCw size={13} className="animate-spin" /> : <BrainCircuit size={13} />}
                Run Ollama Reasoning Loop
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 md:px-8 py-8 space-y-8">
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

        {/* SIDE-BY-SIDE REASONING LOOP CONTROL & LIVE CONSOLE LOGS */}
        <div className="grid lg:grid-cols-2 gap-6 items-stretch">
          {/* LEFT: AGENT REASONING EXPLANATION & TRIGGER */}
          <AgentExplanationPanel
            reasoningData={reasoningData || defaultExplanation}
            onRunReasoning={handleReason}
            isReasoning={reasonLoading}
          />

          {/* RIGHT: AGENT REASONING CONSOLE (LIVE SSE LOG STREAM) */}
          <AgentReasoningConsole />
        </div>

        {/* CHARTS ROW */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* GPU & CPU CHART */}
          <div className="card-glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-heading font-semibold text-frost">GPU & CPU Utilization Trend</h2>
              <span className="font-mono text-xs text-mist">Device: {telemetry?.device_id ?? "Rack-01 (Primary Cluster)"}</span>
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

        {/* REPORTS ROW */}
        <div className="card-glass rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2 mb-1">
              <FileText size={18} className="text-coolant" />
              <h2 className="font-heading font-semibold text-frost text-lg">Export Operational Report</h2>
            </div>
            <p className="text-sm text-mist leading-relaxed">
              Export telemetry logs, thermodynamic water calculations, and Ollama multi-agent recommendations as downloadable reports.
            </p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <button
              onClick={() => handleDownload("csv")}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-rack-2 bg-hall-2 hover:border-coolant px-4 py-2.5 text-sm font-medium text-fog transition-colors"
            >
              <Download size={14} /> Download CSV Report
            </button>
            <button
              onClick={() => handleDownload("pdf")}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-rack-2 bg-hall-2 hover:border-coolant px-4 py-2.5 text-sm font-medium text-fog transition-colors"
            >
              <Download size={14} /> Download PDF Report
            </button>
          </div>
        </div>
      </section>

      {/* INTERACTIVE COCKROACHDB MCP MEMORY CHATBOT OVERLAY (LAUNCHED VIA FLOATING ACTION ICON) */}
      <MCPMemoryChatbot isOpen={isChatbotOpen} setIsOpen={setIsChatbotOpen} />
    </div>
  );
}
