export default function MetricCard({ title, value, tone = "sky" }) {
  const colorMap = {
    sky: "bg-sky/15 text-sky",
    lime: "bg-lime/20 text-lime-700",
    rose: "bg-rose-100 text-rose-700",
    slate: "bg-slate-100 text-slate-700",
  };

  return (
    <div className="card animate-rise">
      <div className="text-sm font-medium text-slate-500">{title}</div>
      <div className="mt-2 text-3xl font-bold tracking-tight text-ink">{value}</div>
      <div className={`pill mt-3 ${colorMap[tone] || colorMap.slate}`}>Live KPI</div>
    </div>
  );
}
