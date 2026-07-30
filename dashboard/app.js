/* AquaMind AI — Phase 1 dashboard client.
 * Talks only to the local FastAPI monolith (SDD Section 10.1 endpoints).
 * No build step, no external JS dependencies — served as a static file
 * directly by the FastAPI app (SDD Section 3.1).
 */
const POLL_MS = 5000;
let history = [];

const $ = (id) => document.getElementById(id);

async function apiGet(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

function setText(id, value) {
  $(id).textContent = value;
}

function renderTelemetry(t) {
  if (!t) return;
  setText("m-cpu", `${t.cpu_pct?.toFixed(1) ?? "–"}%`);
  setText("m-gpu", t.gpu_pct != null ? `${t.gpu_pct.toFixed(1)}%` : "n/a");
  setText("m-ram", `${t.ram_pct?.toFixed(1) ?? "–"}%`);
  setText("m-fan", t.fan_rpm != null ? `${t.fan_rpm} rpm` : "n/a");
  setText("m-batt", t.battery_pct != null ? `${t.battery_pct.toFixed(0)}%` : "n/a");
}

function renderWaterModel(w, openIncidents) {
  if (w) {
    setText("w-util", w.utilisation_pct != null ? `${w.utilisation_pct.toFixed(1)}%` : "–");
    setText("w-thermal", w.thermal_load_kw != null ? `${w.thermal_load_kw.toFixed(2)} kW` : "–");
    setText("w-cooling", `${w.cooling_load_kw.toFixed(2)} kW`);
    setText("w-wue", `${w.wue_factor.toFixed(2)} L/kWh`);
    setText("w-water", `${w.water_l_per_hr.toFixed(2)} L/hr`);
  }
  setText("w-incidents", openIncidents != null ? String(openIncidents) : "–");
}

function renderRecommendation(rec) {
  const box = $("rec-box");
  if (!rec) {
    box.innerHTML = '<p class="muted">No recommendation yet. Click "Get Recommendation".</p>';
    return;
  }
  box.innerHTML = `
    <p class="rec-text">${rec.text}</p>
    <div class="rec-meta">
      <span class="badge">${rec.agent_name}</span>
      <span class="badge">confidence: ${(rec.confidence * 100).toFixed(0)}%</span>
      <span class="badge">${new Date(rec.created_at).toLocaleTimeString()}</span>
    </div>
  `;
}

function renderMemoryResults(results) {
  const list = $("mem-results");
  list.innerHTML = "";
  if (!results || results.length === 0) {
    list.innerHTML = '<li class="muted">No matching memories yet.</li>';
    return;
  }
  for (const m of results) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="badge">${(m.similarity * 100).toFixed(0)}%</span> ${m.summary_text}`;
    list.appendChild(li);
  }
}

function drawChart(points) {
  const canvas = $("chart");
  const ctx = canvas.getContext("2d");
  const w = (canvas.width = canvas.clientWidth);
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (points.length < 2) return;

  const pad = 10;
  const max = 100;
  const step = (w - pad * 2) / (points.length - 1);

  const plotLine = (values, color) => {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    values.forEach((v, i) => {
      const x = pad + i * step;
      const y = h - pad - (Math.min(v, max) / max) * (h - pad * 2);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
  };

  plotLine(points.map((p) => p.cpu_pct ?? 0), "#0ea5e9");
  plotLine(points.map((p) => p.ram_pct ?? 0), "#22c55e");
}

async function refreshAll() {
  try {
    const summary = await apiGet("/api/v1/dashboard/summary");
    renderTelemetry(summary.latest_telemetry);
    renderWaterModel(summary.latest_water_model, summary.open_incidents);
    renderRecommendation(summary.latest_recommendation);
    history = summary.telemetry_history || [];
    drawChart(history);
    $("conn-status").textContent = "Connected";
    $("conn-status").classList.add("ok");
  } catch (e) {
    $("conn-status").textContent = "Disconnected";
    $("conn-status").classList.remove("ok");
    console.warn("Dashboard refresh failed:", e);
  }
}

async function getRecommendation() {
  try {
    const rec = await apiPost("/api/v1/recommend", {});
    renderRecommendation(rec);
  } catch (e) {
    console.error("Recommendation request failed:", e);
  }
}

async function searchMemory() {
  const q = $("mem-query").value.trim();
  if (!q) return;
  try {
    const results = await apiGet(`/api/v1/memory/search?q=${encodeURIComponent(q)}&k=5`);
    renderMemoryResults(results);
  } catch (e) {
    console.error("Memory search failed:", e);
  }
}

$("btn-recommend").addEventListener("click", getRecommendation);
$("btn-refresh").addEventListener("click", refreshAll);
$("btn-search").addEventListener("click", searchMemory);
$("mem-query").addEventListener("keydown", (e) => {
  if (e.key === "Enter") searchMemory();
});

refreshAll();
setInterval(refreshAll, POLL_MS);
