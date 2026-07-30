import { Link } from "react-router-dom";
import { Suspense, lazy } from "react";
import { motion } from "framer-motion";
import BlurText from "../components/ui/BlurText";
import AmbientVeil from "../components/ui/AmbientVeil";
import {
  ArrowUpRightIcon,
  PlayIcon,
  ClockIcon,
  GlobeIcon,
  ImageIcon,
  MovieIcon,
  LightbulbIcon,
} from "../components/ui/icons";

const HeroScene = lazy(() => import("../components/three/HeroScene"));

const fadeBlur = {
  initial: { filter: "blur(10px)", opacity: 0, y: 20 },
  animate: { filter: "blur(0px)", opacity: 1, y: 0 },
};

const capabilities = [
  {
    icon: ImageIcon,
    tags: ["Telemetry", "Digital Twin", "Thermal Model", "5s Polling"],
    title: "Sense",
    body: "Every CPU, GPU, RAM and fan reading is polled continuously and mapped onto a configurable, rack-scale thermal model of your infrastructure.",
  },
  {
    icon: MovieIcon,
    tags: ["Water Model", "WUE", "Memory Engine", "Retrieval"],
    title: "Reason",
    body: "Thermal load is converted into cooling demand and litres-per-hour, then embedded alongside every past event for retrieval-augmented reasoning.",
  },
  {
    icon: LightbulbIcon,
    tags: ["AI Agent", "Explainable", "Auditable", "Fleet-Ready"],
    title: "Decide",
    body: "The decision agent retrieves similar past incidents and recommends an action — with the exact memories it was grounded in stored for audit.",
  },
];

export default function Home() {
  return (
    <div className="relative">
      {/* ---------------- SECTION 1: HERO ---------------- */}
      <section className="relative h-screen overflow-hidden bg-black">
        <Suspense fallback={null}>
          <HeroScene className="absolute inset-0 z-0" />
        </Suspense>
        <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black z-[1]" />

        <div className="relative z-10 flex flex-col h-full pt-24">
          <div className="flex-1 flex flex-col items-center justify-center px-4 text-center">
            <motion.div
              {...fadeBlur}
              transition={{ duration: 0.8, ease: "easeOut", delay: 0.4 }}
              className="liquid-glass rounded-full px-4 py-1.5 inline-flex items-center gap-2"
            >
              <span className="rounded-full bg-white text-black text-[10px] font-semibold font-body px-2 py-0.5">
                New
              </span>
              <span className="text-sm font-body text-white/90">
                Phase 1 — live demo ready, laptop to fleet
              </span>
            </motion.div>

            <div className="mt-6 max-w-3xl">
              <BlurText
                text="Every Watt of Compute Costs a Drop of Water"
                className="text-6xl md:text-7xl lg:text-[5.5rem] font-heading text-white leading-[0.8] tracking-[-4px]"
              />
            </div>

            <motion.p
              {...fadeBlur}
              transition={{ duration: 0.8, ease: "easeOut", delay: 0.8 }}
              className="mt-4 text-sm md:text-base text-white max-w-2xl font-body font-light leading-tight"
            >
              AquaMind AI is a digital-twin platform that watches your infrastructure think, feels
              the heat it gives off, and reasons — with memory — about the cooling and water cost
              of every decision, before you make it.
            </motion.p>

            <motion.div
              {...fadeBlur}
              transition={{ duration: 0.8, ease: "easeOut", delay: 1.1 }}
              className="mt-6 flex items-center gap-6"
            >
              <Link
                to="/dashboard"
                className="liquid-glass-strong rounded-full px-5 py-2.5 inline-flex items-center gap-2 text-white font-body font-medium text-sm"
              >
                Open Dashboard <ArrowUpRightIcon size={16} />
              </Link>
              <Link
                to="/solution"
                className="inline-flex items-center gap-2 text-white font-body font-medium text-sm"
              >
                <PlayIcon size={16} /> See How It Works
              </Link>
            </motion.div>

            <motion.div
              {...fadeBlur}
              transition={{ duration: 0.8, ease: "easeOut", delay: 1.3 }}
              className="mt-8 flex gap-4"
            >
              <div className="liquid-glass p-5 w-[220px] rounded-[1.25rem] text-left">
                <ClockIcon size={20} className="text-white/80" />
                <div className="text-4xl font-heading text-white tracking-[-1px] leading-none mt-4">
                  &lt;5s
                </div>
                <div className="text-xs font-body text-white/70 mt-1.5 leading-snug">
                  Ingest-to-recommendation latency
                </div>
              </div>
              <div className="liquid-glass p-5 w-[220px] rounded-[1.25rem] text-left">
                <GlobeIcon size={20} className="text-white/80" />
                <div className="text-4xl font-heading text-white tracking-[-1px] leading-none mt-4">
                  0.5–2.0
                </div>
                <div className="text-xs font-body text-white/70 mt-1.5 leading-snug">
                  Typical WUE range, litres per kWh
                </div>
              </div>
            </motion.div>
          </div>

          <motion.div
            {...fadeBlur}
            transition={{ duration: 0.8, ease: "easeOut", delay: 1.4 }}
            className="flex flex-col items-center gap-4 pb-8"
          >
            <div className="liquid-glass rounded-full px-4 py-1.5 text-xs font-body text-white/70">
              Same schemas, same reasoning loop — laptop-scale today, fleet-scale tomorrow
            </div>
            <div className="flex gap-12 md:gap-16">
              {["Compute", "Cooling", "Water", "Memory", "Agent"].map((w) => (
                <span
                  key={w}
                  className="font-heading text-2xl md:text-3xl text-white/60 tracking-tight"
                >
                  {w}
                </span>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ---------------- SECTION 2: CAPABILITIES ---------------- */}
      <section className="relative min-h-screen overflow-hidden bg-black">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_0%,rgba(255,255,255,0.06),transparent)]" />
        <AmbientVeil dense />

        <div className="relative z-10 px-8 md:px-16 lg:px-20 pt-24 pb-10 flex flex-col min-h-screen">
          <div className="mb-auto">
            <p className="text-sm font-body text-white/60 mb-6">// Capabilities</p>
            <h2 className="font-heading text-6xl md:text-7xl lg:text-[6rem] text-white leading-[0.9] tracking-[-3px]">
              Telemetry in,
              <br />
              a decision out
            </h2>
          </div>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
            {capabilities.map((c, i) => (
              <motion.div
                key={c.title}
                initial={{ filter: "blur(10px)", opacity: 0, y: 20 }}
                whileInView={{ filter: "blur(0px)", opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.8, ease: "easeOut", delay: i * 0.1 }}
                className="liquid-glass rounded-[1.25rem] p-7 min-h-[380px] flex flex-col"
              >
                <div className="flex items-center justify-between">
                  <div className="liquid-glass h-11 w-11 rounded-[0.75rem] flex items-center justify-center shrink-0">
                    <c.icon size={20} className="text-white" />
                  </div>
                  <span className="font-heading text-xl text-white/30 tracking-[-1px]">
                    0{i + 1}
                  </span>
                </div>

                <div className="mt-6 flex flex-wrap gap-2">
                  {c.tags.map((t) => (
                    <span
                      key={t}
                      className="liquid-glass rounded-full px-3 py-1.5 text-[11px] text-white/80 font-body whitespace-nowrap"
                    >
                      {t}
                    </span>
                  ))}
                </div>

                <div className="flex-1 min-h-8" />

                <div>
                  <h3 className="font-heading text-3xl md:text-4xl text-white tracking-[-1px] leading-none">
                    {c.title}
                  </h3>
                  <p className="mt-3 text-sm text-white/70 font-body font-light leading-relaxed max-w-[34ch]">
                    {c.body}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}