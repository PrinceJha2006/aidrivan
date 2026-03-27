import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const COLORS = ["#84cc16", "#0ea5e9", "#f43f5e"];

export default function SentimentChart({ summary }) {
  const data = [
    { name: "Positive", value: summary?.positive ?? 0 },
    { name: "Neutral", value: summary?.neutral ?? 0 },
    { name: "Negative", value: summary?.negative ?? 0 },
  ];

  return (
    <div className="card h-[320px] animate-rise">
      <h3 className="mb-4 text-lg font-semibold text-ink">Sentiment Mix</h3>
      <ResponsiveContainer width="100%" height="85%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
