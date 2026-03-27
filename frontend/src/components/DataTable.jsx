export default function DataTable({ rows = [] }) {
  return (
    <div className="card animate-rise">
      <h3 className="text-lg font-semibold text-ink">Analyzed Rows</h3>
      <div className="mt-4 max-h-80 overflow-auto rounded-xl border border-slate-100">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="px-3 py-2">URL</th>
              <th className="px-3 py-2">Text</th>
              <th className="px-3 py-2">Sentiment</th>
              <th className="px-3 py-2">Score</th>
              <th className="px-3 py-2">Likes</th>
              <th className="px-3 py-2">Retweets</th>
              <th className="px-3 py-2">Replies</th>
              <th className="px-3 py-2">Views</th>
              <th className="px-3 py-2">Created At</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 25).map((row, idx) => (
              <tr key={`${row.text}-${idx}`} className="border-t border-slate-100">
                <td className="px-3 py-2 text-sky">
                  <a href={row.source_url} target="_blank" rel="noreferrer" className="underline">
                    Open
                  </a>
                </td>
                <td className="px-3 py-2 text-slate-700">{row.text}</td>
                <td className="px-3 py-2 font-medium capitalize">{row.sentiment}</td>
                <td className="px-3 py-2">{row.sentiment_score}</td>
                <td className="px-3 py-2">{row.likes ?? 0}</td>
                <td className="px-3 py-2">{row.retweets ?? 0}</td>
                <td className="px-3 py-2">{row.replies ?? 0}</td>
                <td className="px-3 py-2">{row.views ?? 0}</td>
                <td className="px-3 py-2">{row.created_at ? new Date(row.created_at).toLocaleString() : "NA"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
