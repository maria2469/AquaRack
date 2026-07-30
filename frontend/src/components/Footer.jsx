import { Droplets, FolderGit2 } from "lucide-react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="relative bg-black border-t border-white/10">
      <div className="max-w-7xl mx-auto px-5 md:px-8 py-12 grid grid-cols-1 md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="flex items-center gap-2 mb-3">
            <span className="liquid-glass flex h-9 w-9 items-center justify-center rounded-full">
              <Droplets size={16} className="text-white" />
            </span>
            <span className="font-heading text-2xl text-white">
              AquaMind AI
            </span>
          </div>
          <p className="text-sm font-body font-light text-white/70 max-w-sm leading-relaxed">
            A digital-twin platform for AI data-centre operations — reasoning about
            compute, cooling, and water in one continuous loop, from a single
            laptop today to a distributed fleet tomorrow.
          </p>
        </div>

        <div>
          <h4 className="text-xs uppercase tracking-[0.18em] text-white/50 font-body mb-3">Product</h4>
          <ul className="space-y-2 text-sm font-body">
            <li><Link to="/problem" className="text-white/70 hover:text-white transition-colors">The Problem</Link></li>
            <li><Link to="/solution" className="text-white/70 hover:text-white transition-colors">The Solution</Link></li>
            <li><Link to="/dashboard" className="text-white/70 hover:text-white transition-colors">Live Dashboard</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-xs uppercase tracking-[0.18em] text-white/50 font-body mb-3">Project</h4>
          <ul className="space-y-2 text-sm font-body">
            <li><Link to="/about" className="text-white/70 hover:text-white transition-colors">About &amp; Architecture</Link></li>
            <li>
              <a
                href="#"
                className="text-white/70 hover:text-white transition-colors inline-flex items-center gap-1.5"
              >
                <FolderGit2 size={14} /> Source (Phase 1 + 2)
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="max-w-7xl mx-auto px-5 md:px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs font-body text-white/50">
          <span>© {new Date().getFullYear()} AquaRack. Agentic Digital Twin Platform.</span>
          <span className="font-mono">v1.0.0 · SDD Draft for Engineering Review</span>
        </div>
      </div>
    </footer>
  );
}
