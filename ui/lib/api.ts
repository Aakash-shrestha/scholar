import type { HistoryItem, StreamEvent } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const HEADERS = {
  "Content-Type": "application/json",
  "ngrok-skip-browser-warning": "true",
};

async function parseResponse(r: Response) {
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail ?? `Request failed (${r.status})`);
  return data;
}

export const api = {
  getPapers: () =>
    fetch(`${API_BASE}/papers`, { headers: HEADERS }).then(parseResponse),

  getPaper: (arxivId: string) =>
    fetch(`${API_BASE}/papers/${arxivId}`, { headers: HEADERS }).then(
      parseResponse,
    ),

  ingestPaper: (arxivId: string) =>
    fetch(`${API_BASE}/papers`, {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({ arxiv_id: arxivId }),
    }).then(parseResponse),

  ask: (question: string) =>
    fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({ question }),
    }).then(parseResponse),
  delete: (arxiv_id: string) =>
    fetch(`${API_BASE}/papers/${arxiv_id}`, {
      method: "DELETE",
      headers: HEADERS,
    }).then(async (r) => {
      if (!r.ok) {
        const data = await r.json();
        throw new Error(data.detail ?? `Request failed (${r.status})`);
      }
    }),

  getSuggestions: (): Promise<string[]> =>
    fetch(`${API_BASE}/suggestions`, { headers: HEADERS }).then(parseResponse),

  getGraph: () =>
    fetch(`${API_BASE}/graph`, { headers: HEADERS }).then(parseResponse),

  ingestRefs: (arxiv_id: string, limit: number) =>
    fetch(`${API_BASE}/papers/${arxiv_id}/refs`, {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({ limit }),
    }).then(parseResponse),

  getReferences: (arxiv_id: string) =>
    fetch(`${API_BASE}/papers/${arxiv_id}/references`, {
      headers: HEADERS,
    }).then(parseResponse),

  addCitation: (sourceId: string, citedId: string) =>
    fetch(`${API_BASE}/papers/${sourceId}/citations/${citedId}`, {
      method: "POST",
      headers: HEADERS,
    }).then(async (r) => {
      if (!r.ok) {
        const data = await r.json();
        throw new Error(data.detail ?? `Request failed (${r.status})`);
      }
    }),

  async *askStream(
    question: string,
    paperIds?: string[],
    signal?: AbortSignal,
    history?: HistoryItem[],
  ): AsyncGenerator<StreamEvent> {
    const res = await fetch(`${API_BASE}/ask/stream`, {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({ question, paper_ids: paperIds, history: history ?? [] }),
      signal,
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail ?? `Request failed (${res.status})`);
    }

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop()!;

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        try {
          yield JSON.parse(payload) as StreamEvent;
        } catch {}
      }
    }
  },
};
