import { Suspense, lazy } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Droplets, TrendingUp, EyeOff, Wrench, AlertTriangle, ArrowRight } from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";

const WaterDropScene = lazy(() => import("../components/three/WaterDropScene"));

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.07 } }),
};

const painPoints = [
  {
    icon: EyeOff,
    title: "Cooling decisions are made blind",
    body: "Operators react to temperature alarms after the fact instead of anticipating thermal load from the workload that's about to run.",
  },
  {
    icon: Droplets,
    title: "Water usage is an afterthought",
    body: "Facility teams track PUE closely but WUE — litres of water per kWh of compute — rarely gets the same real-time visibility.",
  },
  {
    icon: TrendingUp,
    title: "Utilisation keeps climbing",
    body: "AI training and inference workloads are pushing rack density and thermal load up faster than cooling infrastructure planning cycles.",
  },
  {
    icon: Wrench,
    title: "No institutional memory",
    body: "The same thermal incident gets re-diagnosed from scratch every time, because past decisions and their outcomes aren't retrievable.",
  },
];

const stats = [
  { value: "0.5–2.0", label: "L/kWh", sub: "Typical WUE range — most facilities never track this live." },
  { value: "1.4×", label: "PUE", sub: "Common air-cooled facility energy overhead — invisible to the workload scheduler." },
  { value: "85%+", label: "Utilisation", sub: "Where thermal risk compounds fastest and reactive cooling breaks down." },
];

export default function Problem() {
  return (
    <div className="relative bg-abyss">

      {/* ── HERO — fullscreen with 3D water-waste background ── */}
      <section className="relative h-screen overflow-hidden bg-black">

        {/* 3D scene canvas */}
        <Suspense fallback={null}>
          <WaterDropScene className="absolute inset-0 z-0 pointer-events-none" />
        </Suspense>

        {/* vignette overlays - subtle left gradient to keep text readable without hiding right-side 3D scene */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black z-[1] pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/70 via-black/30 to-transparent z-[1] pointer-events-none" />

        {/* hero content */}
        <div className="relative z-10 flex flex-col h-full justify-between px-6 pb-10 pt-28 sm:pb-12 sm:pt-32 md:px-12 md:pb-16 lg:px-16">

          {/* top: badge + headline */}
          <div className="max-w-3xl">
            <div
              className="inline-flex items-center gap-2 rounded-full border border-alert/40 bg-alert/10 px-4 py-1.5 text-xs font-mono text-alert mb-5 sm:mb-6"
              style={{ animation: "fadeSlideUp 0.8s ease 0.2s both" }}
            >
              <AlertTriangle size={12} />
              THE PROBLEM
            </div>

            <h1
              className="text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-medium leading-[1.1] tracking-tight text-white"
              style={{ animation: "fadeSlideUp 0.8s ease 0.4s both" }}
            >
              Compute has a water
              <br />
              footprint — and almost
              <br />
              nobody sees it in real time.
            </h1>
          </div>

          {/* bottom: description + CTA */}
          <div>
            <p
              className="text-sm sm:text-base md:text-lg leading-relaxed text-white/60 max-w-sm sm:max-w-lg mb-5 sm:mb-6"
              style={{ animation: "fadeSlideUp 0.8s ease 0.7s both" }}
            >
              Every AI workload that raises a rack's utilisation also raises its thermal load — and that heat has to go somewhere. The water and energy cost is calculated after the month closes, not while the decision is being made.
            </p>
            <div
              className="flex flex-wrap gap-3"
              style={{ animation: "fadeSlideUp 0.8s ease 0.9s both" }}
            >
              <Link
                to="/solution"
                className="rounded-lg bg-white px-5 py-2.5 sm:px-6 sm:py-3 text-sm font-medium text-black hover:scale-105 transition-transform inline-flex items-center gap-2"
              >
                See the Solution <ArrowRight size={16} />
              </Link>
              <Link
                to="/dashboard"
                className="rounded-lg border border-white/20 bg-white/5 backdrop-blur-sm px-5 py-2.5 sm:px-6 sm:py-3 text-sm font-medium text-white hover:bg-white/10 transition-colors inline-flex items-center gap-2"
              >
                Open Dashboard <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── STATS BAND ── */}
      <section className="relative border-y border-rack/60 bg-hall-2 py-12 overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-6xl mx-auto px-5 md:px-8">
          <div className="grid md:grid-cols-3 gap-px bg-rack/40 rounded-2xl overflow-hidden">
            {stats.map((s, i) => (
              <motion.div
                key={s.label}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
                className="bg-hall-2 px-8 py-8"
              >
                <div className="flex items-baseline gap-2 mb-2">
                  <span className="font-mono text-4xl font-semibold text-alert">{s.value}</span>
                  <span className="font-mono text-base text-alert/60">{s.label}</span>
                </div>
                <p className="text-sm text-mist leading-relaxed">{s.sub}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PAIN POINTS GRID ── */}
      <section className="py-20 md:py-28">
        <div className="max-w-6xl mx-auto px-5 md:px-8">
          <motion.div
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
            className="mb-12"
          >
            <p className="text-xs uppercase tracking-[0.18em] text-alert/70 font-mono mb-3">// Root causes</p>
            <h2 className="font-heading text-3xl md:text-4xl text-frost leading-tight max-w-xl">
              Four gaps the industry hasn't closed.
            </h2>
          </motion.div>

          <div className="grid sm:grid-cols-2 gap-5">
            {painPoints.map((p, i) => (
              <motion.div
                key={p.title}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-60px" }} custom={i}
                className="card-glass rounded-2xl p-6 flex gap-4 group hover:border-alert/20 transition-colors"
              >
                <div className="shrink-0 h-11 w-11 rounded-xl bg-alert/10 border border-alert/20 flex items-center justify-center group-hover:bg-alert/15 transition-colors">
                  <p.icon size={18} className="text-alert" />
                </div>
                <div>
                  <h3 className="font-heading font-semibold text-frost mb-2">{p.title}</h3>
                  <p className="text-sm text-mist leading-relaxed">{p.body}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CLOSING PULL-QUOTE ── */}
      <section className="relative border-t border-rack bg-hall py-20 overflow-hidden">
        <AmbientVeil />
        <div className="relative max-w-4xl mx-auto px-5 md:px-8 text-center">
          <motion.p
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
            className="text-mist text-lg md:text-xl leading-relaxed mb-8"
          >
            The gap isn't a lack of sensors. It's that thermal telemetry, water
            physics, and institutional memory of past incidents all live in
            different places — and nothing reasons across all three, live,
            before a decision is made.
          </motion.p>
          <motion.div
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={1}
          >
            <Link
              to="/solution"
              className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-medium text-black hover:scale-105 transition-transform"
            >
              How AquaRack Solves This <ArrowRight size={15} />
            </Link>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
