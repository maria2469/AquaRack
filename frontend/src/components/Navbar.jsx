import { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { Menu, X, Droplets } from "lucide-react";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/problem", label: "The Problem" },
  { to: "/solution", label: "Solution" },
  { to: "/dashboard", label: "Live Dashboard" },
  { to: "/about", label: "About" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-colors duration-300 ${
        scrolled ? "bg-abyss/85 backdrop-blur-md border-b border-rack" : "bg-transparent"
      }`}
    >
      <nav className="max-w-7xl mx-auto px-5 md:px-8 h-16 flex items-center justify-between">
        <NavLink to="/" className="flex items-center gap-2 group">
          <span className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-hall-3 border border-rack-2 group-hover:border-coolant transition-colors">
            <Droplets size={16} className="text-flow" strokeWidth={2.2} />
          </span>
          <span className="font-display font-semibold text-frost tracking-tight text-lg">
            AquaMind <span className="text-coolant-2">AI</span>
          </span>
        </NavLink>

        <div className="hidden md:flex items-center gap-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "text-frost bg-hall-3"
                    : "text-mist hover:text-fog hover:bg-hall-2"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </div>

        <div className="hidden md:block">
          <NavLink
            to="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg bg-coolant/90 hover:bg-coolant px-4 py-2 text-sm font-semibold text-abyss transition-colors shadow-[0_0_20px_-4px_rgba(43,127,255,0.6)]"
          >
            Open Dashboard
          </NavLink>
        </div>

        <button
          className="md:hidden text-fog p-2"
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </nav>

      {open && (
        <div className="md:hidden bg-abyss/97 backdrop-blur-md border-t border-rack px-5 pb-5 pt-2 flex flex-col gap-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `px-3.5 py-2.5 rounded-lg text-sm font-medium ${
                  isActive ? "text-frost bg-hall-3" : "text-mist"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </div>
      )}
    </header>
  );
}
