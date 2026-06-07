"use client";

import { api } from "@/lib/api";
import { Paper } from "@/lib/types";
import { useState, useEffect } from "react";
import Link from "next/link";

export default function Papers() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [arxivId, setArxivId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [ingestMessage, setIngestMessage] = useState<{
    ok: boolean;
    text: string;
  } | null>(null);

  useEffect(() => {
    api.getPapers().then((data) => {
      setPapers(data);
      setLoading(false);
    });
  }, []);

  async function handleIngest() {
    setIngestMessage(null);
    try {
      const data = await api.ingestPaper(arxivId);
      setPapers((prev) => [...prev, data]);
      setArxivId("");
      setIngestMessage({
        ok: true,
        text: `"${data.title}" ingested successfully.`,
      });
    } catch (e: unknown) {
      setIngestMessage({
        ok: false,
        text: e instanceof Error ? e.message : "Ingest failed.",
      });
    }
  }

  if (loading) return <p>Loading papers...</p>;

  return (
    <div className="flex flex-col">
      <h1 className="text-2xl font-bold mb-4">Papers</h1>
      <div className="flex gap-2 mb-6 ml-6 w-full items-center justify-start">
        <div className="flex gap-2 w-1/2">
          <input
            type="text"
            value={arxivId}
            onChange={(e) => {
              setArxivId(e.target.value);
              setIngestMessage(null);
            }}
            placeholder="arXiv ID (e.g. 2301.00001)"
            className="border px-3 py-2 text-sm flex-1"
          />
          <button
            onClick={handleIngest}
            disabled={!arxivId.trim()}
            className="px-4 py-2 text-sm bg-black text-white disabled:opacity-40 cursor-pointer"
          >
            Ingest
          </button>
          <div></div>
        </div>
        {ingestMessage && (
          <p
            className={`text-sm ml-2 ${ingestMessage.ok ? "text-green-600" : "text-red-600"}`}
          >
            {ingestMessage.text}
          </p>
        )}
      </div>
      {papers.length === 0 ? (
        <p>No papers found.</p>
      ) : (
        <ul className="space-y-4">
          {papers.map((paper) => (
            <li key={paper.arxiv_id} className="border p-4 rounded">
              <Link href={`/papers/${paper.arxiv_id}`}>
                <h2 className="text-xl font-semibold hover:underline">{paper.title}</h2>
              </Link>
              <p className="text-sm text-gray-600">{paper.short_citation}</p>
              <p className="mt-2">{paper.abstract}</p>
              <p className="mt-2 text-sm text-gray-500">
                Published in {paper.year}, ingested at{" "}
                {new Date(paper.ingested_at).toLocaleString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
