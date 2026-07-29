import { Link } from "react-router-dom";
import { Suspense, lazy } from "react";
import { motion } from "framer-motion";
import {
  Droplets,
  Thermometer,
  BrainCircuit,
  Database,
  ArrowRight,
  Gauge,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";

const HeroScene = lazy(() => import("../components/three/HeroScene"));

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, delay: i * 0.08, ease: "easeOut" },
  }),
};

const pipeline = [
  { icon: Gauge, label: "Telemetry", desc: "CPU, GPU, RAM, fan & thermal readings, polled every 5s." },
  { icon: Thermometer, label: "Digital Twin", desc: "Maps utilisation onto a configurable rack-scale thermal model." },
  { icon: Droplets, label: "Water Model", desc: "Converts thermal load into cooling demand and litres-per-hour." },
  { icon: Database, label: "Memory Engine", desc: "Embeds and stores every event for retrieval-augmented reasoning." },
  { icon: BrainCircuit, label: "AI Decision Agent", desc: "Retrieves similar past incidents and recommends an action." },
];

const highlights = [
  {
    icon: Workflow,
    title: "Real telemetry, not simulation",
    body: "The system reasons over live compute readings as they happen — not historical averages or offline models — so every recommendation reflects what's actually running right now.",
  },
  {
    icon: ShieldCheck,
    title: "Explainable by design",
    body: "Every recommendation stores the exact memories it was grounded in, so any decision can be traced back and audited after the fact.",
  },
  {
    icon: Droplets,
    title: "Water is a first-class metric",
    body: "WUE and cooling load sit next to CPU and GPU utilisation on the same dashboard — not bolted on as an afterthought.",
  },
];

export default function Home() {
  return (
    <div className="relative">
      {/* ---------------- HERO ---------------- */}
      <section className="relative min-h-[92vh] flex items-center overflow-hidden bg-abyss">
        <div className="absolute inset-0 grid-veil opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-b from-abyss via-transparent to-abyss" />
        <Suspense fallback={null}>
          <HeroScene className="absolute inset-0 z-0" />
        </Suspense>
        <div className="absolute inset-0 bg-gradient-to-r from-abyss via-abyss/40 to-transparent" />

        <div className="relative z-10 max-w-7xl mx-auto px-5 md:px-8 pt-24 pb-16 w-full">
          <div className="max-w-2xl">
            <motion.span
              variants={fadeUp} initial="hidden" animate="show" custom={0}
              className="inline-flex items-center gap-2 rounded-full border border-rack-2 bg-hall-2/80 px-3.5 py-1.5 text-xs font-mono text-flow-2 mb-6"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-signal animate-pulse-slow" />
              LIVE · REAL-TIME TELEMETRY
            </motion.span>

            <motion.h1
              variants={fadeUp} initial="hidden" animate="show" custom={1}
              className="font-display text-4xl sm:text-5xl lg:text-6xl font-semibold leading-[1.08] text-frost"
            >
              Every watt of compute
              <br />
              <span className="text-gradient-coolant">costs a drop of water.</span>
            </motion.h1>

            <motion.p
              variants={fadeUp} initial="hidden" animate="show" custom={2}
              className="mt-6 text-lg text-mist leading-relaxed max-w-xl"
            >
              AquaMind AI is a digital-twin platform that watches your infrastructure
              think, feel the heat it gives off, and reasons — with memory — about
              the cooling and water cost of every decision, before you make it.
            </motion.p>

            <motion.div
              variants={fadeUp} initial="hidden" animate="show" custom={3}
              className="mt-9 flex flex-col sm:flex-row gap-3"
            >
              <Link
                to="/dashboard"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-coolant px-6 py-3.5 text-sm font-semibold text-abyss shadow-[0_0_30px_-6px_rgba(43,127,255,0.7)] hover:bg-coolant-2 transition-colors"
              >
                Open Live Dashboard <ArrowRight size={16} />
              </Link>
              <Link
                to="/solution"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-rack-2 bg-hall-2/60 px-6 py-3.5 text-sm font-semibold text-fog hover:border-coolant hover:text-frost transition-colors"
              >
                See how it works
              </Link>
            </motion.div>

            <motion.div
              variants={fadeUp} initial="hidden" animate="show" custom={4}
              className="mt-14 grid grid-cols-3 gap-6 max-w-md"
            >
              {[
                ["0.5–2.0", "L/kWh typical WUE range"],
                ["<5s", "ingest → recommendation"],
                ["$0", "mandatory cloud spend"],
              ].map(([n, l]) => (
                <div key={l}>
                  <div className="font-mono text-2xl font-semibold text-frost">{n}</div>
                  <div className="text-xs text-mist mt-1 leading-snug">{l}</div>
                </div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* ---------------- PIPELINE STRIP ---------------- */}
      <section className="relative bg-hall border-y border-rack py-16 overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-7xl mx-auto px-5 md:px-8">
          <motion.div
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-80px" }}
            className="mb-10"
          >
            <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono">The reasoning loop</span>
            <h2 className="font-display text-2xl md:text-3xl font-semibold text-frost mt-2">
              Telemetry in, an explainable decision out.
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {pipeline.map((p, i) => (
              <motion.div
                key={p.label}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
                className="card-glass rounded-xl p-5 relative"
              >
                <div className="h-9 w-9 rounded-lg bg-hall-3 border border-rack-2 flex items-center justify-center mb-4">
                  <p.icon size={17} className="text-coolant-2" />
                </div>
                <h3 className="font-semibold text-frost text-sm mb-1.5">{p.label}</h3>
                <p className="text-xs text-mist leading-relaxed">{p.desc}</p>
                {i < pipeline.length - 1 && (
                  <ArrowRight
                    size={14}
                    className="hidden lg:block absolute -right-2.5 top-1/2 -translate-y-1/2 text-rack-2 z-10"
                  />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- HIGHLIGHTS ---------------- */}
      <section className="relative bg-abyss py-24">
        <div className="max-w-7xl mx-auto px-5 md:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-16 items-start">
            <motion.div
              variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
              className="lg:sticky lg:top-28"
            >
              <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono">Why it's built this way</span>
              <h2 className="font-display text-3xl md:text-4xl font-semibold text-frost mt-3 leading-tight">
                Built on real data.
                <br />Reasoning in real time.
              </h2>
              <p className="text-mist mt-4 leading-relaxed">
                No historical batch reports, no offline simulations —
                every number on this dashboard reflects what's happening
                right now.
              </p>
            </motion.div>

            <div className="lg:col-span-2 grid sm:grid-cols-2 gap-5">
              {highlights.map((h, i) => (
                <motion.div
                  key={h.title}
                  variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
                  className={`card-glass rounded-2xl p-6 ${i === 2 ? "sm:col-span-2" : ""}`}
                >
                  <h.icon size={20} className="text-flow mb-4" />
                  <h3 className="font-display font-semibold text-frost mb-2">{h.title}</h3>
                  <p className="text-sm text-mist leading-relaxed">{h.body}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- CTA ---------------- */}
      <section className="relative bg-hall border-t border-rack py-20 overflow-hidden">
        <AmbientVeil dense />
        <div className="relative max-w-4xl mx-auto px-5 md:px-8 text-center">
          <motion.h2
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
            className="font-display text-3xl md:text-4xl font-semibold text-frost"
          >
            Watch the loop run, live.
          </motion.h2>
          <motion.p
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={1}
            className="text-mist mt-4 max-w-xl mx-auto"
          >
            The dashboard streams real telemetry from the connected device, the
            computed water model, and the AI agent's latest recommendation —
            or a synthetic demo stream if no backend is connected.
          </motion.p>
          <motion.div
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={2}
            className="mt-8"
          >
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 rounded-lg bg-coolant px-7 py-3.5 text-sm font-semibold text-abyss hover:bg-coolant-2 transition-colors shadow-[0_0_30px_-6px_rgba(43,127,255,0.7)]"
            >
              Open Live Dashboard <ArrowRight size={16} />
            </Link>
          </motion.div>
        </div>
      </section>
    </div>
  );
}