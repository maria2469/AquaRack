import { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { Menu, X, Droplets } from "lucide-react";
import { ArrowUpRightIcon } from "./ui/icons";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/dashboard", label: "Live Dashboard" },
  { to: "/fleet", label: "Fleet Management" },
  { to: "/memory", label: "Memory & Analytics" },
  { to: "/compare", label: "Benchmark" },
  { to: "/about", label: "About" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="fixed top-4 left-0 right-0 z-50 px-4 md:px-8 lg:px-16">
      <nav className="max-w-7xl mx-auto flex items-center justify-between">
        <NavLink
          to="/"
          className="liquid-glass flex h-12 items-center gap-2.5 rounded-full px-4 shrink-0"
        >
          <Droplets size={18} className="text-white" strokeWidth={2.2} />
          <span className="font-heading font-semibold text-base text-white tracking-tight">AquaRack</span>
        </NavLink>

        <div className="hidden md:flex items-center gap-1 liquid-glass rounded-full px-1.5 py-1.5">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `px-3 py-2 text-sm font-medium font-body rounded-full transition-colors ${isActive ? "text-white bg-white/10" : "text-white/70 hover:text-white"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
          <NavLink
            to="/dashboard"
            className="ml-1 inline-flex items-center gap-1.5 rounded-full bg-white text-black px-4 py-2 text-sm font-medium font-body hover:bg-white/90 transition-colors"
          >
            Live Dashboard <ArrowUpRightIcon size={14} />
          </NavLink>
        </div>

        <button
          className="md:hidden liquid-glass h-12 w-12 rounded-full flex items-center justify-center text-white"
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </nav>

      {open && (
        <div className="md:hidden mt-3 liquid-glass rounded-3xl px-5 py-4 flex flex-col gap-1 max-w-7xl mx-auto">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `px-3.5 py-2.5 rounded-lg text-sm font-medium font-body ${isActive ? "text-white bg-white/10" : "text-white/70"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
          <NavLink
            to="/dashboard"
            onClick={() => setOpen(false)}
            className="mt-2 inline-flex items-center justify-center gap-1.5 rounded-full bg-white text-black px-4 py-2.5 text-sm font-medium font-body"
          >
            Live Dashboard <ArrowUpRightIcon size={14} />
          </NavLink>
        </div>
      )}
    </header>
  );
}