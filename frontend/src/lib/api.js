const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function analyzeText(texts) {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "text", texts }),
  });
  if (!res.ok) throw new Error("Failed to analyze texts");
  return res.json();
}

export async function analyzeUrls(urls, count = 10) {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "url", urls, count }),
  });
  if (!res.ok) throw new Error("Failed to analyze URLs");
  return res.json();
}

export async function analyzeHandle(handle, count = 10) {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "handle", handle, count }),
  });
  if (!res.ok) throw new Error("Failed to analyze handle");
  return res.json();
}

export async function analyzeDataset(count = 10, handle = "") {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "dataset", count, handle }),
  });
  if (!res.ok) throw new Error("Failed to analyze project dataset");
  return res.json();
}

export async function analyzeDownloadDataset(count = 10, handle = "") {
  const form = new FormData();
  form.append("count", String(count));
  form.append("handle", handle);

  const res = await fetch(`${API_BASE}/api/analyze-download`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    let detail = "Failed to analyze Downloads dataset";
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // Keep default message when body is not JSON.
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function analyzeFile(file, count = 10) {
  const form = new FormData();
  form.append("file", file);
  form.append("count", String(count));

  const res = await fetch(`${API_BASE}/api/analyze-file`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    let detail = "Failed to analyze file";
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // Keep default message when body is not JSON.
    }
    throw new Error(detail);
  }
  return res.json();
 }

export async function askAgent(question, context) {
  const res = await fetch(`${API_BASE}/api/agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, context }),
  });
  if (!res.ok) throw new Error("Failed to get agent response");
  return res.json();
}

export async function askAgentic(question, context) {
  const res = await fetch(`${API_BASE}/api/agentic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, context }),
  });
  if (!res.ok) throw new Error("Failed to get agentic response");
  return res.json();
}
