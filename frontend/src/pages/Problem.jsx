import { motion } from "framer-motion";
import { Droplets, TrendingUp, EyeOff, Wrench, AlertTriangle } from "lucide-react";
import AmbientVeil from "../components/ui/AmbientVeil";

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

export default function Problem() {
  return (
    <div className="relative bg-abyss">
      <section className="relative pt-32 pb-20 overflow-hidden border-b border-rack">
        <AmbientVeil />
        <div className="relative max-w-5xl mx-auto px-5 md:px-8">
          <motion.span
            variants={fadeUp} initial="hidden" animate="show"
            className="inline-flex items-center gap-2 rounded-full border border-alert/30 bg-alert/10 px-3.5 py-1.5 text-xs font-mono text-alert mb-6"
          >
            <AlertTriangle size={12} /> THE PROBLEM
          </motion.span>
          <motion.h1
            variants={fadeUp} initial="hidden" animate="show" custom={1}
            className="font-heading text-4xl md:text-5xl font-semibold text-frost leading-tight max-w-3xl"
          >
            Compute has a water footprint —
            <span className="text-gradient-coolant"> and almost nobody sees it in real time.</span>
          </motion.h1>
          <motion.p
            variants={fadeUp} initial="hidden" animate="show" custom={2}
            className="mt-6 text-lg text-mist leading-relaxed max-w-2xl"
          >
            Every AI workload that raises a rack's utilisation also raises its thermal
            load — and that heat has to go somewhere. In most facilities, the water
            and energy cost of removing it is calculated after the month closes, not
            while the decision that caused it is still being made.
          </motion.p>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-6xl mx-auto px-5 md:px-8">
          <motion.div
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
            className="grid md:grid-cols-3 gap-6 mb-16"
          >
            <div className="card-glass rounded-2xl p-7">
              <div className="font-mono text-3xl font-semibold text-flow">0.5–2.0</div>
              <p className="text-sm text-mist mt-2">litres of water per kWh (L/kWh) is the typical WUE range for air-cooled facilities — a benchmark this platform validates estimates against.</p>
            </div>
            <div className="card-glass rounded-2xl p-7">
              <div className="font-mono text-3xl font-semibold text-coolant-2">1.4</div>
              <p className="text-sm text-mist mt-2">a common default PUE for a small air-cooled facility — the ratio of total facility energy to IT equipment energy.</p>
            </div>
            <div className="card-glass rounded-2xl p-7">
              <div className="font-mono text-3xl font-semibold text-amber">85%+</div>
              <p className="text-sm text-mist mt-2">utilisation is where thermal risk compounds fastest — exactly where reactive, alarm-driven cooling struggles most.</p>
            </div>
          </motion.div>

          <div className="grid sm:grid-cols-2 gap-5">
            {painPoints.map((p, i) => (
              <motion.div
                key={p.title}
                variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}
                className="card-glass rounded-2xl p-6 flex gap-4"
              >
                <div className="shrink-0 h-10 w-10 rounded-lg bg-hall-3 border border-rack-2 flex items-center justify-center">
                  <p.icon size={18} className="text-alert" />
                </div>
                <div>
                  <h3 className="font-heading font-semibold text-frost mb-1.5">{p.title}</h3>
                  <p className="text-sm text-mist leading-relaxed">{p.body}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative border-t border-rack bg-hall py-16">
        <div className="max-w-4xl mx-auto px-5 md:px-8 text-center">
          <motion.p
            variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
            className="text-mist text-lg leading-relaxed"
          >
            The gap isn't a lack of sensors. It's that thermal telemetry, water
            physics, and institutional memory of past incidents all live in
            different places — and nothing reasons across all three, live,
            before a decision is made.
          </motion.p>
        </div>
      </section>
    </div>
  );
}
