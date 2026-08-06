import { useEffect, useRef, useState, useCallback } from "react";
import { getEnterpriseDashboard } from "../lib/api";

/**
 * Polls GET /api/dashboard on an interval (default 5s).
 * This is the enterprise dashboard endpoint served by enterprise_api.py.
 *
 * Maps the backend response to a shape that includes `latest_telemetry`
 * so Dashboard.jsx can destructure it consistently, whether live or in
 * demo mode (backend unreachable).
 */
export function useLiveTelemetry({ intervalMs = 5000 } = {}) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("connecting"); // connecting | live | mock | error
  const mockTick = useRef(0);
  const historyRef = useRef([]);

  const fetchOnce = useCallback(async () => {
    try {
      const dash = await getEnterpriseDashboard();
      // Map enterprise dashboard shape -> { latest_telemetry, ... }
      // so Dashboard.jsx can use data?.latest_telemetry as before.
      setData({
        ...dash,
        latest_telemetry: {
          telemetry_id: "live",
          device_id: "rack-01-primary",
          timestamp: new Date().toISOString(),
          cpu_pct: dash.current_cpu,
          gpu_pct: dash.current_gpu,
          gpu_temp: 58.5,
          ram_pct: 52.0,
          weather_temp: dash.weather_temp,
          humidity: dash.humidity,
          predicted_water_usage: dash.predicted_water_usage,
          source: "live",
        },
      });
      setStatus("live");
    } catch (err) {
      // Backend not reachable — synthesize a plausible-looking reading
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
        current_gpu: reading.gpu_pct,
        current_cpu: reading.cpu_pct,
        weather_temp: 39,
        humidity: 62,
        predicted_water_usage: 1.45,
        water_saved_today_liters: 184.5,
        memory_confidence_pct: 93,
        historical_matches_count: 24,
        latest_recommendation: {
          id: `mock-rec-${t}`,
          text:
            util > 80
              ? "Utilisation trending high — consider shifting non-urgent batch jobs to off-peak hours to reduce cooling demand."
              : "Thermal load is within nominal range. No cooling adjustment recommended at this time.",
          expected_water_saving: 17.8,
          confidence: +(0.7 + Math.random() * 0.2).toFixed(2),
        },
        opendc_fleet: { rack_count: 100 },
        charts: {
          gpu_usage: [
            { timestamp: "19:00", gpu_usage: 65, cpu_usage: 40 },
            { timestamp: "19:05", gpu_usage: 78, cpu_usage: 45 },
            { timestamp: "19:10", gpu_usage: 91, cpu_usage: 52 },
            { timestamp: "19:15", gpu_usage: 84, cpu_usage: 48 },
            { timestamp: "19:20", gpu_usage: +util.toFixed(1), cpu_usage: +cpu.toFixed(1) },
          ],
          water_consumption: [
            { timestamp: "19:00", predicted_water: 1.6, saved_water: 0.3 },
            { timestamp: "19:05", predicted_water: 1.8, saved_water: 0.35 },
            { timestamp: "19:10", predicted_water: 2.1, saved_water: 0.42 },
            { timestamp: "19:15", predicted_water: 1.9, saved_water: 0.38 },
            { timestamp: "19:20", predicted_water: +water, saved_water: +(water * 0.18).toFixed(2) },
          ],
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

