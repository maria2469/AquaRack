import { motion } from "framer-motion";
import {
  Gauge, Thermometer, Droplets, Database, BrainCircuit,
  CheckCircle2, ArrowRight, Layers,
} from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.07 } }),
};

const stages = [
  {
    icon: Gauge,
    title: "1. Live Telemetry Collection",
    tag: "Every 5 seconds",
    body: "A lightweight collector continuously polls CPU, GPU, RAM, disk, battery, and fan telemetry from real hardware, normalises it into a shared schema, and buffers locally if the connection drops — replaying on reconnect so no reading is lost.",
  },
  {
    icon: Thermometer,
    title: "2. Digital Twin Engine",
    tag: "Real-time",
    body: "Maps live utilisation onto a configurable rack profile, producing a continuously updated thermal load estimate — the same signal a facility engineer would be watching, computed automatically.",
  },
  {
    icon: Droplets,
    title: "3. Water Thermodynamic Model",
    tag: "Real-time",
    body: "Converts thermal load into cooling demand (kW) and estimated water consumption (L/hr) using PUE, WUE, and a psychrometric evaporation approximation from live ambient temperature and humidity.",
  },
  {
    icon: Database,
    title: "4. Memory Engine",
    tag: "Continuous",
    body: "Every significant event is summarised, embedded, and stored with a retrievable vector index — a growing institutional memory the AI agent draws on for every new decision.",
  },
  {
    icon: BrainCircuit,
    title: "5. AI Decision Agent",
    tag: "On demand",
    body: "Retrieves the most similar past incidents via similarity search, reasons over current live state plus retrieved context, and produces a recommendation with a confidence score and cited evidence.",
  },
];

const principles = [
  "Reasons over live telemetry, not batch reports or offline simulation — every recommendation reflects what's happening right now.",
  "Runs with zero mandatory paid cloud dependency: local buffering, a deterministic rules-based fallback, and free-tier storage.",
  "Every recommendation is explainable — it stores exactly which past events it was grounded in.",
  "Water usage estimates are sanity-checked against published industry benchmarks (0.5–2.0 L/kWh) automatically.",
];

export default function Solution() {
  return (
    <div className="relative bg-abyss">
      <section className="relative pt-32 pb-16 border-b border-rack overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-5xl mx-auto px-5 md:px-8">
          <motion.span
            variants={fadeUp} initial="hidden" animate="show"
            className="inline-flex items-center gap-2 rounded-full border border-signal/30 bg-signal/10 px-3.5 py-1.5 text-xs font-mono text-signal mb-6"
          >
            <CheckCircle2 size={12} /> THE SOLUTION
          </motion.span>
          <motion.h1
            variants={fadeUp} initial="hidden" animate="show" custom={1}
            className="font-display text-4xl md:text-5xl font-semibold text-frost leading-tight max-w-3xl"
          >
            One live reasoning loop that connects
            <span className="text-gradient-coolant"> compute, cooling, and memory.</span>
          </motion.h1>
          <motion.p
            variants={fadeUp} initial="hidden" animate="show" custom={2}
            className="mt-6 text-lg text-mist leading-relaxed max-w-2xl"
          >
            AquaMind AI ingests real telemetry as it happens, simulates thermal
            behaviour, estimates water and cooling demand, retrieves relevant
            past incidents, and produces an explainable AI recommendation —
            end to end, in under 5 seconds.
          </motion.p>
        </div>
      </section>

      {/* PIPELINE DETAIL */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-5 md:px-8">
          <div className="space-y-4">
            {stages.map((s, i) => (
              <motion.div
                key={s.title}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-60px" }} custom={i}
                className="card-glass rounded-2xl p-6 md:p-7 flex flex-col md:flex-row gap-5 md:items-start"
              >
                <div className="shrink-0 h-12 w-12 rounded-xl bg-hall-3 border border-rack-2 flex items-center justify-center">
                  <s.icon size={20} className="text-coolant-2" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 flex-wrap mb-1.5">
                    <h3 className="font-display font-semibold text-frost text-lg">{s.title}</h3>
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

      {/* DESIGN PRINCIPLES */}
      <section className="relative border-t border-rack bg-hall py-20 overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-6xl mx-auto px-5 md:px-8 grid lg:grid-cols-2 gap-14 items-start">
          <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}>
            <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono flex items-center gap-2">
              <Layers size={13} /> Design principles
            </span>
            <h2 className="font-display text-3xl font-semibold text-frost mt-3 leading-tight">
              Built for the problem as it actually happens.
            </h2>
            <p className="text-mist mt-4 leading-relaxed">
              Cooling and water decisions are time-sensitive — by the time a
              monthly report flags a problem, the opportunity to act on it is
              gone. This system closes that gap by reasoning continuously,
              on live data, the moment a pattern emerges.
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