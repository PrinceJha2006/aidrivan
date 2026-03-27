import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const SENTIMENT_COLORS = {
  positive: "#16a34a",
  neutral: "#f59e0b",
  negative: "#ef4444",
};

function renderPieValueLabel({ cx, cy, midAngle, innerRadius, outerRadius, value }) {
  if (!value) return null;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.55;
  const x = cx + radius * Math.cos((-midAngle * Math.PI) / 180);
  const y = cy + radius * Math.sin((-midAngle * Math.PI) / 180);

  return (
    <text
      x={x}
      y={y}
      fill="#ffffff"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={18}
      fontWeight={700}
    >
      {value}
    </text>
  );
}

function formatNum(value) {
  return new Intl.NumberFormat().format(Number(value || 0));
}

function metricCards(summary) {
  return [
    { title: "Total Likes", value: summary?.total_likes ?? 0 },
    { title: "Total Replies", value: summary?.total_replies ?? 0 },
    { title: "Total Retweets", value: summary?.total_retweets ?? 0 },
    { title: "Total Views", value: summary?.total_views ?? 0 },
  ];
}

function sentimentData(summary) {
  return [
    { sentiment: "positive", count: summary?.positive ?? 0 },
    { sentiment: "neutral", count: summary?.neutral ?? 0 },
    { sentiment: "negative", count: summary?.negative ?? 0 },
  ];
}

function makeHistogram(values, bins = 8) {
  const clean = values.map((v) => Number(v || 0));
  if (!clean.length) return [];

  const min = Math.min(...clean);
  const max = Math.max(...clean);
  if (min === max) {
    return [{ bucket: `${min}`, count: clean.length }];
  }

  const step = Math.max(1, Math.ceil((max - min + 1) / bins));
  const buckets = [];
  for (let start = min; start <= max; start += step) {
    buckets.push({
      start,
      end: Math.min(start + step - 1, max),
      count: 0,
    });
  }

  clean.forEach((value) => {
    const idx = Math.min(Math.floor((value - min) / step), buckets.length - 1);
    buckets[idx].count += 1;
  });

  return buckets.map((b) => ({ bucket: `${b.start}-${b.end}`, count: b.count }));
}

function sectionCard(title, children) {
  return (
    <div className="card">
      <h3 className="mb-3 text-2xl font-bold text-ink">{title}</h3>
      {children}
    </div>
  );
}

function downloadCsv(rows) {
  if (!rows?.length) return;
  const headers = [
    "source_url",
    "text",
    "sentiment",
    "sentiment_score",
    "likes",
    "retweets",
    "replies",
    "views",
    "created_at",
    "user",
  ];

  const lines = [headers.join(",")];
  rows.forEach((r) => {
    const line = headers
      .map((h) => {
        const raw = r[h] ?? "";
        const str = String(raw).replaceAll('"', '""');
        return `"${str}"`;
      })
      .join(",");
    lines.push(line);
  });

  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "twitter_analysis_data.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function ClassicResultView({ rows = [], summary }) {
  const sentiment = sentimentData(summary);

  const sentimentGroups = {
    positive: rows.filter((r) => r.sentiment === "positive").slice(0, 3),
    neutral: rows.filter((r) => r.sentiment === "neutral").slice(0, 3),
    negative: rows.filter((r) => r.sentiment === "negative").slice(0, 3),
  };

  const likesHist = makeHistogram(rows.map((r) => r.likes));
  const retweetsHist = makeHistogram(rows.map((r) => r.retweets));
  const repliesHist = makeHistogram(rows.map((r) => r.replies));
  const viewsHist = makeHistogram(rows.map((r) => r.views));

  const byTweet = rows.map((r, i) => ({
    tweet: `${i + 1}`,
    likes: Number(r.likes || 0),
    retweets: Number(r.retweets || 0),
    replies: Number(r.replies || 0),
    views: Number(r.views || 0),
  }));

  const overallSentiment = sentiment.reduce((a, b) => (a.count > b.count ? a : b), {
    sentiment: "neutral",
    count: 0,
  }).sentiment;

  return (
    <div className="mt-6 space-y-6">
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-700">
        Successfully analyzed {summary?.count ?? 0} tweets!
      </div>

      {sectionCard(
        "Performance Metrics",
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {metricCards(summary).map((m) => (
            <div key={m.title} className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
              <div className="text-sm text-slate-500">{m.title}</div>
              <div className="mt-1 text-3xl font-bold text-ink">{formatNum(m.value)}</div>
            </div>
          ))}
        </div>
      )}

      {sectionCard(
        "Sentiment Analysis",
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="h-[340px] rounded-xl border border-slate-200 bg-slate-50/80 p-3">
            <div className="mb-2 text-sm font-semibold text-slate-600">Sentiment Distribution</div>
            <ResponsiveContainer width="100%" height="92%">
              <PieChart>
                <Pie
                  data={sentiment}
                  dataKey="count"
                  nameKey="sentiment"
                  innerRadius={34}
                  outerRadius={120}
                  label={renderPieValueLabel}
                  labelLine={false}
                >
                  {sentiment.map((entry) => (
                    <Cell key={entry.sentiment} fill={SENTIMENT_COLORS[entry.sentiment]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="h-[340px] rounded-xl border border-slate-200 bg-slate-50/80 p-3">
            <div className="mb-2 text-sm font-semibold text-slate-600">Sentiment Count</div>
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={sentiment}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="sentiment" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count">
                  {sentiment.map((entry) => (
                    <Cell key={entry.sentiment} fill={SENTIMENT_COLORS[entry.sentiment]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {sectionCard(
        "Sentiment Breakdown",
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
              <div className="text-sm text-slate-500">Positive Tweets</div>
              <div className="text-3xl font-bold text-emerald-600">{summary?.positive ?? 0}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
              <div className="text-sm text-slate-500">Neutral Tweets</div>
              <div className="text-3xl font-bold text-amber-500">{summary?.neutral ?? 0}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
              <div className="text-sm text-slate-500">Negative Tweets</div>
              <div className="text-3xl font-bold text-rose-600">{summary?.negative ?? 0}</div>
            </div>
          </div>

          <div className="rounded-xl border-l-4 border-emerald-500 bg-slate-100 p-4">
            <div className="font-semibold text-ink">Overall Sentiment: {overallSentiment.toUpperCase()}</div>
            <div className="text-sm text-slate-600">
              Based on analysis of {summary?.count ?? 0} tweets | Positive: {summary?.positive ?? 0} | Neutral: {summary?.neutral ?? 0} | Negative: {summary?.negative ?? 0}
            </div>
          </div>
        </div>
      )}

      {sectionCard(
        "Sample Tweets by Sentiment",
        <div className="space-y-2">
          {Object.entries(sentimentGroups).map(([sentimentName, tweets]) => (
            <details key={sentimentName} className="rounded-lg border border-slate-200 bg-slate-50/80 p-3">
              <summary className="cursor-pointer text-sm font-semibold capitalize text-slate-700">
                {sentimentName} Sentiment Tweets ({tweets.length} examples)
              </summary>
              <div className="mt-3 space-y-2 text-sm text-slate-700">
                {tweets.map((t, idx) => (
                  <div key={`${sentimentName}-${idx}`} className="rounded bg-slate-50 p-2">
                    <div>{idx + 1}. {t.text}</div>
                    <div className="text-xs text-slate-500">Score: {t.sentiment_score} | Likes: {t.likes || 0} | Replies: {t.replies || 0}</div>
                  </div>
                ))}
              </div>
            </details>
          ))}
        </div>
      )}

      {sectionCard(
        "Tweet Performance Data",
        <div className="max-h-[420px] overflow-auto rounded-xl border border-slate-200 bg-slate-50/80">
          <table className="min-w-full text-left text-sm">
            <thead className="sticky top-0 bg-slate-100 text-slate-700">
              <tr>
                <th className="px-3 py-2">text</th>
                <th className="px-3 py-2">likes</th>
                <th className="px-3 py-2">retweets</th>
                <th className="px-3 py-2">replies</th>
                <th className="px-3 py-2">views</th>
                <th className="px-3 py-2">user</th>
                <th className="px-3 py-2">sentiment</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, idx) => (
                <tr key={idx} className="border-t border-slate-100">
                  <td className="px-3 py-2">{r.text}</td>
                  <td className="px-3 py-2">{r.likes || 0}</td>
                  <td className="px-3 py-2">{r.retweets || 0}</td>
                  <td className="px-3 py-2">{r.replies || 0}</td>
                  <td className="px-3 py-2">{r.views || 0}</td>
                  <td className="px-3 py-2">{r.user || "unknown"}</td>
                  <td className="px-3 py-2 capitalize">{r.sentiment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sectionCard(
        "Performance Charts",
        <div className="grid gap-4 lg:grid-cols-4">
          <div className="h-[280px] rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 text-sm font-semibold text-rose-500">Likes Distribution</div>
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={likesHist}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bucket" hide />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#f87171" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="h-[280px] rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 text-sm font-semibold text-sky">Retweets Distribution</div>
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={retweetsHist}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bucket" hide />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#4ECDC4" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="h-[280px] rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 text-sm font-semibold text-violet-500">Replies Distribution</div>
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={repliesHist}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bucket" hide />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#9D4EDD" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="h-[280px] rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 text-sm font-semibold text-emerald-500">Views Distribution</div>
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={viewsHist}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bucket" hide />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#45B7D1" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {sectionCard(
        "Detailed Performance Analysis",
        <div className="grid gap-4 lg:grid-cols-4">
          <div className="h-[280px] rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 text-sm font-semibold text-slate-700">Tweet Count vs Likes</div>
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={byTweet}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="tweet" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="likes" fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="h-[280px] rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 text-sm font-semibold text-slate-700">Tweet Count vs Retweets</div>
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={byTweet}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="tweet" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="retweets" fill="#1d4ed8" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="h-[280px] rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 text-sm font-semibold text-slate-700">Tweet Count vs Replies</div>
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={byTweet}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="tweet" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="replies" fill="#6d28d9" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="h-[280px] rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 text-sm font-semibold text-slate-700">Tweet Count vs Views</div>
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={byTweet}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="tweet" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="views" fill="#15803d" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {sectionCard(
        "Export Data",
        <div>
          <button
            onClick={() => downloadCsv(rows)}
            className="rounded-lg bg-sky px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
          >
            Download CSV
          </button>
        </div>
      )}
    </div>
  );
}
