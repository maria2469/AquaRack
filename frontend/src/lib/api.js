import axios from "axios";

/**
 * AquaMind AI API client.
 *
 * Talks to the Phase 1 FastAPI monolith (SDD Section 10 — /api/v1/*).
 * Same shared schemas/data contracts carry into Phase 2's distributed
 * services (SDD Phase 2, Section on gateway routing), so this client
 * does not need to change when the backend topology changes — only
 * VITE_API_BASE_URL does.
 *
 * Dev: vite.config.js proxies /api -> http://127.0.0.1:8000
 * Prod: set VITE_API_BASE_URL to the deployed API origin (see .env.example)
 */
const baseURL = import.meta.env.VITE_API_BASE_URL || "";

export const api = axios.create({
  baseURL,
  timeout: 10000,
});

// Optional local bearer token support (SDD Section 17.1 — Phase 1 auth)
const token = import.meta.env.VITE_API_TOKEN;
if (token) {
  api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
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

export default api;
