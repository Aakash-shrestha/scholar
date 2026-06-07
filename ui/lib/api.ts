const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function parseResponse(r: Response) {
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail ?? `Request failed (${r.status})`);
  return data;
}

export const api = {
  getPapers: () => fetch(`${API_BASE}/papers`).then(parseResponse),
  getPaper: (arxivId: string) =>
    fetch(`${API_BASE}/papers/${arxivId}`).then(parseResponse),
  ingestPaper: (arxivId: string) =>
    fetch(`${API_BASE}/papers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ arxiv_id: arxivId }),
    }).then(parseResponse),
  ask: (question: string) =>
    fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }).then(parseResponse),
  ingestRefs: (arxiv_id: string, limit: number) =>
    fetch(`${API_BASE}/papers/${arxiv_id}/refs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit }),
    }).then(parseResponse),
};
