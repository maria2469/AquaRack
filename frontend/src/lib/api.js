import axios from "axios";

/**
 * AquaMind AI API client.
 *
 * Talks to the Phase 1 FastAPI monolith (SDD Section 10 — /api/v1/*)
 * Same shared schemas/data contracts carry into Phase 2's distributed
 * services (SDD Phase 2, Section on gateway routing), so this client
 * does not need to change when the backend topology changes — only
 * VITE_API_BASE_URL does.
 *
 * Dev: vite.config.js proxies /api -> http://127.0.0.1:8000
 * Prod: set VITE_API_BASE_URL to the deployed API origin (see .env.example)
 *
 * Two axios instances:
 *   api        — 10 s timeout for fast polling endpoints (telemetry, dashboard, etc.)
 *   reasonApi  — 60 s timeout for /api/reason which runs the full multi-agent
 *                pipeline (MCP retrieval + Bedrock + fallback). The pipeline
 *                completes in ~6-15 s even when Bedrock falls back to rules.
 */
const baseURL = import.meta.env.VITE_API_BASE_URL || "";

export const api = axios.create({
  baseURL,
  timeout: 10000,
});

// Dedicated instance for slow agentic endpoints — avoids the 10 s global cap
// triggering on the multi-agent reasoning pipeline (SDD FR-1.11 fallback adds
// latency even when Bedrock is unreachable).
export const reasonApi = axios.create({
  baseURL,
  timeout: 60000,
});

// Optional local bearer token support (SDD Section 17.1 — Phase 1 auth)
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

/** POST /api/v1/simulate ({ telemetry_id? }) -> { utilisation, thermal_load_kw, power_draw_kw, water_model } */
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

/**
 * POST /api/reason — runs the full multi-agent pipeline.
 * Uses reasonApi (60 s) because the pipeline involves:
 *   MCP memory retrieval → Bedrock Converse → rules fallback → DB writes
 * which can take 6–15 s even on a warm path.
 */
export const postReason = (telemetry_id) =>
  reasonApi.post("/api/reason", { telemetry_id }).then((r) => r.data);

export const postMemorySearch = (query, k = 5, memory_type = null) =>
  api.post("/api/memory/search", { query, k, memory_type }).then((r) => r.data);

export const getIncidents = (severity = null, limit = 20) =>
  api.get("/api/incidents", { params: { severity, limit } }).then((r) => r.data);

export const getRecommendations = (limit = 20) =>
  api.get("/api/recommendations", { params: { limit } }).then((r) => r.data);

export default api;

