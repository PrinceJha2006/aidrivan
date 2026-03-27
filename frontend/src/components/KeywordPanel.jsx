export default function KeywordPanel({ keywords = [] }) {
  return (
    <div className="card animate-rise">
      <h3 className="text-lg font-semibold text-ink">Top NLP Keywords</h3>
      <div className="mt-4 flex flex-wrap gap-2">
        {keywords.length ? (
          keywords.map((kw) => (
            <span key={kw} className="pill bg-ink text-white">
              {kw}
            </span>
          ))
        ) : (
          <span className="text-sm text-slate-500">No keyword data available.</span>
        )}
      </div>
    </div>
  );
}
