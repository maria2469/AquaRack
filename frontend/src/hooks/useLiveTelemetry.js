import { useEffect, useRef, useState, useCallback } from "react";
import { getDashboardSummary } from "../lib/api";

/**
 * Polls GET /api/v1/dashboard/summary on an interval (default 5s, matching
 * the Telemetry Collector's default polling interval in the SDD, FR-1.1).
 *
 * If the backend isn't reachable (e.g. viewing the frontend standalone),
 * falls back to a light synthetic stream so the dashboard is still
 * demoable — mirrors the SDD's own "mockable Bedrock / offline-safe"
 * design philosophy for Phase 1.
 */
export function useLiveTelemetry({ intervalMs = 5000 } = {}) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("connecting"); // connecting | live | mock | error
  const mockTick = useRef(0);
  const historyRef = useRef([]);

  const fetchOnce = useCallback(async () => {
    try {
      const summary = await getDashboardSummary();
      setData(summary);
      setStatus("live");
    } catch (err) {
      // Backend not reachable — synthesize a plausible-looking reading so
      // the UI remains fully explorable without a running FastAPI process.
      mockTick.current += 1;
      const t = mockTick.current;
      const cpu = 38 + 22 * Math.sin(t / 4) + Math.random() * 6;
      const util = Math.max(5, Math.min(98, cpu + Math.random() * 8));
      const thermal = +(util * 0.045).toFixed(2);
      const wue = +(1.1 + 0.4 * Math.sin(t / 6)).toFixed(2);
      const cooling = +(thermal * 1.4).toFixed(2);
      const water = +(wue * thermal * 3.2).toFixed(1);

      const reading = {
        telemetry_id: `mock-${t}`,
        device_id: "demo-laptop-01",
        timestamp: new Date().toISOString(),
        cpu_pct: +cpu.toFixed(1),
        gpu_pct: +(cpu * 0.6).toFixed(1),
        ram_pct: +(50 + 10 * Math.cos(t / 5)).toFixed(1),
        fan_rpm: Math.round(1800 + cpu * 20),
        battery_pct: Math.max(10, 100 - t * 0.4),
        source: "laptop",
      };

      historyRef.current = [...historyRef.current.slice(-49), reading];

      setData({
        latest_telemetry: reading,
        latest_water_model: {
          water_model_id: `mock-wm-${t}`,
          telemetry_id: reading.telemetry_id,
          wue_factor: wue,
          cooling_load_kw: cooling,
          water_l_per_hr: water,
          pue: 1.4,
          utilisation_pct: +util.toFixed(1),
          thermal_load_kw: thermal,
          power_draw_kw: +(thermal * 0.95).toFixed(2),
          computed_at: new Date().toISOString(),
        },
        latest_recommendation: {
          recommendation_id: `mock-rec-${t}`,
          telemetry_id: reading.telemetry_id,
          text:
            util > 80
              ? "Utilisation trending high — consider shifting non-urgent batch jobs to off-peak hours to reduce cooling demand."
              : "Thermal load is within nominal range. No cooling adjustment recommended at this time.",
          confidence: +(0.7 + Math.random() * 0.2).toFixed(2),
          agent_name: "rules_fallback",
          cited_memory_ids: [],
          rationale: "Simulated locally — connect the AquaMind backend for live Bedrock-grounded reasoning.",
          created_at: new Date().toISOString(),
        },
        telemetry_history: historyRef.current,
        open_incidents: util > 85 ? 1 : 0,
      });
      setStatus((s) => (s === "live" ? "error" : "mock"));
    }
  }, []);

  useEffect(() => {
    fetchOnce();
    const id = setInterval(fetchOnce, intervalMs);
    return () => clearInterval(id);
  }, [fetchOnce, intervalMs]);

  return { data, status, refresh: fetchOnce };
}
