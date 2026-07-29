import { Droplets, FolderGit2 } from "lucide-react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="relative border-t border-rack bg-hall">
      <div className="max-w-7xl mx-auto px-5 md:px-8 py-12 grid grid-cols-1 md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="flex items-center gap-2 mb-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-hall-3 border border-rack-2">
              <Droplets size={16} className="text-flow" />
            </span>
            <span className="font-display font-semibold text-frost text-lg">
              AquaMind AI
            </span>
          </div>
          <p className="text-sm text-mist max-w-sm leading-relaxed">
            A digital-twin platform for AI data-centre operations — reasoning about
            compute, cooling, and water in one continuous loop, from a single
            laptop today to a distributed fleet tomorrow.
          </p>
        </div>

        <div>
          <h4 className="text-xs uppercase tracking-[0.18em] text-mist mb-3">Product</h4>
          <ul className="space-y-2 text-sm">
            <li><Link to="/problem" className="text-fog hover:text-flow transition-colors">The Problem</Link></li>
            <li><Link to="/solution" className="text-fog hover:text-flow transition-colors">The Solution</Link></li>
            <li><Link to="/dashboard" className="text-fog hover:text-flow transition-colors">Live Dashboard</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-xs uppercase tracking-[0.18em] text-mist mb-3">Project</h4>
          <ul className="space-y-2 text-sm">
            <li><Link to="/about" className="text-fog hover:text-flow transition-colors">About &amp; Architecture</Link></li>
            <li>
              <a
                href="#"
                className="text-fog hover:text-flow transition-colors inline-flex items-center gap-1.5"
              >
                <FolderGit2 size={14} /> Source (Phase 1 + 2)
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-rack">
        <div className="max-w-7xl mx-auto px-5 md:px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-mist">
          <span>© {new Date().getFullYear()} AquaMind AI. Phase 1 — Standalone Digital Twin.</span>
          <span className="font-mono">v1.0.0 · SDD Draft for Engineering Review</span>
        </div>
      </div>
    </footer>
  );
}
