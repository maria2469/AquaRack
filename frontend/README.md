# AquaMind AI — Frontend

A React + Tailwind CSS frontend for **AquaMind AI**, the digital-twin platform
described in the Phase 1 / Phase 2 Software Design Documents. Includes a
marketing site (landing, problem, solution, about) and a live operations
dashboard wired to the Phase 1 FastAPI backend's `/api/v1/*` endpoints.

## Stack

- React 18 + Vite
- Tailwind CSS v4 (via `@tailwindcss/vite`, no separate config file needed)
- React Router
- Three.js + `@react-three/fiber` for the hero 3D scene (lazy-loaded)
- Recharts for the telemetry chart
- Framer Motion for scroll/entry animation
- Axios for API calls
- lucide-react for icons

## Pages

| Route         | Purpose                                                            |
|---------------|---------------------------------------------------------------------|
| `/`           | Landing page — hero, pipeline overview, highlights, CTA            |
| `/problem`    | The data-centre water/cooling visibility problem                   |
| `/solution`   | How the 5-stage reasoning pipeline solves it (maps to SDD FR IDs)  |
| `/dashboard`  | **Live** dashboard — telemetry, water model, AI recommendation, memory search, report export |
| `/about`      | Architecture, tech stack, Phase 1 / Phase 2 roadmap                |

## Connecting to the backend

The dashboard calls these Phase 1 endpoints exactly as specified in the SDD (Section 10):

```
GET  /api/v1/dashboard/summary
GET  /api/v1/telemetry/latest
POST /api/v1/telemetry
POST /api/v1/simulate
GET  /api/v1/watermodel/latest
POST /api/v1/recommend
GET  /api/v1/recommend/latest
GET  /api/v1/memory/search?q=&k=
GET  /api/v1/reports/daily?format=csv|pdf
```

### Local development

By default `vite.config.js` proxies `/api` to `http://127.0.0.1:8000` — just
run your FastAPI backend (`uvicorn app.main:app --reload`) and the frontend
dev server together:

```bash
npm install
npm run dev
```

If the backend isn't running, the dashboard automatically falls back to a
synthetic demo stream (see `src/hooks/useLiveTelemetry.js`) so the UI is
still fully explorable.

### Production

Copy `.env.example` to `.env` and set:

```
VITE_API_BASE_URL=https://your-deployed-api.example.com
VITE_API_TOKEN=your-optional-bearer-token   # only if API_TOKEN is set server-side
```

Then:

```bash
npm run build
npm run preview   # serves the production build locally
```

The build output lands in `dist/` — deploy it to any static host (Vercel,
Netlify, S3 + CloudFront, nginx, etc.) alongside/behind your FastAPI backend.

## Design

- **Palette**: near-black data-hall base (`#04070c`/`#070d16`) with a
  coolant-blue (`#2b7fff`) and water-cyan (`#22d3ee`) accent pair, plus a
  restrained signal-green for efficiency/positive states.
- **Type**: Space Grotesk (display), Inter (body), JetBrains Mono (metrics/data).
- **Signature element**: the hero's 3D scene — a small rack cluster with a
  pulsing wireframe "coolant core" and rising particle stream, meant to read
  simultaneously as heat, water flow, and telemetry.

All design tokens live in `src/index.css` under the `@theme` block (Tailwind v4).

## Project structure

```
src/
  components/
    three/HeroScene.jsx    # signature 3D hero (lazy-loaded)
    ui/AmbientVeil.jsx      # lightweight non-WebGL section backdrop
    ui/StatCard.jsx
    Navbar.jsx
    Footer.jsx
  hooks/
    useLiveTelemetry.js     # polls dashboard summary, mock fallback
  lib/
    api.js                  # typed wrapper over every backend endpoint
  pages/
    Home.jsx  Problem.jsx  Solution.jsx  Dashboard.jsx  About.jsx
  App.jsx
  main.jsx
  index.css
```
