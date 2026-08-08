import { useState, useEffect } from "react";
import { Server, Activity, Droplets, BrainCircuit, RefreshCw, Zap, Cpu, HardDrive, ChevronDown, ChevronUp, TrendingUp, CheckCircle, Clock, Timer, Filter, Search, SortAsc, SortDesc, Gauge, X } from "lucide-react";
import { getGlobalFleetResult, setGlobalFleetResult } from "../lib/globalState";
import { runSingleRackReasoning, getSavedRackResults } from "../lib/api";

// Generate rack profiles client-side for display
const generateRackProfiles = (fleetSize = 100) => {
  const profiles = [];
  for (let i = 1; i <= fleetSize; i++) {
    const rackId = `RACK-${String(i).padStart(3, '0')}`;
    const deviceId = i === 1 ? 'rack-01-primary' : `rack-${String(i).padStart(2, '0')}-primary`;
    
    // Generate deterministic profile variations
    const cpuFactor = 0.85 + (Math.sin(i * 123.456) * 0.15);
    const gpuFactor = 0.85 + (Math.cos(i * 789.012) * 0.15);
    const ramFactor = 0.90 + (Math.sin(i * 345.678) * 0.10);
    const coolingEfficiency = 0.90 + (Math.cos(i * 901.234) * 0.05);
    const hardwareAge = 0.95 + (Math.sin(i * 567.890) * 0.10);
    
    profiles.push({
      rack_id: rackId,
      device_id: deviceId,
      is_laptop: i === 1,
      cpu_factor: cpuFactor,
      gpu_factor: gpuFactor,
      ram_factor: ramFactor,
      cooling_efficiency: coolingEfficiency,
      hardware_age: hardwareAge,
      success: false,
      result: null,
    });
  }
  return profiles;
};

// JSON Tree View Component
const JsonTreeView = ({ data, level = 0 }) => {
  const [expanded, setExpanded] = useState(level < 2); // Auto-expand first 2 levels
  
  if (data === null) return <span className="text-alert">null</span>;
  if (data === undefined) return <span className="text-alert">undefined</span>;
  if (typeof data === 'boolean') return <span className="text-flow">{data.toString()}</span>;
  if (typeof data === 'number') return <span className="text-coolant">{data}</span>;
  if (typeof data === 'string') return <span className="text-fog">"{data}"</span>;
  
  if (Array.isArray(data)) {
    if (data.length === 0) return <span className="text-mist">[]</span>;
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-coolant hover:text-flow flex items-center gap-1"
        >
          {expanded ? <ChevronDown size={10} /> : <ChevronUp size={10} />}
          [{data.length} items]
        </button>
        {expanded && (
          <div className="ml-2 border-l border-rack pl-2">
            {data.map((item, idx) => (
              <div key={idx} className="py-0.5">
                <span className="text-mist text-xs">{idx}:</span>
                <JsonTreeView data={item} level={level + 1} />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  
  if (typeof data === 'object') {
    const keys = Object.keys(data);
    if (keys.length === 0) return <span className="text-mist">{{}}</span>;
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-coolant hover:text-flow flex items-center gap-1"
        >
          {expanded ? <ChevronDown size={10} /> : <ChevronUp size={10} />}
          {'{'}{keys.length} keys{'}'}
        </button>
        {expanded && (
          <div className="ml-2 border-l border-rack pl-2">
            {keys.map(key => (
              <div key={key} className="py-0.5">
                <span className="text-flow text-xs font-mono">{key}:</span>
                <JsonTreeView data={data[key]} level={level + 1} />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  
  return <span className="text-mist">{String(data)}</span>;
};

export default function FleetView() {
  const [fleetResult, setFleetResult] = useState(getGlobalFleetResult() || {
    fleet_size: 100,
    successful_racks: 0,
    failed_racks: 0,
    total_expected_savings: 0,
    avg_confidence: 0,
    timestamp: new Date().toISOString(),
    rack_results: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rackResults, setRackResults] = useState(generateRackProfiles(100));
  const [selectedRack, setSelectedRack] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(null);
  const [filter, setFilter] = useState("all"); // all, pending, completed, failed
  const [sortBy, setSortBy] = useState("rack_id"); // rack_id, confidence, water_savings
  const [sortOrder, setSortOrder] = useState("asc"); // asc, desc
  const [searchQuery, setSearchQuery] = useState("");
  const [rackTimings, setRackTimings] = useState({});

  // Check for updated global result every second
  useEffect(() => {
    const interval = setInterval(() => {
      const current = getGlobalFleetResult();
      if (current && (!fleetResult || current.timestamp !== fleetResult.timestamp)) {
        setFleetResult(current);
        if (current.rack_results && current.rack_results.length > 0) {
          setRackResults(current.rack_results);
        }
      }
    }, 1000);
    
    return () => clearInterval(interval);
  }, [fleetResult]);

  const runRackReasoning = async (rackId, setGlobalLoading = true) => {
    const startTime = Date.now();
    if (setGlobalLoading) {
      setLoading(true);
    }
    setSelectedRack(rackId);
    setError(null);
    
    try {
      const result = await runSingleRackReasoning(rackId, true);
      
      const endTime = Date.now();
      const timing = endTime - startTime;
      
      // Update rack timings
      setRackTimings(prev => ({
        ...prev,
        [rackId]: timing
      }));
      
      // Update the specific rack in the results
      setRackResults(prev => prev.map(rack => 
        rack.rack_id === rackId ? { ...rack, result, success: true } : rack
      ));
      
      // Update fleet summary safely
      setFleetResult(prev => ({
        fleet_size: prev?.fleet_size || 100,
        successful_racks: (prev?.successful_racks || 0) + 1,
        failed_racks: prev?.failed_racks || 0,
        total_expected_savings: (prev?.total_expected_savings || 0) + (result?.result?.expected_water_saving || result?.expected_water_saving || 0),
        avg_confidence: 0.75,
        timestamp: new Date().toISOString(),
        rack_results: rackResults,
      }));
    } catch (err) {
      setError(`Rack ${rackId} reasoning failed.`);
      
      // Update failed rack count
      setFleetResult(prev => ({
        ...prev,
        failed_racks: (prev?.failed_racks || 0) + 1
      }));
    } finally {
      if (setGlobalLoading) {
        setLoading(false);
      }
      setSelectedRack(null);
    }
  };

  const openDetailModal = (rack) => {
    // Ensure the modal gets a properly structured object with all the data
    const modalData = {
      ...rack,
      // Ensure result data is accessible at both top level and nested
      result: rack.result || {},
      recommendation: rack.result?.recommendation || rack.recommendation,
      rationale: rack.result?.rationale || rack.rationale,
      confidence: rack.result?.confidence || rack.confidence,
      expected_water_saving: rack.result?.expected_water_saving || rack.expected_water_saving,
      reasoning_logs: rack.reasoning_logs || rack.result?.reasoning_logs || []
    };
    setShowDetailModal(modalData);
  };

  const closeDetailModal = () => {
    setShowDetailModal(null);
  };

  // Run fleet reasoning for first 10 racks sequentially
  const runFirst10Racks = async () => {
    const first10Racks = rackResults.slice(0, 10);
    setLoading(true);
    setError(null);
    
    for (const rack of first10Racks) {
      if (!rack.success) {
        try {
          await runRackReasoning(rack.rack_id, false); // Don't set global loading state for individual racks
          // Small delay between racks to avoid overwhelming the system
          await new Promise(resolve => setTimeout(resolve, 1000));
        } catch (err) {
          // Continue with next rack even if one fails
        }
      }
    }
    
    setLoading(false);
  };

  // Load saved results from database on component mount
  useEffect(() => {
    const loadSavedResults = async () => {
      try {
        const savedData = await getSavedRackResults();
        
        if (savedData && savedData.rack_results && savedData.rack_results.length > 0) {
          // Update rack results with saved data
          setRackResults(prev => {
            const updatedRacks = prev.map(rack => {
              const savedRack = savedData.rack_results.find(sr => sr.rack_id === rack.rack_id);
              if (savedRack) {
                return {
                  ...rack,
                  result: savedRack.result,
                  success: savedRack.success,
                  reasoning_logs: savedRack.reasoning_logs,
                  cpu_factor: savedRack.cpu_factor || rack.cpu_factor,
                  gpu_factor: savedRack.gpu_factor || rack.gpu_factor,
                  ram_factor: savedRack.ram_factor || rack.ram_factor,
                  cooling_efficiency: savedRack.cooling_efficiency || rack.cooling_efficiency,
                  hardware_age: savedRack.hardware_age || rack.hardware_age
                };
              }
              return rack;
            });
            return updatedRacks;
          });

          // Update rack timings with saved data
          const savedTimings = {};
          savedData.rack_results.forEach(savedRack => {
            if (savedRack.reasoning_time_ms) {
              savedTimings[savedRack.rack_id] = savedRack.reasoning_time_ms;
            }
          });
          setRackTimings(savedTimings);

          // Update fleet summary with saved data
          if (savedData.summary) {
            setFleetResult({
              fleet_size: savedData.summary.total_racks || 100,
              successful_racks: savedData.summary.successful_racks || 0,
              failed_racks: savedData.summary.failed_racks || 0,
              total_expected_savings: savedData.summary.total_water_savings || 0,
              avg_confidence: savedData.summary.avg_confidence || 0,
              timestamp: new Date().toISOString(),
              rack_results: savedData.rack_results || [],
            });
          }
        }
      } catch (error) {
        // Silently handle loading errors
      }
    };

    loadSavedResults();
  }, []);

  // Filter and sort rack results
  const filteredAndSortedRacks = rackResults
    .filter(rack => {
      if (searchQuery && !rack.rack_id.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      if (filter === "pending") return !rack.success;
      if (filter === "completed") return rack.success;
      if (filter === "failed") return false; // Currently no failed state tracking
      return true;
    })
    .sort((a, b) => {
      let comparison = 0;
      if (sortBy === "rack_id") {
        comparison = a.rack_id.localeCompare(b.rack_id);
      } else if (sortBy === "confidence") {
        const aConf = a.result?.confidence || 0;
        const bConf = b.result?.confidence || 0;
        comparison = aConf - bConf;
      } else if (sortBy === "water_savings") {
        const aSavings = a.result?.expected_water_saving || 0;
        const bSavings = b.result?.expected_water_saving || 0;
        comparison = aSavings - bSavings;
      }
      return sortOrder === "asc" ? comparison : -comparison;
    });

  if (rackResults.every(r => !r.success)) {
    return (
      <div className="min-h-screen bg-abyss pt-28 p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-heading font-bold text-frost flex items-center gap-3">
                <Server className="text-flow" size={36} />
                Fleet Management - 100 Racks
              </h1>
              <p className="text-mist mt-2">
                Rack 1: Real Laptop Telemetry | Racks 2-100: Digital Twins
              </p>
            </div>
            <button
              onClick={() => window.location.href = "/dashboard"}
              className="px-4 py-2 bg-hall-2 border border-rack rounded-lg text-frost hover:border-coolant transition-colors"
            >
              Dashboard
            </button>
          </div>

          {/* Fleet Summary - Enhanced Stats Strip */}
          <div className="card-glass rounded-xl p-4 border border-rack mb-6">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {/* Progress Ring */}
              <div className="flex flex-col items-center">
                <div className="relative w-16 h-16">
                  <svg className="w-16 h-16 transform -rotate-90">
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="transparent"
                      className="text-hall-2"
                    />
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="transparent"
                      strokeDasharray={`${(rackResults.filter(r => r.success).length / 100) * 175.93} 175.93`}
                      className="text-flow"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-sm font-bold text-frost">{rackResults.filter(r => r.success).length}/100</span>
                  </div>
                </div>
                <span className="text-xs text-mist mt-1">Complete</span>
              </div>

              {/* Successful Racks */}
              <div className="flex flex-col items-center">
                <div className="text-2xl font-heading font-bold text-signal">
                  {fleetResult.successful_racks || rackResults.filter(r => r.success).length}
                </div>
                <span className="text-xs text-mist">Completed Racks</span>
              </div>

              {/* Failed Racks */}
              <div className="flex flex-col items-center">
                <div className="text-2xl font-heading font-bold text-alert">
                  {fleetResult.failed_racks || 0}
                </div>
                <span className="text-xs text-mist">Failed</span>
              </div>

              {/* Total Water Savings */}
              <div className="flex flex-col items-center">
                <div className="text-2xl font-heading font-bold text-coolant">
                  {rackResults.reduce((sum, r) => sum + (r.result?.expected_water_saving || 0), 0).toFixed(2)}
                </div>
                <span className="text-xs text-mist">Total L/hr</span>
              </div>

              {/* Confidence Range */}
              <div className="flex flex-col items-center">
                <div className="text-2xl font-heading font-bold text-flow">
                  {(() => {
                    const confidences = rackResults.filter(r => r.success).map(r => r.result?.confidence || 0);
                    if (confidences.length === 0) return "0-0%";
                    const min = Math.min(...confidences) * 100;
                    const max = Math.max(...confidences) * 100;
                    return `${min.toFixed(0)}-${max.toFixed(0)}%`;
                  })()}
                </div>
                <span className="text-xs text-mist">Conf Range</span>
              </div>

              {/* Timing Stats */}
              <div className="flex flex-col items-center">
                <div className="text-2xl font-heading font-bold text-fog">
                  {(() => {
                    const timings = Object.values(rackTimings);
                    if (timings.length === 0) return "N/A";
                    const avg = timings.reduce((sum, t) => sum + t, 0) / timings.length;
                    return `${(avg / 1000).toFixed(1)}s`;
                  })()}
                </div>
                <span className="text-xs text-mist">Avg Time</span>
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="card-glass rounded-xl p-4 border border-alert mb-6">
              <div className="text-sm text-alert">{error}</div>
            </div>
          )}

          {/* Rack Grid */}
          <div className="card-glass rounded-xl p-6 border border-rack">
            <h2 className="text-xl font-heading font-semibold text-frost mb-4">Per-Rack Results</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {filteredAndSortedRacks.map((rack, index) => (
                <div
                  key={rack.rack_id}
                  onClick={() => {
                    if (rack.success) {
                      openDetailModal(rack);
                    } else if (!loading) {
                      runRackReasoning(rack.rack_id, true);
                    }
                  }}
                  className={`rounded-xl p-4 border transition-all duration-300 cursor-pointer hover:scale-105 hover:shadow-lg hover:shadow-flow/20 animate-slide-in ${
                    rack.success
                      ? index === 0
                        ? "bg-gradient-to-br from-flow/10 to-flow/5 border-flow/30"
                        : "bg-gradient-to-br from-hall-3 to-hall-2 border-rack"
                      : "bg-gradient-to-br from-hall-2 to-hall border-rack"
                  } ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-mono text-frost font-semibold">{rack.rack_id}</span>
                    {index === 0 && (
                      <span className="text-[10px] bg-flow/20 text-flow px-2 py-0.5 rounded-full animate-pulse">Laptop</span>
                    )}
                    {rack.success ? (
                      <CheckCircle size={16} className="text-signal" />
                    ) : (
                      <Clock size={16} className="text-mist" />
                    )}
                  </div>
                  
                  {/* Rack Profile Values */}
                  <div className="space-y-2 mb-3">
                    <div className="flex justify-between text-xs items-center">
                      <span className="text-mist flex items-center gap-1"><Cpu size={12} /> CPU:</span>
                      <span className="text-fog font-mono">{rack.cpu_factor ? rack.cpu_factor.toFixed(2) : (rack.cpu_factor || 1.00).toFixed(2)}x</span>
                    </div>
                    <div className="flex justify-between text-xs items-center">
                      <span className="text-mist flex items-center gap-1"><HardDrive size={12} /> Cool:</span>
                      <span className="text-fog font-mono">{rack.cooling_efficiency ? rack.cooling_efficiency.toFixed(2) : (rack.cooling_efficiency || 1.00).toFixed(2)}x</span>
                    </div>
                  </div>
                  
                  {rack.success && rack.result ? (
                    <div className="space-y-2 border-t border-rack pt-3">
                      <div className="flex justify-between text-xs items-center">
                        <span className="text-mist">Conf:</span>
                        <span className="text-fog font-mono">{rack.result.confidence ? (rack.result.confidence * 100).toFixed(1) : "0.0"}%</span>
                      </div>
                      <div className="flex justify-between text-xs items-center">
                        <span className="text-mist">Saving:</span>
                        <span className="text-coolant font-mono font-semibold">{rack.result.expected_water_saving ? rack.result.expected_water_saving.toFixed(3) : "0.000"}L</span>
                      </div>
                      
                      {/* View Details Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openDetailModal(rack);
                        }}
                        className="w-full text-xs text-coolant flex items-center justify-center gap-1 hover:text-flow transition-colors bg-hall-2 rounded py-2"
                      >
                        <TrendingUp size={12} /> View Details
                      </button>
                    </div>
                  ) : (
                    <div className="text-xs text-mist border-t border-rack pt-3">
                      {selectedRack === rack.rack_id ? (
                        <div className="flex items-center gap-2 text-flow">
                          <RefreshCw size={12} className="animate-spin" />
                          Running...
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-coolant hover:text-flow transition-colors">
                          <Zap size={12} />
                          Click to run
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-abyss pt-28 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-heading font-bold text-frost flex items-center gap-3">
              <Server className="text-flow" size={36} />
              Fleet Management - 100 Racks
            </h1>
            <p className="text-mist mt-2">
              Run agent reasoning across 100 data center racks. Rack 1 uses real laptop telemetry, others use digital twins.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={runFirst10Racks}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-flow/20 border border-flow/50 rounded-lg text-frost hover:bg-flow/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  Running First 10...
                </>
              ) : (
                <>
                  <Zap size={16} />
                  Run First 10 Racks
                </>
              )}
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        {loading && (
          <div className="card-glass rounded-xl p-4 border border-rack mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-mist">Processing Rack: {selectedRack}</span>
            </div>
            <div className="w-full bg-hall-2 rounded-full h-2">
              <div 
                className="bg-flow h-2 rounded-full transition-all duration-300"
                style={{ width: "100%" }}
              />
            </div>
          </div>
        )}

        {/* Fleet Summary - Enhanced Stats Strip */}
        <div className="card-glass rounded-xl p-4 border border-rack mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {/* Progress Ring */}
            <div className="flex flex-col items-center">
              <div className="relative w-16 h-16">
                <svg className="w-16 h-16 transform -rotate-90">
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="transparent"
                    className="text-hall-2"
                  />
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="transparent"
                    strokeDasharray={`${(rackResults.filter(r => r.success).length / 100) * 175.93} 175.93`}
                    className="text-flow"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-sm font-bold text-frost">{rackResults.filter(r => r.success).length}/100</span>
                </div>
              </div>
              <span className="text-xs text-mist mt-1">Complete</span>
            </div>

            {/* Successful Racks */}
            <div className="flex flex-col items-center">
              <div className="text-2xl font-heading font-bold text-signal">
                {fleetResult.successful_racks || rackResults.filter(r => r.success).length}
              </div>
              <span className="text-xs text-mist">Completed Racks</span>
            </div>

            {/* Failed Racks */}
            <div className="flex flex-col items-center">
              <div className="text-2xl font-heading font-bold text-alert">
                {fleetResult.failed_racks || 0}
              </div>
              <span className="text-xs text-mist">Failed</span>
            </div>

            {/* Total Water Savings */}
            <div className="flex flex-col items-center">
              <div className="text-2xl font-heading font-bold text-coolant">
                {rackResults.reduce((sum, r) => sum + (r.result?.expected_water_saving || 0), 0).toFixed(2)}
              </div>
              <span className="text-xs text-mist">Total L/hr</span>
            </div>

            {/* Confidence Range */}
            <div className="flex flex-col items-center">
              <div className="text-2xl font-heading font-bold text-flow">
                {(() => {
                  const confidences = rackResults.filter(r => r.success).map(r => r.result?.confidence || 0);
                  if (confidences.length === 0) return "0-0%";
                  const min = Math.min(...confidences) * 100;
                  const max = Math.max(...confidences) * 100;
                  return `${min.toFixed(0)}-${max.toFixed(0)}%`;
                })()}
              </div>
              <span className="text-xs text-mist">Conf Range</span>
            </div>

            {/* Timing Stats */}
            <div className="flex flex-col items-center">
              <div className="text-2xl font-heading font-bold text-fog">
                {(() => {
                  const timings = Object.values(rackTimings);
                  if (timings.length === 0) return "N/A";
                  const avg = timings.reduce((sum, t) => sum + t, 0) / timings.length;
                  return `${(avg / 1000).toFixed(1)}s`;
                })()}
              </div>
              <span className="text-xs text-mist">Avg Time</span>
            </div>
          </div>
        </div>

        {/* Filtering and Sorting Controls */}
        <div className="card-glass rounded-xl p-4 border border-rack mb-6">
          <div className="flex flex-wrap items-center gap-4">
            {/* Search */}
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-mist" />
                <input
                  type="text"
                  placeholder="Search rack ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-hall-2 border border-rack rounded-lg text-frost text-sm focus:outline-none focus:border-coolant"
                />
              </div>
            </div>

            {/* Filter */}
            <div className="flex items-center gap-2">
              <Filter size={16} className="text-mist" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-hall-2 border border-rack rounded-lg text-frost text-sm px-3 py-2 focus:outline-none focus:border-coolant"
              >
                <option value="all">All Racks</option>
                <option value="pending">Pending Only</option>
                <option value="completed">Completed Only</option>
                <option value="failed">Failed Only</option>
              </select>
            </div>

            {/* Sort */}
            <div className="flex items-center gap-2">
              <SortAsc size={16} className="text-mist" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-hall-2 border border-rack rounded-lg text-frost text-sm px-3 py-2 focus:outline-none focus:border-coolant"
              >
                <option value="rack_id">Rack ID</option>
                <option value="confidence">Confidence</option>
                <option value="water_savings">Water Savings</option>
              </select>
              <button
                onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
                className="p-2 bg-hall-2 border border-rack rounded-lg text-frost hover:border-coolant transition-colors"
              >
                {sortOrder === "asc" ? <SortAsc size={16} /> : <SortDesc size={16} />}
              </button>
            </div>

            {/* Results Count */}
            <div className="text-sm text-mist">
              Showing {filteredAndSortedRacks.length} of {rackResults.length} racks
            </div>
          </div>
        </div>

        {/* Fleet-wide Visualization */}
        {/* Error Display */}
        {error && (
          <div className="card-glass rounded-xl p-4 border border-alert mb-6">
            <div className="text-sm text-alert">{error}</div>
          </div>
        )}

        {/* Rack Grid */}
        <div className="card-glass rounded-xl p-6 border border-rack">
          <h2 className="text-xl font-heading font-semibold text-frost mb-4">Per-Rack Results</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {filteredAndSortedRacks.map((rack, index) => (
              <div
                key={rack.rack_id}
                onClick={() => {
                  if (rack.success) {
                    openDetailModal(rack);
                  } else if (!loading) {
                    runRackReasoning(rack.rack_id, true);
                  }
                }}
                className={`rounded-xl p-4 border transition-all duration-300 cursor-pointer hover:scale-105 hover:shadow-lg hover:shadow-flow/20 ${
                  rack.success
                    ? index === 0
                      ? "bg-flow/10 border-flow/30"
                      : "bg-hall-3 border-rack"
                    : "bg-hall-2 border-rack"
                } ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono text-frost font-semibold">{rack.rack_id}</span>
                  {index === 0 && (
                    <span className="text-[10px] bg-flow/20 text-flow px-2 py-0.5 rounded-full animate-pulse">Laptop</span>
                  )}
                  {rack.success ? (
                    <CheckCircle size={16} className="text-signal" />
                  ) : (
                    <Clock size={16} className="text-mist" />
                  )}
                </div>
                
                {/* Rack Profile Values */}
                <div className="space-y-2 mb-3">
                  <div className="flex justify-between text-xs items-center">
                    <span className="text-mist flex items-center gap-1"><Cpu size={12} /> CPU:</span>
                    <span className="text-fog font-mono">{rack.cpu_factor ? rack.cpu_factor.toFixed(2) : (rack.cpu_factor || 1.00).toFixed(2)}x</span>
                  </div>
                  <div className="flex justify-between text-xs items-center">
                    <span className="text-mist flex items-center gap-1"><HardDrive size={12} /> Cool:</span>
                    <span className="text-fog font-mono">{rack.cooling_efficiency ? rack.cooling_efficiency.toFixed(2) : (rack.cooling_efficiency || 1.00).toFixed(2)}x</span>
                  </div>
                </div>
                
                {/* Compact Info Layer - Always Visible */}
                <div className="border-t border-rack pt-2 mb-2">
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-mist text-[10px]">GPU:</span>
                      <span className="text-fog font-mono text-[10px]">{rack.gpu_factor ? rack.gpu_factor.toFixed(2) : (rack.gpu_factor || 1.00).toFixed(2)}x</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-mist text-[10px]">RAM:</span>
                      <span className="text-fog font-mono text-[10px]">{rack.ram_factor ? rack.ram_factor.toFixed(2) : (rack.ram_factor || 1.00).toFixed(2)}x</span>
                    </div>
                    <div className="flex justify-between items-center col-span-2">
                      <span className="text-mist text-[10px]">Age:</span>
                      <span className="text-fog font-mono text-[10px]">{rack.hardware_age ? rack.hardware_age.toFixed(2) : (rack.hardware_age || 1.00).toFixed(2)}x</span>
                    </div>
                  </div>
                  
                  {/* Profile Sparkline */}
                  <div className="mt-2 flex items-end gap-1 h-4">
                    <div 
                      className="bg-coolant/60 rounded-sm flex-1 transition-all hover:bg-coolant" 
                      style={{ height: `${(rack.cpu_factor || 1.0) * 100}%` }}
                      title={`CPU: ${(rack.cpu_factor || 1.0).toFixed(2)}x`}
                    />
                    <div 
                      className="bg-flow/60 rounded-sm flex-1 transition-all hover:bg-flow" 
                      style={{ height: `${(rack.gpu_factor || 1.0) * 100}%` }}
                      title={`GPU: ${(rack.gpu_factor || 1.0).toFixed(2)}x`}
                    />
                    <div 
                      className="bg-signal/60 rounded-sm flex-1 transition-all hover:bg-signal" 
                      style={{ height: `${(rack.ram_factor || 1.0) * 100}%` }}
                      title={`RAM: ${(rack.ram_factor || 1.0).toFixed(2)}x`}
                    />
                    <div 
                      className="bg-coolant-2/60 rounded-sm flex-1 transition-all hover:bg-coolant-2" 
                      style={{ height: `${(rack.cooling_efficiency || 1.0) * 100}%` }}
                      title={`Cooling: ${(rack.cooling_efficiency || 1.0).toFixed(2)}x`}
                    />
                    <div 
                      className="bg-amber/60 rounded-sm flex-1 transition-all hover:bg-amber" 
                      style={{ height: `${(rack.hardware_age || 1.0) * 100}%` }}
                      title={`Age: ${(rack.hardware_age || 1.0).toFixed(2)}x`}
                    />
                  </div>
                </div>
                
                {rack.success && rack.result ? (
                  <div className="space-y-2 border-t border-rack pt-3">
                    {/* Confidence Gauge */}
                    <div className="flex items-center justify-between">
                      <span className="text-mist">Conf:</span>
                      <div className="flex items-center gap-2">
                        <div className="relative w-16 h-8">
                          <svg className="w-16 h-8" viewBox="0 0 64 32">
                            <path
                              d="M 4 32 A 28 28 0 0 1 60 32"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="4"
                              className="text-hall-2"
                            />
                            <path
                              d="M 4 32 A 28 28 0 0 1 60 32"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="4"
                              strokeDasharray={`${(rack.result.confidence || 0) * 87.96} 87.96`}
                              className="text-flow"
                            />
                          </svg>
                          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 text-xs font-bold text-frost">
                            {(rack.result.confidence ? (rack.result.confidence * 100).toFixed(0) : "0")}%
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex justify-between text-xs items-center">
                      <span className="text-mist">Saving:</span>
                      <span className="text-coolant font-mono font-semibold">{rack.result.expected_water_saving ? rack.result.expected_water_saving.toFixed(3) : "0.000"}L</span>
                    </div>
                    
                    {/* View Details Button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openDetailModal(rack);
                      }}
                      className="w-full text-xs text-coolant flex items-center justify-center gap-1 hover:text-flow transition-colors bg-hall-2 rounded py-2"
                    >
                      <TrendingUp size={12} /> View Details
                    </button>
                  </div>
                ) : (
                  <div className="text-xs text-mist border-t border-rack pt-3">
                    {selectedRack === rack.rack_id ? (
                      <div className="flex items-center gap-2 text-flow">
                        <RefreshCw size={12} className="animate-spin" />
                        Running...
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-coolant hover:text-flow transition-colors">
                        <Zap size={12} />
                        Click to run
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Detail Modal Overlay */}
      {showDetailModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="card-glass rounded-xl border border-rack max-w-2xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-rack">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-flow/20 flex items-center justify-center">
                  <BrainCircuit size={20} className="text-flow" />
                </div>
                <div>
                  <h3 className="text-lg font-heading font-semibold text-frost">{showDetailModal.rack_id}</h3>
                  <p className="text-xs text-mist">{showDetailModal.is_laptop ? 'Real Laptop Telemetry' : 'Digital Twin'}</p>
                </div>
              </div>
              <button
                onClick={closeDetailModal}
                className="p-2 hover:bg-hall-2 rounded-lg transition-colors text-frost"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-140px)]">
              <div className="space-y-4">
                {/* Quick Stats */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-hall-2 rounded-lg p-3 text-center">
                    <div className="text-xs text-mist mb-1">Confidence</div>
                    <div className="text-xl font-bold text-flow">
                      {showDetailModal.result?.confidence ? (showDetailModal.result.confidence * 100).toFixed(1) : 
                       showDetailModal.confidence ? (showDetailModal.confidence * 100).toFixed(1) : "0.0"}%
                    </div>
                  </div>
                  <div className="bg-hall-2 rounded-lg p-3 text-center">
                    <div className="text-xs text-mist mb-1">Water Saving</div>
                    <div className="text-xl font-bold text-coolant">
                      {showDetailModal.result?.expected_water_saving ? showDetailModal.result.expected_water_saving.toFixed(3) :
                       showDetailModal.expected_water_saving ? showDetailModal.expected_water_saving.toFixed(3) : "0.000"}L
                    </div>
                  </div>
                  <div className="bg-hall-2 rounded-lg p-3 text-center">
                    <div className="text-xs text-mist mb-1">Status</div>
                    <div className="text-xl font-bold text-signal">
                      {showDetailModal.success ? 'Success' : 'Pending'}
                    </div>
                  </div>
                </div>

                {/* Agent Pipeline Timeline */}
                {(showDetailModal.reasoning_logs && showDetailModal.reasoning_logs.length > 0) ||
                 (showDetailModal.result?.reasoning_logs && showDetailModal.result.reasoning_logs.length > 0) && (
                  <div>
                    <div className="text-sm font-semibold text-frost mb-3 flex items-center gap-2">
                      <BrainCircuit size={16} className="text-flow" />
                      Agent Pipeline
                    </div>
                    <div className="flex items-center justify-between mb-3">
                      {(showDetailModal.reasoning_logs || showDetailModal.result?.reasoning_logs || []).map((log, idx) => (
                        <div key={idx} className="flex flex-col items-center flex-1">
                          <div className="w-8 h-8 rounded-full bg-flow flex items-center justify-center text-sm font-bold text-frost mb-1">
                            {idx + 1}
                          </div>
                          <div className="text-[10px] text-fog text-center leading-tight">
                            {log.agent.replace('Agent', '')}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="h-1 bg-hall-2 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-coolant via-flow to-signal"
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div className="mt-3 space-y-2">
                      {(showDetailModal.reasoning_logs || showDetailModal.result?.reasoning_logs || []).map((log, idx) => (
                        <div key={idx} className="text-xs border-l-2 border-coolant pl-3 py-2 bg-hall-2 rounded">
                          <div className="text-flow font-medium mb-1">{log.agent}</div>
                          <div className="text-fog">{log.message}</div>
                          <div className="text-mist text-[10px] mt-1">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommendation */}
                <div>
                  <div className="text-sm font-semibold text-frost mb-2">Recommendation</div>
                  <div className="text-sm text-fog leading-relaxed bg-hall-2 rounded-lg p-3">
                    {showDetailModal.result?.recommendation || 
                     showDetailModal.recommendation || 
                     "No recommendation available"}
                  </div>
                </div>

                {/* Rationale */}
                {(showDetailModal.result?.rationale || showDetailModal.rationale) && (
                  <div>
                    <div className="text-sm font-semibold text-frost mb-2">Rationale</div>
                    <div className="text-sm text-fog leading-relaxed bg-hall-2 rounded-lg p-3">
                      {showDetailModal.result?.rationale || showDetailModal.rationale}
                    </div>
                  </div>
                )}

                {/* Full API Response */}
                <div>
                  <div className="text-sm font-semibold text-frost mb-2 flex items-center gap-2">
                    <TrendingUp size={16} className="text-coolant" />
                    Full API Response
                  </div>
                  <div className="bg-hall-2 rounded-lg p-3">
                    <JsonTreeView data={showDetailModal.result || showDetailModal} />
                  </div>
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-hall-2 rounded-lg p-3">
                    <div className="text-xs text-mist mb-1">Device ID</div>
                    <div className="text-sm text-fog font-mono">{showDetailModal.device_id}</div>
                  </div>
                  <div className="bg-hall-2 rounded-lg p-3">
                    <div className="text-xs text-mist mb-1">Laptop</div>
                    <div className="text-sm text-fog">{showDetailModal.is_laptop ? "Yes" : "No"}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-rack bg-hall-2">
              <button
                onClick={closeDetailModal}
                className="w-full py-2 bg-hall-3 border border-rack rounded-lg text-frost hover:border-coolant transition-colors flex items-center justify-center gap-2"
              >
                <X size={16} /> Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
