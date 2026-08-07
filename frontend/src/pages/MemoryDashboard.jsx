import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Database, Brain, CheckCircle2, XCircle, BarChart3, TrendingUp,
  RefreshCw, Trophy, AlertTriangle, Droplets, Zap, Clock
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid
} from "recharts";
import { getEpisodesReplay, getMemoryHistory, getComprehensiveStats } from "../lib/api";
import AmbientVeil from "../components/ui/AmbientVeil";
import StatCard from "../components/ui/StatCard";

const PIE_COLORS = ["#34e0a1", "#ff6b6b", "#7d93ad"];

function StrategyBar({ name, confidence, successCount, failureCount }) {
  const total = successCount + failureCount;
  const pct = Math.round(confidence * 100);
  return (
    <div className="group">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-fog font-mono truncate max-w-[200px]" title={name}>{name.slice(0, 50)}{name.length > 50 ? "…" : ""}</span>
        <span className="text-xs font-mono text-signal font-semibold">{pct}%</span>
      </div>
      <div className="h-2 bg-hall-3 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="h-full rounded-full bg-gradient-to-r from-coolant to-signal"
        />
      </div>
      <div className="flex items-center gap-2 mt-0.5">
        <span className="text-[9px] font-mono text-mist">{total} runs</span>
        <span className="text-[9px] font-mono text-signal">{successCount}✓</span>
        <span className="text-[9px] font-mono text-alert">{failureCount}✗</span>
      </div>
    </div>
  );
}

function EpisodeCard({ ep }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.div
      layout
      className={`rounded-xl border p-3 cursor-pointer transition-all ${
        ep.success
          ? "border-signal/20 bg-signal/5 hover:border-signal/40"
          : "border-alert/20 bg-alert/5 hover:border-alert/40"
      }`}
      onClick={() => setOpen(!open)}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {ep.success ? (
            <CheckCircle2 size={14} className="text-signal flex-shrink-0" />
          ) : (
            <XCircle size={14} className="text-alert flex-shrink-0" />
          )}
          <span className="text-xs font-mono text-fog truncate max-w-[180px]">{ep.action_taken?.slice(0, 50)}</span>
        </div>
        <span className={`text-xs font-mono font-semibold ${ep.success ? "text-signal" : "text-alert"}`}>
          {ep.reward?.toFixed(2)}
        </span>
      </div>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2 pt-2 border-t border-rack/30 grid grid-cols-2 gap-2">
              <div className="text-[10px] text-mist font-mono">Water Δ: <span className={ep.water_delta_pct < 0 ? "text-signal" : "text-alert"}>{ep.water_delta_pct?.toFixed(1)}%</span></div>
              <div className="text-[10px] text-mist font-mono">Temp Δ: <span className={ep.temp_delta_c < 0 ? "text-signal" : "text-alert"}>{ep.temp_delta_c?.toFixed(1)}°C</span></div>
              <div className="text-[10px] text-mist font-mono">Confidence: <span className="text-coolant-2">{(ep.confidence_at_decision * 100)?.toFixed(0)}%</span></div>
              <div className="text-[10px] text-mist font-mono">Rack: <span className="text-fog">{ep.rack_id || "n/a"}</span></div>
              {ep.incident_occurred && (
                <div className="col-span-2 text-[10px] text-alert font-mono flex items-center gap-1">
                  <AlertTriangle size={10} /> Incident occurred during episode
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function MemoryDashboard() {
  const [episodes, setEpisodes] = useState([]);
  const [memories, setMemories] = useState([]);
  const [comprehensiveStats, setComprehensiveStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch comprehensive stats, episodes, and memory history
      const [comprehensiveStats, episodesData, memoriesData] = await Promise.all([
        getComprehensiveStats(),
        getEpisodesReplay({ limit: 200, includeUnresolved: true }),
        getMemoryHistory(100)
      ]);
      console.log('=== MEMORY DASHBOARD DEBUG ===');
      console.log('Comprehensive Stats:', comprehensiveStats);
      console.log('API Response - Episodes:', episodesData);
      console.log('API Response - Memories:', memoriesData);
      console.log('Episodes length:', episodesData?.length, 'Memories length:', memoriesData?.length);
      console.log('============================');
      
      // Set comprehensive stats if available
      if (comprehensiveStats) {
        setComprehensiveStats(comprehensiveStats);
        setMemories(memoriesData || []);
        // Use episodes replay data if available, otherwise fallback to comprehensive stats
        setEpisodes(episodesData?.length > 0 ? episodesData : []);
      } else {
        setMemories(memoriesData || []);
        setEpisodes(episodesData || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      // Set empty arrays on error - don't use demo data
      setEpisodes([]);
      setMemories([]);
      setComprehensiveStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Derived stats - use comprehensive stats if available, otherwise calculate from raw data
  const totalEpisodes = comprehensiveStats?.episode_stats?.total_episodes || episodes.length;
  const resolvedEpisodes = comprehensiveStats?.episode_stats?.resolved_episodes || episodes.filter(e => e.outcome_recorded_at).length;
  const unresolvedEpisodes = comprehensiveStats?.episode_stats?.unresolved_episodes || (totalEpisodes - resolvedEpisodes);
  const successEpisodes = comprehensiveStats?.episode_stats?.successful_episodes || episodes.filter(e => e.success === true).length;
  const failedEpisodes = comprehensiveStats?.episode_stats?.failed_episodes || episodes.filter(e => e.success === false).length;
  const avgReward = comprehensiveStats?.episode_stats?.avg_reward || (totalEpisodes > 0 ? (episodes.reduce((s, e) => s + (e.reward || 0), 0) / totalEpisodes).toFixed(2) : "0.00");
  
  // Memory stats - use comprehensive stats if available, otherwise calculate from raw data
  const totalMemories = comprehensiveStats?.memory_stats?.total_memories || memories.length;
  const recommendationMemories = comprehensiveStats?.memory_stats?.recommendation_memories || memories.filter(m => m.memory_type === "recommendation").length;
  const incidentMemories = comprehensiveStats?.memory_stats?.incident_memories || memories.filter(m => m.memory_type === "incident").length;
  const hotMemories = comprehensiveStats?.memory_stats?.hot_memories || memories.filter(m => {
    const createdTime = new Date(m.created_at).getTime();
    const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;
    return createdTime > oneDayAgo;
  }).length;

  // Strategy scores derived from episodes - use raw episode data for detailed analysis
  const strategyMap = {};
  episodes.forEach(ep => {
    const key = ep.action_taken || "unknown";
    if (!strategyMap[key]) strategyMap[key] = { name: key, successCount: 0, failureCount: 0 };
    if (ep.success) strategyMap[key].successCount++;
    else strategyMap[key].failureCount++;
  });
  const strategies = Object.values(strategyMap).map(s => ({
    ...s,
    confidence: (s.successCount + 1) / (s.successCount + s.failureCount + 2),
  })).sort((a, b) => b.confidence - a.confidence);

  // Pie chart data
  const pieData = [
    { name: "Success", value: successEpisodes },
    { name: "Failed", value: failedEpisodes },
  ];

  // Episode growth over time (bucket by day)
  const dayBuckets = {};
  episodes.forEach(ep => {
    const day = ep.created_at?.split("T")[0] || "unknown";
    dayBuckets[day] = (dayBuckets[day] || 0) + 1;
  });
  const growthData = Object.entries(dayBuckets)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, count]) => ({ day: day.slice(5), count }));

  // Confidence calibration data (bucket by confidence decile)
  const calibrationBuckets = {};
  episodes.forEach(ep => {
    const bucket = Math.floor((ep.confidence_at_decision || 0) * 10) / 10;
    const key = `${Math.round(bucket * 100)}%`;
    if (!calibrationBuckets[key]) calibrationBuckets[key] = { predicted: key, total: 0, successes: 0 };
    calibrationBuckets[key].total++;
    if (ep.success) calibrationBuckets[key].successes++;
  });
  const calibrationData = Object.values(calibrationBuckets)
    .map(b => ({ ...b, actual: b.total > 0 ? Math.round((b.successes / b.total) * 100) : 0, predicted_val: parseInt(b.predicted) }))
    .sort((a, b) => a.predicted_val - b.predicted_val);

  return (
    <div className="relative bg-abyss min-h-screen">
      <section className="relative pt-28 pb-8 border-b border-rack overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-7xl mx-auto px-5 md:px-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono">Agentic Memory Architecture</span>
              <h1 className="font-heading text-3xl md:text-4xl font-semibold text-frost mt-1.5">
                Memory Intelligence Dashboard
              </h1>
              <p className="text-sm text-mist mt-1">Episode history, strategy scoring, and memory retrieval analytics</p>
            </div>
            <button
              onClick={fetchData}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-coolant via-flow to-signal hover:brightness-110 disabled:opacity-60 px-4 py-2 text-xs font-semibold text-abyss transition-all shadow-lg"
            >
              <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
              Refresh Data
            </button>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 md:px-8 py-8 space-y-8">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Database} label="Total Memories" value={totalMemories} unit="stored" accent="coolant" />
          <StatCard icon={Brain} label="Recommendations" value={recommendationMemories} unit="strategies" accent="signal" />
          <StatCard icon={AlertTriangle} label="Incidents" value={incidentMemories} unit="learned" accent="alert" />
          <StatCard icon={Zap} label="Hot Memory" value={hotMemories} unit="active" accent="flow" />
        </div>

        {/* Episode Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Database} label="Total Episodes" value={totalEpisodes} unit="created" accent="coolant" />
          <StatCard icon={Clock} label="Unresolved" value={unresolvedEpisodes} unit="pending" accent="flow" />
          <StatCard icon={CheckCircle2} label="Successful" value={successEpisodes} unit="confirmed" accent="signal" />
          <StatCard icon={XCircle} label="Failed" value={failedEpisodes} unit="confirmed" accent="alert" />
        </div>

        {/* Strategy Confidence + Pie Chart */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Strategy Score Bars */}
          <div className="lg:col-span-2 card-glass rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-5">
              <Trophy size={16} className="text-amber" />
              <h2 className="font-heading font-semibold text-frost">StrategyScore Confidence</h2>
              <span className="text-[10px] font-mono text-mist ml-auto">Beta-distribution mean</span>
            </div>
            <div className="space-y-4">
              {strategies.length > 0 ? strategies.slice(0, 6).map((s, i) => (
                <StrategyBar key={i} name={s.name} confidence={s.confidence} successCount={s.successCount} failureCount={s.failureCount} />
              )) : (
                <p className="text-sm text-mist font-mono text-center py-8">No strategy data yet — run the reasoning loop to generate episodes</p>
              )}
            </div>
          </div>

          {/* Success/Failure Pie */}
          <div className="card-glass rounded-2xl p-6 flex flex-col items-center justify-center">
            <h2 className="font-heading font-semibold text-frost mb-4">Outcome Split</h2>
            {totalEpisodes > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0a1420", border: "1px solid #16273a", borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-[200px]">
                <Database size={32} className="text-rack-2 mb-2" />
                <p className="text-xs text-mist font-mono">No episodes</p>
              </div>
            )}
            <div className="flex items-center gap-4 mt-2">
              <span className="flex items-center gap-1.5 text-xs font-mono"><span className="w-2.5 h-2.5 rounded-full bg-signal" />Success</span>
              <span className="flex items-center gap-1.5 text-xs font-mono"><span className="w-2.5 h-2.5 rounded-full bg-alert" />Failed</span>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Episode Growth */}
          <div className="card-glass rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-5">
              <BarChart3 size={16} className="text-coolant" />
              <h2 className="font-heading font-semibold text-frost">Memory Growth Over Time</h2>
            </div>
            <div className="h-52">
              {growthData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={growthData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#16273a" vertical={false} />
                    <XAxis dataKey="day" tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} />
                    <YAxis tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} width={28} />
                    <Tooltip contentStyle={{ background: "#0a1420", border: "1px solid #16273a", borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="count" name="Episodes" fill="#2b7fff" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-xs text-mist font-mono">No growth data</div>
              )}
            </div>
          </div>

          {/* Confidence Calibration Chart */}
          <div className="card-glass rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-5">
              <TrendingUp size={16} className="text-signal" />
              <h2 className="font-heading font-semibold text-frost">Confidence Calibration</h2>
              <span className="text-[10px] font-mono text-mist ml-auto">predicted vs actual success rate</span>
            </div>
            <div className="h-52">
              {calibrationData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={calibrationData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#16273a" vertical={false} />
                    <XAxis dataKey="predicted" tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} />
                    <YAxis tick={{ fill: "#7d93ad", fontSize: 10 }} axisLine={{ stroke: "#16273a" }} width={32} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: "#0a1420", border: "1px solid #16273a", borderRadius: 8, fontSize: 12 }} />
                    <Line type="monotone" dataKey="predicted_val" name="Predicted %" stroke="#2b7fff" strokeWidth={1.5} strokeDasharray="5 5" dot={false} />
                    <Line type="monotone" dataKey="actual" name="Actual %" stroke="#34e0a1" strokeWidth={2.5} dot={{ fill: "#34e0a1", r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-xs text-mist font-mono">No calibration data</div>
              )}
            </div>
          </div>
        </div>

        {/* Recent Memory History */}
        <div className="card-glass rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Brain size={16} className="text-coolant-2" />
            <h2 className="font-heading font-semibold text-frost">Recent Memory History</h2>
            <span className="text-[10px] font-mono text-mist ml-auto">{totalMemories} total</span>
          </div>
          <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1" style={{ scrollbarWidth: "thin", scrollbarColor: "#223850 #070d16" }}>
            {memories.length > 0 ? (
              memories.map((m, i) => (
                <div key={m.id || m.memory_id || i} className={`rounded-lg border p-3 transition-colors ${
                  m.memory_type === "recommendation" 
                    ? "bg-signal/5 border-signal/20 hover:border-signal/40" 
                    : "bg-alert/5 border-alert/20 hover:border-alert/40"
                }`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono text-flow flex items-center gap-1">
                      {m.memory_type === "recommendation" ? <CheckCircle2 size={10} className="text-signal" /> : <AlertTriangle size={10} className="text-alert" />}
                      {m.id || m.memory_id}
                    </span>
                    <span className={`text-[10px] font-mono ${new Date(m.created_at) > new Date(Date.now() - 24 * 60 * 60 * 1000) ? "text-amber" : "text-mist"}`}>
                      {new Date(m.created_at) > new Date(Date.now() - 24 * 60 * 60 * 1000) ? "hot" : "warm"}
                    </span>
                  </div>
                  <p className="text-xs text-fog">{m.summary || m.summary_text}</p>
                  <div className="text-[9px] font-mono text-mist/70 mt-1">
                    {new Date(m.created_at).toLocaleString()}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-mist text-sm">
                No memory entries found. Run the reasoning loop to generate memories.
              </div>
            )}
          </div>
        </div>

        {/* Recent Episodes */}
        <div className="card-glass rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock size={16} className="text-flow" />
            <h2 className="font-heading font-semibold text-frost">Recent Episode History</h2>
            <span className="text-[10px] font-mono text-mist ml-auto">{totalEpisodes} total</span>
          </div>
          {episodes.length > 0 ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[400px] overflow-y-auto pr-1" style={{ scrollbarWidth: "thin", scrollbarColor: "#223850 #070d16" }}>
              {episodes.slice(0, 15).map((ep, i) => (
                <EpisodeCard key={ep.episode_id || i} ep={ep} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-mist text-sm">
              No episodes found yet. Run the reasoning loop to generate episode data.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
