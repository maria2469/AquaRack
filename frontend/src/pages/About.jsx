import { motion } from "framer-motion";
import { Server, Cloud, GitBranch, Cpu, ShieldCheck, Zap, Droplets } from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.07 } }),
};

const stack = [
  { group: "Backend", items: ["FastAPI", "Pydantic", "SQLAlchemy", "LangGraph", "AsyncIO"] },
  { group: "Data & Memory", items: ["CockroachDB Managed MCP", "Vector Index Search", "Episode Memory Storage"] },
  { group: "AI Reasoning", items: ["Ollama (Qwen2.5)", "Multi-Agent Workflow", "LangChain", "Groq Fallback"] },
  { group: "Frontend & UI", items: ["React 18", "Tailwind CSS", "Framer Motion", "Lucide React"] },
];

const pillars = [
  {
    icon: Server,
    title: "Real-Time Telemetry Collection",
    status: "Active",
    body: "Continuous monitoring of GPU, CPU, temperature, and humidity across data center racks with 5-second polling intervals and automatic buffer replay on network disconnects.",
  },
  {
    icon: Cloud,
    title: "Multi-Agent Reasoning System",
    status: "Active",
    body: "LangGraph-powered agent orchestration with Monitor, Predictor, Optimizer, Action, Reflect, and Explainer agents that collaborate to optimize water usage and thermal efficiency.",
  },
  {
    icon: ShieldCheck,
    title: "CockroachDB Vector Memory",
    status: "Active",
    body: "Structured MCP server tools for vector similarity search, episode memory storage, and historical incident retrieval to inform intelligent decision-making.",
  },
  {
    icon: Droplets,
    title: "Water Conservation Optimization",
    status: "Active",
    body: "Thermodynamic modeling and predictive analytics to reduce evaporative cooling water consumption while maintaining optimal data center operating conditions.",
  },
  {
    icon: Zap,
    title: "Energy Efficiency Management",
    status: "Active",
    body: "GPU workload optimization and thermal management strategies to reduce energy consumption while maintaining computational performance.",
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
            <GitBranch size={12} /> ABOUT AQUARACK
          </motion.span>
          <motion.h1
            variants={fadeUp} initial="hidden" animate="show" custom={1}
            className="font-heading text-4xl md:text-5xl font-semibold text-frost leading-tight max-w-3xl"
          >
            AquaRack: Intelligent Data Center
            <span className="text-gradient-coolant"> Optimization Platform</span>
          </motion.h1>
          <motion.p
            variants={fadeUp} initial="hidden" animate="show" custom={2}
            className="mt-6 text-lg text-mist leading-relaxed max-w-2xl"
          >
            AquaRack combines real-time hardware telemetry, multi-agent AI reasoning, and vector-based memory 
            to optimize water usage and thermal efficiency in data center operations through intelligent decision-making.
          </motion.p>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-5xl mx-auto px-5 md:px-8">
          <div className="grid sm:grid-cols-2 gap-5">
            {pillars.map((p, i) => (
              <motion.div
                key={p.title}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
                className="card-glass rounded-2xl p-6 flex gap-4"
              >
                <div className="shrink-0 h-12 w-12 rounded-xl bg-hall-3 border border-rack-2 flex items-center justify-center">
                  <p.icon size={20} className="text-coolant-2" />
                </div>
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-heading font-semibold text-frost text-base">{p.title}</h3>
                    <span className="text-xs font-mono text-signal bg-signal/10 border border-signal/20 rounded px-2 py-0.5">
                      {p.status}
                    </span>
                  </div>
                  <p className="text-sm text-mist leading-relaxed">{p.body}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative border-t border-rack bg-hall py-20 overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-6xl mx-auto px-5 md:px-8">
          <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} className="mb-10">
            <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono flex items-center gap-2">
              <Cpu size={13} /> Technology Stack
            </span>
            <h2 className="font-heading text-3xl font-semibold text-frost mt-3">Built for scale and reliability</h2>
          </motion.div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {stack.map((s, i) => (
              <motion.div
                key={s.group}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
                className="card-glass rounded-2xl p-6"
              >
                <h3 className="font-heading font-semibold text-frost mb-4 text-sm uppercase tracking-wide">
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

      <section className="py-20">
        <div className="max-w-5xl mx-auto px-5 md:px-8">
          <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} className="mb-10">
            <span className="text-xs uppercase tracking-[0.18em] text-flow font-mono flex items-center gap-2">
              <GitBranch size={13} /> Multi-Agent Workflow
            </span>
            <h2 className="font-heading text-3xl font-semibold text-frost mt-3">How AquaRack thinks</h2>
          </motion.div>

          <motion.div 
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
            className="card-glass rounded-2xl p-8"
          >
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="font-heading font-semibold text-frost text-lg mb-4">Agent Pipeline</h3>
                <ol className="space-y-3">
                  <li className="flex items-start gap-3">
                    <span className="h-6 w-6 rounded-full bg-coolant/20 text-coolant text-xs font-mono flex items-center justify-center shrink-0">1</span>
                    <div>
                      <span className="text-sm font-semibold text-frost">Monitor Agent</span>
                      <p className="text-xs text-mist mt-1">Ingests telemetry and retrieves context from vector memory</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="h-6 w-6 rounded-full bg-coolant/20 text-coolant text-xs font-mono flex items-center justify-center shrink-0">2</span>
                    <div>
                      <span className="text-sm font-semibold text-frost">Predictor Agent</span>
                      <p className="text-xs text-mist mt-1">Assesses thermal/power risks using Ollama local inference</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="h-6 w-6 rounded-full bg-coolant/20 text-coolant text-xs font-mono flex items-center justify-center shrink-0">3</span>
                    <div>
                      <span className="text-sm font-semibold text-frost">Optimizer Agent</span>
                      <p className="text-xs text-mist mt-1">Formulates optimization strategies for water and energy usage</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="h-6 w-6 rounded-full bg-coolant/20 text-coolant text-xs font-mono flex items-center justify-center shrink-0">4</span>
                    <div>
                      <span className="text-sm font-semibold text-frost">Action Agent</span>
                      <p className="text-xs text-mist mt-1">Validates recommendations against guardrails and cluster health</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="h-6 w-6 rounded-full bg-coolant/20 text-coolant text-xs font-mono flex items-center justify-center shrink-0">5</span>
                    <div>
                      <span className="text-sm font-semibold text-frost">Reflect Agent</span>
                      <p className="text-xs text-mist mt-1">Writes episodes to CockroachDB for continuous learning</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="h-6 w-6 rounded-full bg-coolant/20 text-coolant text-xs font-mono flex items-center justify-center shrink-0">6</span>
                    <div>
                      <span className="text-sm font-semibold text-frost">Explainer Agent</span>
                      <p className="text-xs text-mist mt-1">Assembles human-readable recommendations with evidence</p>
                    </div>
                  </li>
                </ol>
              </div>
              <div>
                <h3 className="font-heading font-semibold text-frost text-lg mb-4">Key Benefits</h3>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <Droplets size={16} className="text-signal shrink-0 mt-0.5" />
                    <span className="text-sm text-mist">Reduced water consumption through predictive cooling optimization</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Zap size={16} className="text-flow shrink-0 mt-0.5" />
                    <span className="text-sm text-mist">Lower energy costs via intelligent GPU workload distribution</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <ShieldCheck size={16} className="text-coolant shrink-0 mt-0.5" />
                    <span className="text-sm text-mist">Improved reliability through incident prevention and memory-based learning</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Cloud size={16} className="text-amber shrink-0 mt-0.5" />
                    <span className="text-sm text-mist">Scalable architecture supporting multi-rack data center deployments</span>
                  </li>
                </ul>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
