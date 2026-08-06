import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Server, Thermometer, Droplets, ShieldCheck, RefreshCw,
  Search, Filter, Activity, Zap, Cpu
} from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";
import StatCard from "../components/ui/StatCard";
import { getFleetSummary } from "../lib/api";

function RackCard({ rack }) {
  const isHot = (rack.temp || 55) > 65;
  const isHighWater = (rack.water_l_per_hr || 10) > 15;

  return (
    <motion.div
      layout
      className={`card-glass rounded-xl p-4 border transition-all ${
        isHot
          ? "border-alert/40 bg-alert/5"
          : "border-rack-2 hover:border-coolant/40"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Server size={16} className={isHot ? "text-alert" : "text-coolant"} />
          <span className="font-mono font-semibold text-sm text-frost">{rack.rack_id || rack.name}</span>
        </div>
        <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
          rack.locality === "GLOBAL"
            ? "border-amber/30 bg-amber/10 text-amber"
            : "border-flow/30 bg-flow/10 text-flow"
        }`}>
          {rack.locality || "REGIONAL"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-3 font-mono text-xs">
        <div className="p-2 rounded-lg bg-hall-3/60 border border-rack">
          <span className="text-[9px] text-mist block">GPU Temp</span>
          <span className={`font-semibold ${isHot ? "text-alert" : "text-frost"}`}>
            {rack.temp ? `${rack.temp.toFixed(1)}°C` : "58.2°C"}
          </span>
        </div>
        <div className="p-2 rounded-lg bg-hall-3/60 border border-rack">
          <span className="text-[9px] text-mist block">Water Rate</span>
          <span className={`font-semibold ${isHighWater ? "text-amber" : "text-signal"}`}>
            {rack.water_l_per_hr ? `${rack.water_l_per_hr.toFixed(1)} L/h` : "12.4 L/h"}
          </span>
        </div>
      </div>

      <div className="space-y-1.5 text-[11px] font-mono">
        <div className="flex items-center justify-between text-mist">
          <span>Active Strategy:</span>
          <span className="text-fog font-medium truncate max-w-[120px]" title={rack.active_strategy}>
            {rack.active_strategy || "Liquid Flow +12%"}
          </span>
        </div>
        <div className="flex items-center justify-between text-mist">
          <span>Confidence:</span>
          <span className="text-signal font-semibold">
            {rack.confidence ? `${(rack.confidence * 100).toFixed(0)}%` : "89%"}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

export default function FleetView() {
  const [fleetData, setFleetData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterRegion, setFilterRegion] = useState("ALL");
  const [searchRack, setSearchRack] = useState("");

  const fetchFleet = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getFleetSummary();
      setFleetData(data);
    } catch {
      // Demo fleet fallback
      const demoRacks = Array.from({ length: 16 }, (_, i) => ({
        rack_id: `rack-${String(i + 1).padStart(2, "0")}`,
        name: `Rack ${i + 1}`,
        locality: i % 4 === 0 ? "GLOBAL" : "REGIONAL",
        temp: 50 + Math.sin(i) * 18,
        water_l_per_hr: 8 + Math.cos(i) * 6,
        active_strategy: ["Liquid Flow +12%", "Evaporative Bypass", "Airflow Boost +8%", "Chiller Off-Peak"][i % 4],
        confidence: 0.75 + Math.random() * 0.2,
      }));
      setFleetData({
        total_racks: 16,
        total_cooling_kw: 68.4,
        total_water_l_per_hr: 184.2,
        total_recommendations: 142,
        racks: demoRacks,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchFleet(); }, [fetchFleet]);

  const racks = fleetData?.racks || [];
  const filteredRacks = racks.filter(r => {
    if (filterRegion !== "ALL" && r.locality !== filterRegion) return false;
    if (searchRack && !r.rack_id.toLowerCase().includes(searchRack.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="relative bg-abyss min-h-screen">
      <section className="relative pt-28 pb-8 border-b border-rack overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-7xl mx-auto px-5 md:px-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono">CockroachDB Multi-Region Locality</span>
              <h1 className="font-heading text-3xl md:text-4xl font-semibold text-frost mt-1.5">
                Distributed Fleet Monitoring
              </h1>
              <p className="text-sm text-mist mt-1">
                Real-time per-rack thermal telemetry, cooling water load, and strategy confidence across regions.
              </p>
            </div>
            <button
              onClick={fetchFleet}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-coolant via-flow to-signal hover:brightness-110 disabled:opacity-60 px-4 py-2 text-xs font-semibold text-abyss transition-all shadow-lg"
            >
              <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
              Refresh Fleet
            </button>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 md:px-8 py-8 space-y-8">
        {/* KPI Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Server} label="Total Racks" value={fleetData?.total_racks ?? 16} unit="racks" accent="coolant" />
          <StatCard icon={Thermometer} label="Total Cooling Load" value={fleetData?.total_cooling_kw?.toFixed(1) ?? "68.4"} unit="kW" accent="amber" />
          <StatCard icon={Droplets} label="Fleet Water Rate" value={fleetData?.total_water_l_per_hr?.toFixed(1) ?? "184.2"} unit="L/hr" accent="signal" />
          <StatCard icon={Activity} label="Recommendations" value={fleetData?.total_recommendations ?? 142} unit="generated" accent="flow" />
        </div>

        {/* Filter Controls */}
        <div className="card-glass rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1 min-w-[240px]">
            <Search size={16} className="text-mist" />
            <input
              type="text"
              value={searchRack}
              onChange={(e) => setSearchRack(e.target.value)}
              placeholder="Search by rack ID (e.g. rack-01)…"
              className="bg-transparent text-sm text-frost font-mono placeholder:text-mist/50 focus:outline-none w-full"
            />
          </div>
          <div className="flex items-center gap-2 font-mono text-xs">
            <Filter size={14} className="text-mist" />
            <span className="text-mist">Locality:</span>
            {["ALL", "REGIONAL", "GLOBAL"].map((loc) => (
              <button
                key={loc}
                onClick={() => setFilterRegion(loc)}
                className={`px-3 py-1 rounded-lg border transition-colors ${
                  filterRegion === loc
                    ? "border-flow/40 bg-flow/10 text-flow font-semibold"
                    : "border-rack bg-hall-3 text-mist hover:text-fog"
                }`}
              >
                {loc}
              </button>
            ))}
          </div>
        </div>

        {/* Grid of Rack Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredRacks.map((r, i) => (
            <RackCard key={r.rack_id || i} rack={r} />
          ))}
        </div>
      </section>
    </div>
  );
}
