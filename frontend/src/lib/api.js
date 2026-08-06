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
  timeout: 10000,
});

// Dedicated instance for slow agentic endpoints (multi-agent pipeline via Ollama/Groq)
export const reasonApi = axios.create({
  baseURL,
  timeout: 120000,
});

// Optional local bearer token support
const token = import.meta.env.VITE_API_TOKEN;
if (token) {
  api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  reasonApi.defaults.headers.common["Authorization"] = `Bearer ${token}`;
}

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

/** GET /api/v1/reports/daily?format=csv|pdf -> Blob (file stream) */
export const downloadDailyReport = (format = "csv") =>
  api
    .get("/api/v1/reports/daily", { params: { format }, responseType: "blob" })
    .then((r) => r.data);

/** Enterprise APIs */
export const getEnterpriseDashboard = () =>
  api.get("/api/dashboard").then((r) => r.data);

/** POST /api/reason — runs the full multi-agent pipeline via Ollama/Groq with fallback to /api/v1/recommend. */
export const postReason = (telemetry_id) =>
  reasonApi
    .post("/api/reason", { telemetry_id })
    .catch((err) => {
      if (err.response && err.response.status === 404) {
        return reasonApi.post("/api/v1/recommend", { telemetry_id });
      }
      throw err;
    })
    .then((r) => r.data);

export const postMemorySearch = (query, k = 5, memory_type = null) =>
  reasonApi.post("/api/memory/search", { query, k, memory_type }).then((r) => r.data);

export const getIncidents = (severity = null, limit = 20) =>
  api.get("/api/incidents", { params: { severity, limit } }).then((r) => r.data);

export const getRecommendations = (limit = 20) =>
  api.get("/api/recommendations", { params: { limit } }).then((r) => r.data);

// ─── New Memory Architecture APIs (Tasks 4-7) ───────────────────────

/** GET /api/v1/episodes/replay -> Episode[] — resolved episodes for experience replay */
export const getEpisodesReplay = (params = {}) =>
  api.get("/api/v1/episodes/replay", { params }).then((r) => r.data);

/** GET /api/v1/fleet/summary -> fleet-wide rack stats */
export const getFleetSummary = () =>
  api.get("/api/v1/fleet/summary").then((r) => r.data);

/** GET /api/v1/agent/trace/recent -> ReasoningEvent[] (REST polling fallback) */
export const getRecentTraces = (run_id = null, limit = 200) =>
  api.get("/api/v1/agent/trace/recent", { params: { run_id, limit } }).then((r) => r.data);

export default api;
