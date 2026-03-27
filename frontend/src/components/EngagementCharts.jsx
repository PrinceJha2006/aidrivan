import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function ChartCard({ title, children }) {
  return (
    <div className="card animate-rise">
      <h3 className="mb-4 text-lg font-semibold text-ink">{title}</h3>
      <div className="h-[280px]">{children}</div>
    </div>
  );
}

export default function EngagementCharts({ trends }) {
  const byTweet = trends?.by_tweet ?? [];
  const week = trends?.week ?? [];
  const month = trends?.month ?? [];

  return (
    <section className="mt-6 space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Per Tweet Engagement (Likes/Retweets/Replies)">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={byTweet}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="likes" fill="#0ea5e9" />
              <Bar dataKey="retweets" fill="#84cc16" />
              <Bar dataKey="replies" fill="#f43f5e" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Per Tweet Views">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={byTweet}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="views" fill="#1e293b" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Last 7 Days Trend">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={week}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="tweet_count" stroke="#0ea5e9" />
              <Line type="monotone" dataKey="likes" stroke="#84cc16" />
              <Line type="monotone" dataKey="replies" stroke="#f43f5e" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Last 30 Days Trend">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={month}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="tweet_count" stroke="#0ea5e9" />
              <Line type="monotone" dataKey="likes" stroke="#84cc16" />
              <Line type="monotone" dataKey="retweets" stroke="#1e293b" />
              <Line type="monotone" dataKey="replies" stroke="#f43f5e" />
              <Line type="monotone" dataKey="views" stroke="#a855f7" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </section>
  );
}
