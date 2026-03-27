import { useState } from "react";

export default function AgentPanel({ onAsk, loading }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [mode, setMode] = useState("agentic");
  const [plan, setPlan] = useState([]);
  const [steps, setSteps] = useState([]);
  const [confidence, setConfidence] = useState("");

  async function handleAsk(e) {
    e.preventDefault();
    const response = await onAsk(question, mode);
    if (typeof response === "string") {
      setAnswer(response || "No response");
      setPlan([]);
      setSteps([]);
      setConfidence("");
      return;
    }

    setAnswer(response?.answer || "No response");
    setPlan(response?.plan || []);
    setSteps(response?.steps || []);
    setConfidence(response?.confidence || "");
  }

  return (
    <div className="card animate-rise">
      <h3 className="text-lg font-semibold text-ink">AI Agent Assistant</h3>
      <p className="mt-1 text-sm text-slate-500">Ask strategy questions from analyzed Twitter data using classic or agentic mode.</p>

      <div className="mt-3 inline-flex rounded-xl border border-slate-200 p-1 text-xs">
        <button
          type="button"
          onClick={() => setMode("agentic")}
          className={`rounded-lg px-3 py-1 ${mode === "agentic" ? "bg-ink text-white" : "text-slate-600"}`}
        >
          Agentic
        </button>
        <button
          type="button"
          onClick={() => setMode("classic")}
          className={`rounded-lg px-3 py-1 ${mode === "classic" ? "bg-ink text-white" : "text-slate-600"}`}
        >
          Classic
        </button>
      </div>

      <form onSubmit={handleAsk} className="mt-4 flex gap-2">
        <input
          className="w-full rounded-xl border border-slate-200 px-4 py-2 outline-none focus:border-sky"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask after analyzing links..."
        />
        <button
          disabled={loading}
          className="rounded-xl bg-ink px-4 py-2 text-white transition hover:opacity-90 disabled:opacity-60"
        >
          {loading ? "Thinking" : "Ask"}
        </button>
      </form>

      {confidence ? (
        <div className="mt-3 text-xs text-slate-500">Confidence: <span className="font-semibold text-slate-700">{confidence}</span></div>
      ) : null}

      {answer ? <div className="mt-4 rounded-xl bg-slate-100 p-3 text-sm text-slate-700">{answer}</div> : null}

      {plan.length ? (
        <div className="mt-4 rounded-xl border border-slate-200 p-3 text-sm text-slate-700">
          <div className="font-semibold text-ink">Plan</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {plan.map((item) => (
              <span key={item} className="rounded-full bg-slate-100 px-2 py-1 text-xs">
                {item}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {steps.length ? (
        <div className="mt-3 rounded-xl border border-slate-200 p-3 text-sm text-slate-700">
          <div className="font-semibold text-ink">Execution Trace</div>
          <div className="mt-2 space-y-1">
            {steps.map((item, idx) => (
              <div key={`${item.step}-${idx}`} className="text-xs">
                {idx + 1}. {item.step} - {item.observation}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
