import { Suspense, lazy } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Gauge, Thermometer, Droplets, Database, BrainCircuit,
  CheckCircle2, ArrowRight, Layers, ShieldCheck,
} from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";

const WaterSaveScene = lazy(() => import("../components/three/WaterSaveScene"));

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.07 } }),
};

const stages = [
  {
    icon: Gauge,
    title: "1. Telemetry Collector",
    tag: "FR-1.1 – FR-1.3",
    body: "A lightweight local daemon polls CPU, GPU, RAM, disk, battery, and fan telemetry every 5 seconds, normalises it into a shared JSON schema, and buffers locally in SQLite if the API is unreachable — replaying on reconnect.",
  },
  {
    icon: Thermometer,
    title: "2. Digital Twin Engine",
    tag: "FR-1.4",
    body: "Maps single-device utilisation onto a configurable synthetic rack profile, producing a rack-equivalent utilisation and thermal load estimate — without needing real data-centre hardware.",
  },
  {
    icon: Droplets,
    title: "3. Water Thermodynamic Model",
    tag: "FR-1.5",
    body: "Converts thermal load into cooling demand (kW) and estimated water consumption (L/hr) using PUE, WUE, and a psychrometric evaporation approximation from ambient temperature and humidity.",
  },
  {
    icon: Database,
    title: "4. Memory Engine",
    tag: "FR-1.6",
    body: "Every significant event is summarised, embedded, and stored in CockroachDB with a retrievable vector index — the institutional memory the AI agent reasons over.",
  },
  {
    icon: BrainCircuit,
    title: "5. AI Decision Agent",
    tag: "FR-1.7",
    body: "Retrieves the top-K most similar past memories via cosine similarity search, reasons over current state plus retrieved context, and produces a natural-language recommendation with a confidence score and cited memory IDs.",
  },
];

const principles = [
  "Unified data contracts, standardized API shapes, and distributed database schemas engineered for seamless scale.",
  "Zero mandatory cloud dependency: SQLite fallback, mockable Bedrock calls, single-node CockroachDB free tier.",
  "Every recommendation is explainable — it stores exactly which memories it was grounded in.",
  "Model outputs are sanity-checked against published industry WUE benchmarks (0.5–2.0 L/kWh) as an automated test.",
];

const impactMetrics = [
  { val: "17.8%", label: "Avg Water Savings", sub: "Achieved by anticipatory pump & chiller modulation" },
  { val: "< 5s", label: "Closed-Loop Latency", sub: "From telemetry pulse to AI action recommendation" },
  { val: "100%", label: "Auditability", sub: "Every decision linked to cited memory IDs and telemetry context" },
];

export default function Solution() {
  return (
    <div className="relative bg-abyss">

      {/* ── HERO — fullscreen with 3D clean-water background ── */}
      <section className="relative h-screen overflow-hidden bg-black">

        {/* 3D scene */}
        <Suspense fallback={null}>
          <WaterSaveScene className="absolute inset-0 z-0" />
        </Suspense>

        {/* vignette overlays */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-black/20 to-black z-[1]" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/40 via-transparent to-black/20 z-[1]" />

        {/* hero content */}
        <div className="relative z-10 flex flex-col h-full justify-between px-6 pb-10 pt-28 sm:pb-12 sm:pt-32 md:px-12 md:pb-16 lg:px-16">

          {/* top: badge + headline */}
          <div className="max-w-3xl">
            <div
              className="inline-flex items-center gap-2 rounded-full border border-signal/40 bg-signal/10 px-4 py-1.5 text-xs font-mono text-signal mb-5 sm:mb-6"
              style={{ animation: "fadeSlideUp 0.8s ease 0.2s both" }}
            >
              <ShieldCheck size={12} />
              THE SOLUTION
            </div>

            <h1
              className="text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-medium leading-[1.1] tracking-tight text-white"
              style={{ animation: "fadeSlideUp 0.8s ease 0.4s both" }}
            >
              Preserving clean water,
              <br />
              one intelligent cooling
              <br />
              decision at a time.
            </h1>
          </div>

          {/* bottom: description + CTA */}
          <div>
            <p
              className="text-sm sm:text-base md:text-lg leading-relaxed text-white/60 max-w-sm sm:max-w-lg mb-5 sm:mb-6"
              style={{ animation: "fadeSlideUp 0.8s ease 0.7s both" }}
            >
              AquaRack connects telemetry, thermal physics, and RAG memory into a single real-time loop — forecasting water demand before compute peaks and eliminating wasted cooling.
            </p>
            <div
              className="flex flex-wrap gap-3"
              style={{ animation: "fadeSlideUp 0.8s ease 0.9s both" }}
            >
              <Link
                to="/dashboard"
                className="rounded-lg bg-white px-5 py-2.5 sm:px-6 sm:py-3 text-sm font-medium text-black hover:scale-105 transition-transform inline-flex items-center gap-2"
              >
                Launch Dashboard <ArrowRight size={16} />
              </Link>
              <Link
                to="/problem"
                className="rounded-lg border border-white/20 bg-white/5 backdrop-blur-sm px-5 py-2.5 sm:px-6 sm:py-3 text-sm font-medium text-white hover:bg-white/10 transition-colors inline-flex items-center gap-2"
              >
                Review The Problem <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── IMPACT METRICS BAND ── */}
      <section className="relative border-y border-rack/60 bg-hall-2 py-12 overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-6xl mx-auto px-5 md:px-8">
          <div className="grid md:grid-cols-3 gap-px bg-rack/40 rounded-2xl overflow-hidden">
            {impactMetrics.map((m, i) => (
              <motion.div
                key={m.label}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
                className="bg-hall-2 px-8 py-8"
              >
                <div className="font-mono text-4xl font-semibold text-flow mb-2">{m.val}</div>
                <div className="font-heading text-lg text-frost mb-1">{m.label}</div>
                <p className="text-sm text-mist leading-relaxed">{m.sub}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PIPELINE DETAIL ── */}
      <section className="py-20 md:py-28">
        <div className="max-w-5xl mx-auto px-5 md:px-8">
          <motion.div
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
            className="mb-12"
          >
            <p className="text-xs uppercase tracking-[0.18em] text-flow font-mono mb-3">// Architecture</p>
            <h2 className="font-heading text-3xl md:text-4xl text-frost leading-tight max-w-xl">
              5 connected stages. Under 5 seconds.
            </h2>
          </motion.div>

          <div className="space-y-4">
            {stages.map((s, i) => (
              <motion.div
                key={s.title}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-60px" }} custom={i}
                className="card-glass rounded-2xl p-6 md:p-7 flex flex-col md:flex-row gap-5 md:items-start group hover:border-flow/30 transition-colors"
              >
                <div className="shrink-0 h-12 w-12 rounded-xl bg-hall-3 border border-rack-2 flex items-center justify-center group-hover:border-flow/40 transition-colors">
                  <s.icon size={20} className="text-coolant-2" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 flex-wrap mb-1.5">
                    <h3 className="font-heading font-semibold text-frost text-lg">{s.title}</h3>
                    <span className="font-mono text-[11px] text-flow bg-flow/10 border border-flow/20 rounded px-2 py-0.5">
                      {s.tag}
                    </span>
                  </div>
                  <p className="text-sm text-mist leading-relaxed">{s.body}</p>
                </div>
                {i < stages.length - 1 && (
                  <ArrowRight size={16} className="hidden md:block text-rack-2 mt-3 self-center shrink-0" />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DESIGN PRINCIPLES ── */}
      <section className="relative border-t border-rack bg-hall py-20 overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-6xl mx-auto px-5 md:px-8 grid lg:grid-cols-2 gap-14 items-start">
          <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}>
            <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono flex items-center gap-2">
              <Layers size={13} /> Design principles
            </span>
            <h2 className="font-heading text-3xl font-semibold text-frost mt-3 leading-tight">
              Built to scale without a rewrite.
            </h2>
            <p className="text-mist mt-4 leading-relaxed">
              AquaRack deploys identical core modules — Digital Twin, Water Model, Memory Engine,
              AI Agent — across both edge and distributed cloud infrastructure. The schema and API
              contracts remain completely consistent at any scale.
            </p>
          </motion.div>

          <div className="space-y-3">
            {principles.map((p, i) => (
              <motion.div
                key={p}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
                className="flex items-start gap-3 card-glass rounded-xl p-4"
              >
                <CheckCircle2 size={17} className="text-signal shrink-0 mt-0.5" />
                <p className="text-sm text-fog leading-relaxed">{p}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
