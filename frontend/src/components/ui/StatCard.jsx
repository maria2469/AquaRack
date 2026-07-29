export default function StatCard({ icon: Icon, label, value, unit, accent = "coolant", hint }) {
  const accentMap = {
    coolant: "text-coolant-2",
    flow: "text-flow",
    signal: "text-signal",
    alert: "text-alert",
    amber: "text-amber",
  };
  return (
    <div className="card-glass rounded-2xl p-5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-[0.18em] text-mist font-medium">{label}</span>
        {Icon && <Icon size={16} className={accentMap[accent]} strokeWidth={2} />}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className={`font-mono text-3xl font-semibold ${accentMap[accent]}`}>{value}</span>
        {unit && <span className="text-sm text-mist font-mono">{unit}</span>}
      </div>
      {hint && <p className="text-xs text-mist/80">{hint}</p>}
    </div>
  );
}
