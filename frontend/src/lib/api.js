import axios from "axios";

/**
 * AquaMind AI API client.
 *
 * Talks to the FastAPI monolith (SDD Section 10 — /api/v1/*).
 * Dev: vite.config.js proxies /api -> http://127.0.0.1:8000
 * Prod: set VITE_API_BASE_URL to the deployed API origin
 */
const baseURL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

export const api = axios.create({
  baseURL,
  timeout: 30000, // Increased timeout to 30 seconds to avoid timeouts on slow requests
});

// Dedicated instance for slow agentic endpoints (multi-agent pipeline via Ollama/Groq)
export const reasonApi = axios.create({
  baseURL,
  timeout: 300000, // 5 minutes timeout for Ollama reasoning
});

// Optional local bearer token support
const token = import.meta.env.VITE_API_TOKEN;
if (token) {
  api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  reasonApi.defaults.headers.common["Authorization"] = `Bearer ${token}`;
}

// Device ID for multi-device support - matching backend generation
const DEVICE_ID_KEY = "rackpulse_device_id";
const getDeviceId = () => {
  // Clear old device ID to force consistency
  const oldDeviceId = localStorage.getItem(DEVICE_ID_KEY);
  if (oldDeviceId && oldDeviceId !== "rack-01-primary") {
    localStorage.removeItem(DEVICE_ID_KEY);
  }
  
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);
  if (!deviceId) {
    // Use a consistent device ID for development/testing
    // In production, this should match the backend's device ID generation
    deviceId = "rack-01-primary"; // Consistent with backend default
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
};

// Add device ID to all requests
const deviceId = getDeviceId();
api.defaults.headers.common["X-Device-ID"] = deviceId;
reasonApi.defaults.headers.common["X-Device-ID"] = deviceId;

// Override baseURL for development or production
const devBaseURL = "http://127.0.0.1:8000";
const prodBaseURL = import.meta.env.VITE_API_BASE_URL || devBaseURL;
api.defaults.baseURL = prodBaseURL;
reasonApi.defaults.baseURL = prodBaseURL;

/** GET /api/v1/dashboard/summary -> DashboardSummary */
export const getDashboardSummary = () =>
  api.get("/api/v1/dashboard/summary").then((r) => r.data);

/** GET /api/v1/telemetry/latest -> TelemetryReadingOut */
export const getLatestTelemetry = () =>
  api.get("/api/v1/telemetry/latest").then((r) => r.data);

/** POST /api/v1/telemetry (TelemetryReadingIn) -> { telemetry_id } */
export const postTelemetry = (reading) =>
  api.post("/api/v1/telemetry", reading).then((r) => r.data);

/** POST /api/v1/simulate ({ telemetry_id? }) -> { utilisation, thermal_load_kw, ... } */
export const postSimulate = (telemetry_id) =>
  api.post("/api/v1/simulate", { telemetry_id }).then((r) => r.data);

/** GET /api/v1/watermodel/latest -> WaterModelOut */
export const getLatestWaterModel = () =>
  api.get("/api/v1/watermodel/latest").then((r) => r.data);

/** POST /api/v1/recommend ({ telemetry_id? }) -> RecommendationOut */
export const postRecommend = (telemetry_id) =>
  api.post("/api/v1/recommend", { telemetry_id }).then((r) => r.data);

/** GET /api/v1/recommend/latest -> RecommendationOut */
export const getLatestRecommendation = () =>
  api.get("/api/v1/recommend/latest").then((r) => r.data);

/** GET /api/v1/memory/search?q=&k= -> MemoryOut[] */
export const searchMemory = (q, k = 5) =>
  api.get("/api/v1/memory/search", { params: { q, k } }).then((r) => r.data);

/** POST /api/memory/search - Search memory with semantic search */
export const postMemorySearch = (query, k = 5) =>
  api.post("/api/memory/search", { query, k }).then((r) => r.data);

/** GET /api/memory/history?limit= -> Memory history */
export const getMemoryHistory = (limit = 50) =>
  api.get("/api/memory/history", { params: { limit } }).then((r) => r.data);

/** GET /api/memory/comprehensive -> Comprehensive memory and episode stats */
export const getComprehensiveStats = () =>
  api.get("/api/memory/comprehensive").then((r) => r.data);

/** GET /api/v1/reports/daily?format=csv|pdf -> Blob (file stream) */
export const downloadDailyReport = (format = "csv") =>
  api
    .get("/api/v1/reports/daily", { params: { format }, responseType: "blob" })
    .then((r) => r.data);

/** Enterprise APIs */
export const getEnterpriseDashboard = () =>
  api.get("/api/dashboard").then((r) => r.data);

/** POST /api/reason — runs the full multi-agent pipeline via Ollama/Groq with fallback to /api/v1/recommend. */
export const postReason = (telemetry_id, use_memory = true) =>
  reasonApi
    .post("/api/reason", { telemetry_id, use_memory })
    .catch((err) => {
      if (err.response && err.response.status === 404) {
        return reasonApi.post("/api/v1/recommend", { telemetry_id });
      }
      throw err;
    })
    .then((r) => r.data);

/** POST /api/compare — side-by-side memory vs no-memory benchmark (single blocking call) */
export const postCompare = (telemetry_id) =>
  reasonApi.post("/api/compare", { telemetry_id }).then((r) => r.data);

/** POST /api/benchmark - Run memory vs no-memory benchmark comparison */
export const runCompareBenchmark = (telemetry_id) =>
  reasonApi.post("/api/benchmark", { telemetry_id }).then((r) => r.data);

function formatCompareSide(reasonRes, useMemory) {
  return {
    run_id: reasonRes.run_id,
    use_memory: useMemory,
    agent: reasonRes.agent_name || (useMemory ? "langgraph_multi_agent" : "baseline_no_memory"),
    recommendation: reasonRes.recommendation,
    rationale: reasonRes.rationale,
    explanation: reasonRes.explanation,
    confidence: reasonRes.confidence,
    confidence_pct: reasonRes.confidence_pct ?? Math.round((reasonRes.confidence ?? 0) * 100),
    expected_water_saving: reasonRes.expected_water_saving,
    cited_episodes: useMemory ? (reasonRes.cited_episodes_count ?? 0) : 0,
    cited_memory_ids: useMemory ? (reasonRes.historical_evidence?.map((h) => h.memory_id) ?? []) : [],
    matched_memories_count: useMemory ? (reasonRes.matched_memories_count ?? 0) : 0,
    historical_evidence: useMemory ? (reasonRes.historical_evidence ?? []) : [],
  };
}

function buildFailureMemory(failedEpisodes) {
  const failedEp =
    failedEpisodes?.find((e) => e.incident_occurred) ?? failedEpisodes?.[0];
  if (!failedEp?.action_taken) return null;
  const dateStr = failedEp.created_at?.split("T")[0] ?? "a prior run";
  if (failedEp.incident_occurred) {
    return `Avoided strategy '${failedEp.action_taken}' which caused an incident on ${dateStr}.`;
  }
  const rewardStr = failedEp.reward != null ? failedEp.reward.toFixed(2) : "n/a";
  return `Avoided strategy '${failedEp.action_taken}' (reward ${rewardStr}) from ${dateStr}.`;
}

/** Map POST /api/v1/simulate response + optional live dashboard context to scenario card shape. */
export function buildScenarioFromSimulate(simulateRes, liveContext = {}) {
  if (!simulateRes) {
    return {
      telemetry_id: liveContext.telemetry_id,
      rack: liveContext.rack ?? "Primary Rack — Live Telemetry",
      utilisation: liveContext.utilisation ?? liveContext.gpu_pct ?? null,
      thermal_load_kw: liveContext.thermal_load_kw ?? null,
      ambient_temp: liveContext.ambient_temp ?? null,
      humidity: liveContext.humidity ?? null,
      cpu_pct: liveContext.cpu_pct ?? null,
      gpu_pct: liveContext.gpu_pct ?? null,
    };
  }

  const rackLabel =
    simulateRes.rack ??
    (simulateRes.device_id
      ? `${simulateRes.device_id} — Active Cluster`
      : simulateRes.rack_id
        ? `${simulateRes.rack_id} — Active Cluster`
        : liveContext.rack ?? "Primary Rack — Active Cluster");

  return {
    telemetry_id: simulateRes.telemetry_id ?? liveContext.telemetry_id,
    rack_id: simulateRes.rack_id,
    device_id: simulateRes.device_id,
    rack: rackLabel,
    utilisation: simulateRes.utilisation ?? liveContext.utilisation ?? liveContext.gpu_pct,
    thermal_load_kw: simulateRes.thermal_load_kw,
    ambient_temp:
      simulateRes.ambient_temp ??
      liveContext.ambient_temp,
    humidity: simulateRes.humidity ?? liveContext.humidity,
    cpu_pct: simulateRes.cpu_pct ?? liveContext.cpu_pct,
    gpu_pct: simulateRes.gpu_pct ?? liveContext.gpu_pct,
    pue: simulateRes.pue,
    wue_factor: simulateRes.wue_factor,
    water_l_per_hr: simulateRes.water_l_per_hr,
    cooling_load_kw: simulateRes.cooling_load_kw,
    power_draw_kw: simulateRes.power_draw_kw,
  };
}

/** GET /api/v1/episodes/replay?includeUnresolved=&limit= -> Episode[] */
export const getEpisodesReplay = ({ includeUnresolved = false, limit = 20 } = {}) => {
  const finalParams = { includeUnresolved, limit };
  if (includeUnresolved === false) {
    delete finalParams.includeUnresolved;
  }
  return api.get("/api/v1/episodes/replay", { params: finalParams }).then((r) => r.data);
};

/** POST /api/v1/fleet/reason - Run agent reasoning across all 100 racks */
export const runFleetReasoning = (useMemory = true) =>
  api.post("/api/v1/fleet/reason", null, {
    timeout: 120000 // 2 minutes timeout for fleet reasoning
  }).then((r) => r.data);

/** GET /api/v1/fleet/reason/stream - Run fleet reasoning with streaming responses */
export const streamFleetReasoning = (useMemory = true, tick = 0) =>
  fetch(
    `/api/v1/fleet/reason/stream?use_memory=${useMemory}&tick=${tick}`
  );

/** POST /api/v1/fleet/reason/rack/{rack_id} - Run reasoning for a specific rack */
export const runSingleRackReasoning = (rackId, useMemory = true) =>
  api.post(`/api/v1/fleet/reason/rack/${rackId}`, null, {
    timeout: 180000, // 3 minutes timeout for individual rack reasoning
  }).then((r) => r.data);

/** GET /api/v1/fleet/status - Get current status of all racks in the fleet */
export const getFleetStatus = () =>
  api.get("/api/v1/fleet/status").then((r) => r.data);

/** GET /api/v1/fleet/summary -> fleet-wide rack stats */
export const getFleetSummary = () =>
  api.get("/api/v1/fleet/summary", { timeout: 60000 }).then((r) => r.data);

/** GET /api/v1/fleet/saved-results -> Get all saved rack reasoning results */
export const getSavedRackResults = () =>
  api.get("/api/v1/fleet/saved-results", { timeout: 60000 }).then((r) => r.data);

/** GET /api/v1/agent/trace/recent -> ReasoningEvent[] (REST polling fallback) */
export const getRecentTraces = (run_id = null, limit = 200) =>
  api.get("/api/v1/agent/trace/recent", { params: { run_id, limit } }).then((r) => r.data);

export default api;