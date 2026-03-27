import { useState } from "react";
import AgentPanel from "./components/AgentPanel";
import ClassicResultView from "./components/ClassicResultView";
import { analyzeHandle, analyzeUrls, askAgent, askAgentic } from "./lib/api";

export default function App() {
  const [summary, setSummary] = useState({
    count: 0,
    positive: 0,
    negative: 0,
    engagement_rate: 0,
    top_keywords: [],
    total_likes: 0,
    total_retweets: 0,
    total_replies: 0,
    total_views: 0,
  });
  const [rows, setRows] = useState([]);
  const [trends, setTrends] = useState({ week: [], month: [], by_tweet: [] });
  const [agentLoading, setAgentLoading] = useState(false);
  const [urlLoading, setUrlLoading] = useState(false);
  const [error, setError] = useState("");
  const [inputMethod, setInputMethod] = useState("single");
  const [singleUrl, setSingleUrl] = useState("");
  const [multipleUrls, setMultipleUrls] = useState("");
  const [handle, setHandle] = useState("");
  const [tweetCount, setTweetCount] = useState(10);

  async function handleAgentAsk(question, mode = "agentic") {
    try {
      setAgentLoading(true);
      if (mode === "classic") {
        const response = await askAgent(question, rows);
        return response.answer;
      }
      return await askAgentic(question, rows);
    } catch (err) {
      return err.message || "Agent failed to respond.";
    } finally {
      setAgentLoading(false);
    }
  }

  async function handleAnalyzeUrls() {
    try {
      setUrlLoading(true);
      let data;

      if (inputMethod === "handle") {
        if (!handle.trim()) {
          setError("Please enter a Twitter handle.");
          setUrlLoading(false);
          return;
        }
        data = await analyzeHandle(handle.trim(), tweetCount);
      } else {
        const urlText = inputMethod === "single" ? singleUrl : multipleUrls;
        const urls = urlText
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean)
          .slice(0, tweetCount);

        if (!urls.length) {
          setError("Please enter at least one Twitter/X status URL.");
          setUrlLoading(false);
          return;
        }
        data = await analyzeUrls(urls, tweetCount);
      }

      setSummary(data.summary);
      setRows(data.rows);
      setTrends(data.trends ?? { week: [], month: [], by_tweet: [] });
      setError("");
    } catch (err) {
      setError(err.message || "Unable to analyze URLs.");
    } finally {
      setUrlLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8 animate-rise">
        <h1 className="text-4xl font-extrabold tracking-tight text-ink">AI Twitter Analytics </h1>
        <p className="mt-2 max-w-3xl text-slate-600">
          Real Twitter/X URL analysis with Python NLP backend and AI-powered analytics assistant.
        </p>
      </header>

      {error ? <div className="mb-4 rounded-xl bg-rose-100 p-3 text-rose-700">{error}</div> : null}

      <section className="mt-6 card animate-rise">
        <h3 className="text-lg font-semibold text-ink">Input Method</h3>
        <p className="mt-1 text-sm text-slate-500">Choose single URL, multiple URLs, or Twitter handle.</p>

        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="radio" name="inputMethod" checked={inputMethod === "single"} onChange={() => setInputMethod("single")} />
            Single URL
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="radio" name="inputMethod" checked={inputMethod === "multiple"} onChange={() => setInputMethod("multiple")} />
            Multiple URLs
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="radio" name="inputMethod" checked={inputMethod === "handle"} onChange={() => setInputMethod("handle")} />
            Twitter Handle
          </label>
        </div>

        {inputMethod === "single" ? (
          <input
            className="mt-3 w-full rounded-xl border border-slate-200 p-3 outline-none focus:border-sky"
            placeholder="https://x.com/username/status/1234567890"
            value={singleUrl}
            onChange={(e) => setSingleUrl(e.target.value)}
          />
        ) : null}

        {inputMethod === "multiple" ? (
          <textarea
            className="mt-3 h-28 w-full rounded-xl border border-slate-200 p-3 outline-none focus:border-sky"
            placeholder="Paste one status URL per line"
            value={multipleUrls}
            onChange={(e) => setMultipleUrls(e.target.value)}
          />
        ) : null}

        {inputMethod === "handle" ? (
          <input
            className="mt-3 w-full rounded-xl border border-slate-200 p-3 outline-none focus:border-sky"
            placeholder="Enter handle without @ (example: elonmusk)"
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
          />
        ) : null}

        <div className="mt-4 max-w-xs">
          <label className="mb-1 block text-sm font-medium text-slate-700">Number of tweets to analyze: {tweetCount}</label>
          <input
            type="range"
            min="1"
            max="50"
            value={tweetCount}
            onChange={(e) => setTweetCount(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <button
          onClick={handleAnalyzeUrls}
          disabled={urlLoading}
          className="mt-3 rounded-xl bg-ink px-4 py-2 text-white transition hover:opacity-90 disabled:opacity-60"
        >
          {urlLoading ? "Analyzing..." : "Scrape & Analyze Data"}
        </button>
      </section>

      <ClassicResultView rows={rows} summary={summary} trends={trends} />

      <section className="mt-6 card">
        <h3 className="text-xl font-bold text-ink">AI Agent Assistant</h3>
        <p className="mt-1 text-sm text-slate-500">Ask strategy questions from analyzed rows.</p>
        <AgentPanel onAsk={handleAgentAsk} loading={agentLoading} />
      </section>
    </main>
  );
}
