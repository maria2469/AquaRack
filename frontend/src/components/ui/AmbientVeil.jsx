/**
 * Cheap, non-WebGL ambient backdrop for sections below the hero:
 * a faint rack-grid plus a few slow-rising "droplet/data" motes.
 * Keeps the water + data motif present throughout without the
 * cost of running Three.js on every section.
 */
export default function AmbientVeil({ dense = false }) {
  const motes = dense ? 14 : 8;
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 grid-veil opacity-60" />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-abyss/40 to-abyss" />
      {Array.from({ length: motes }).map((_, i) => (
        <span
          key={i}
          className="absolute block rounded-full bg-flow/40 animate-rise"
          style={{
            left: `${(i * 137) % 100}%`,
            bottom: `-${Math.random() * 40}px`,
            width: `${2 + (i % 3)}px`,
            height: `${2 + (i % 3)}px`,
            animationDelay: `${(i * 0.9).toFixed(1)}s`,
            animationDuration: `${10 + (i % 5) * 2}s`,
          }}
        />
      ))}
    </div>
  );
}
