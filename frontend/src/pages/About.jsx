import { motion } from "framer-motion";
import { Server, Cloud, GitBranch, Cpu } from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.07 } }),
};

const stack = [
  { group: "Orchestration", items: ["FastAPI", "Pydantic", "SQLAlchemy"] },
  { group: "Data & Memory", items: ["CockroachDB", "Vector index (HNSW)", "SQLite (local buffer)"] },
  { group: "AI Reasoning", items: ["Amazon Bedrock", "Titan Embeddings V2", "Local sentence-transformer fallback"] },
  { group: "Frontend", items: ["React", "Tailwind CSS", "Recharts", "Three.js / R3F"] },
];

const phases = [
  {
    icon: Server,
    title: "Phase 1 — Standalone Laptop Digital Twin",
    status: "Complete",
    body: "The full workflow — telemetry, digital twin, water model, memory engine, and AI agent — running end to end on a single laptop with zero mandatory cloud dependency.",
  },
  {
    icon: Cloud,
    title: "Phase 2 — Distributed / Cloud-Scale",
    status: "Complete",
    body: "The same modules promoted to a distributed, multi-agent system across a fleet of devices — OpenDC/CloudSim integration, multi-node CockroachDB, and a peer-agent orchestration layer.",
  },
];

export default function About() {
  return (
    <div className="relative bg-abyss">
      <section className="relative pt-32 pb-16 border-b border-rack overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-5xl mx-auto px-5 md:px-8">
          <motion.span
            variants={fadeUp} initial="hidden" animate="show"
            className="inline-flex items-center gap-2 rounded-full border border-rack-2 bg-hall-2 px-3.5 py-1.5 text-xs font-mono text-flow-2 mb-6"
          >
            <GitBranch size={12} /> ABOUT THE PROJECT
          </motion.span>
          <motion.h1
            variants={fadeUp} initial="hidden" animate="show" custom={1}
            className="font-display text-4xl md:text-5xl font-semibold text-frost leading-tight max-w-3xl"
          >
            A digital twin, built in two phases,
            <span className="text-gradient-coolant"> on one architecture.</span>
          </motion.h1>
          <motion.p
            variants={fadeUp} initial="hidden" animate="show" custom={2}
            className="mt-6 text-lg text-mist leading-relaxed max-w-2xl"
          >
            AquaMind AI's Software Design Document specifies the same data
            contracts, API shapes, and database schema across both phases —
            so scaling from a laptop to a fleet is a matter of configuration
            and deployment topology, not a rewrite.
          </motion.p>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-5xl mx-auto px-5 md:px-8 space-y-5">
          {phases.map((p, i) => (
            <motion.div
              key={p.title}
              variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
              className="card-glass rounded-2xl p-7 flex gap-5"
            >
              <div className="shrink-0 h-12 w-12 rounded-xl bg-hall-3 border border-rack-2 flex items-center justify-center">
                <p.icon size={20} className="text-coolant-2" />
              </div>
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="font-display font-semibold text-frost text-lg">{p.title}</h3>
                  <span className="text-xs font-mono text-signal bg-signal/10 border border-signal/20 rounded px-2 py-0.5">
                    {p.status}
                  </span>
                </div>
                <p className="text-sm text-mist leading-relaxed">{p.body}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="relative border-t border-rack bg-hall py-20 overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-6xl mx-auto px-5 md:px-8">
          <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} className="mb-10">
            <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono flex items-center gap-2">
              <Cpu size={13} /> Technology
            </span>
            <h2 className="font-display text-3xl font-semibold text-frost mt-3">The stack underneath</h2>
          </motion.div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {stack.map((s, i) => (
              <motion.div
                key={s.group}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
                className="card-glass rounded-2xl p-6"
              >
                <h3 className="font-display font-semibold text-frost mb-4 text-sm uppercase tracking-wide">
                  {s.group}
                </h3>
                <ul className="space-y-2">
                  {s.items.map((it) => (
                    <li key={it} className="text-sm text-mist flex items-center gap-2">
                      <span className="h-1 w-1 rounded-full bg-coolant-2 shrink-0" />
                      {it}
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
