import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Database, Brain, CheckCircle2, XCircle, BarChart3, TrendingUp,
  RefreshCw, Trophy, AlertTriangle, Droplets, Zap, Clock, Info, Server, BrainCircuit
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid
} from "recharts";
import { getEpisodesReplay, getMemoryHistory, getComprehensiveStats, getDeviceId } from "../lib/api";
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
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-fog">{ep.episode_id?.slice(0, 8)}...</span>
        {ep.success ? (
          <CheckCircle2 size={14} className="text-signal" />
        ) : (
          <XCircle size={14} className="text-alert" />
        )}
      </div>
      <div className="text-xs text-fog line-clamp-2 mb-2">{ep.action_taken}</div>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="text-[10px] text-mist space-y-1 pt-2 border-t border-rack/20"
          >
            <div><span className="text-signal">Confidence:</span> {ep.confidence_at_decision?.toFixed(2)}</div>
            <div><span className="text-flow">Expected Saving:</span> {ep.action_params?.expected_water_saving?.toFixed(3)}L</div>
            <div><span className="text-coolant">Reward:</span> {ep.reward?.toFixed(2)}</div>
            <div><span className="text-mist">Created:</span> {new Date(ep.created_at).toLocaleString()}</div>
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
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [episodesData, memoriesData, statsData] = await Promise.all([
        getEpisodesReplay({ limit: 200, includeUnresolved: true }),
        getMemoryHistory(100),
        getComprehensiveStats()
      ]);
      
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
  
  // Note: These are RL training episodes from recommendation outcomes, NOT fleet rack reasoning results
  // Fleet rack reasoning results are shown on the Fleet Management page
  
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
    .map(([date, count]) => ({ date, count }));

  // Calibration data (placeholder - would come from real calibration runs)
  const calibrationData = [
    { name: "Run 1", predicted: 75, actual: 72 },
    { name: "Run 2", predicted: 68, actual: 71 },
    { name: "Run 3", predicted: 82, actual: 79 },
    { name: "Run 4", predicted: 70, actual: 68 },
    { name: "Run 5", predicted: 78, actual: 76 },
  ];

  return (
    <div className="min-h-screen bg-abyss pt-28">
      <AmbientVeil />
      <div className="relative max-w-7xl mx-auto px-5 md:px-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono">Reinforcement Learning Analytics</span>
            <h1 className="font-heading text-3xl md:text-4xl font-semibold text-frost mt-1.5">
              Memory & Episodes Dashboard
            </h1>
            <p className="text-sm text-mist mt-1">
              RL training episodes, strategy scoring, and memory retrieval analytics
            </p>
            <p className="text-xs text-mist mt-1 opacity-70">
              Current Device: {getDeviceId() || 'Not set'}
            </p>
          </div>
        </div>
      </div>

      <section className="max-w-7xl mx-auto px-5 md:px-8 py-8 space-y-8">
        {/* Empty State */}
        {(totalEpisodes === 0 && totalMemories === 0) && (
          <div className="card-glass rounded-xl p-8 border border-rack mb-6 text-center">
            <Brain size={48} className="text-mist mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-semibold text-frost mb-2">No Memory Data Available</h3>
            <p className="text-sm text-mist mb-4">
              The Memory Dashboard requires RL training episodes to display analytics. 
              Run individual rack reasoning on the Live Dashboard to generate episodes.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => window.location.href = "/dashboard"}
                className="inline-flex items-center gap-2 px-4 py-2 bg-flow/20 border border-flow/50 rounded-lg text-frost hover:bg-flow/30 transition-colors"
              >
                <BrainCircuit size={16} />
                Go to Live Dashboard
              </button>
              <button
                onClick={() => window.location.href = "/fleet"}
                className="inline-flex items-center gap-2 px-4 py-2 bg-coolant/20 border border-coolant/50 rounded-lg text-frost hover:bg-coolant/30 transition-colors"
              >
                <Server size={16} />
                Go to Fleet Management
              </button>
            </div>
          </div>
        )}

        {/* Info Box */}
        <div className="card-glass rounded-xl p-4 border border-rack mb-6">
          <div className="flex items-start gap-3">
            <Info size={20} className="text-coolant mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-frost mb-1">Memory Dashboard Status</h3>
              <p className="text-xs text-mist leading-relaxed">
                This dashboard shows <strong>RL training episodes</strong> and <strong>memory embeddings</strong> for reinforcement learning. 
                These are different from fleet reasoning results which are shown on the <strong>Fleet Management</strong> page.
                <br/><br/>
                <strong>Current Status:</strong>
                <br/>• Episodes: {totalEpisodes} (RL training data)
                <br/>• Memories: {totalMemories} (Historical recommendations/incidents)
                <br/>• Device: {getDeviceId() || 'rack-01-primary'}
                <br/><br/>
                {totalEpisodes === 0 && totalMemories === 0 ? (
                  <span className="text-amber">• No RL training data yet - Run individual rack reasoning on Live Dashboard to generate episodes</span>
                ) : (
                  <span className="text-signal">• RL training data available - Episodes are being collected</span>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* KPI Cards - Only show when data exists */}
        {(totalMemories > 0 || totalEpisodes > 0) && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard icon={Database} label="Total Memories" value={totalMemories} unit="stored" accent="coolant" />
              <StatCard icon={Brain} label="Recommendations" value={recommendationMemories} unit="strategies" accent="signal" />
              <StatCard icon={AlertTriangle} label="Incidents" value={incidentMemories} unit="learned" accent="alert" />
              <StatCard icon={Zap} label="Hot Memory" value={hotMemories} unit="active" accent="flow" />
            </div>

            {/* Episode Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard icon={Database} label="Total Episodes" value={totalEpisodes} unit="RL training" accent="coolant" />
              <StatCard icon={Clock} label="Unresolved" value={unresolvedEpisodes} unit="pending" accent="flow" />
              <StatCard icon={CheckCircle2} label="Successful Episodes" value={successEpisodes} unit="RL outcomes" accent="signal" />
              <StatCard icon={XCircle} label="Failed Episodes" value={failedEpisodes} unit="RL outcomes" accent="alert" />
            </div>
          </>
        )}

        {/* Strategy Confidence + Pie Chart - Only show when data exists */}
        {(totalEpisodes > 0 || totalMemories > 0) && (
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Strategy Score Bars */}
            <div className="lg:col-span-2 card-glass rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <Trophy size={16} className="text-amber" />
                <h2 className="font-heading font-semibold text-frost">Strategy Score Confidence</h2>
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
        )}

        {/* Charts Row - Only show when data exists */}
        {(totalEpisodes > 0 || totalMemories > 0) && (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Episode Growth */}
            <div className="card-glass rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <TrendingUp size={16} className="text-coolant" />
                <h2 className="font-heading font-semibold text-frost">Episode Growth</h2>
                <span className="text-[10px] font-mono text-mist ml-auto">Daily new episodes</span>
              </div>
              {growthData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={growthData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#223850" />
                    <XAxis dataKey="date" stroke="#4a5568" fontSize={10} />
                    <YAxis stroke="#4a5568" fontSize={10} />
                    <Tooltip contentStyle={{ backgroundColor: "#0a1420", border: "1px solid #16273a", borderRadius: 8 }} />
                    <Bar dataKey="count" fill="#34e0a1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-xs text-mist font-mono">No growth data</div>
              )}
            </div>

            {/* Calibration */}
            <div className="card-glass rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <BarChart3 size={16} className="text-flow" />
                <h2 className="font-heading font-semibold text-frost">Calibration</h2>
                <span className="text-[10px] font-mono text-mist ml-auto">Predicted vs Actual</span>
              </div>
              {calibrationData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={calibrationData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#223850" />
                    <XAxis dataKey="name" stroke="#4a5568" fontSize={10} />
                    <YAxis stroke="#4a5568" fontSize={10} />
                    <Tooltip contentStyle={{ backgroundColor: "#0a1420", border: "1px solid #16273a", borderRadius: 8 }} />
                    <Line type="monotone" dataKey="predicted" name="Predicted %" stroke="#7d93ad" strokeWidth={2.5} dot={{ fill: "#7d93ad", r: 4 }} />
                    <Line type="monotone" dataKey="actual" name="Actual %" stroke="#34e0a1" strokeWidth={2.5} dot={{ fill: "#34e0a1", r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-xs text-mist font-mono">No calibration data</div>
              )}
            </div>
          </div>
        )}

        {/* Recent Memory History - Only show when data exists */}
        {(totalMemories > 0) && (
          <div className="card-glass rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <Brain size={16} className="text-coolant-2" />
              <h2 className="font-heading font-semibold text-frost">Recent Memory History</h2>
              <span className="text-[10px] font-mono text-mist ml-auto">{totalMemories} total</span>
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1" style={{ scrollbarWidth: "thin", scrollbarColor: "#223850 #070d16" }}>
              {memories.map((m, i) => (
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
              ))}
            </div>
          </div>
        )}

        {/* Recent Episodes - Only show when data exists */}
        {(totalEpisodes > 0) && (
          <div className="card-glass rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <Clock size={16} className="text-flow" />
              <h2 className="font-heading font-semibold text-frost">Recent Episode History</h2>
              <span className="text-[10px] font-mono text-mist ml-auto">{totalEpisodes} total</span>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[400px] overflow-y-auto pr-1" style={{ scrollbarWidth: "thin", scrollbarColor: "#223850 #070d16" }}>
              {episodes.slice(0, 15).map((ep, i) => (
                <EpisodeCard key={ep.episode_id || i} ep={ep} />
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}