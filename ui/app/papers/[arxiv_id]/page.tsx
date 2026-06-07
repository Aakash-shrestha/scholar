"use client";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { Paper } from "@/lib/types";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function SinglePaper() {
  const [singlePaper, setSinglePaper] = useState<Paper | null>(null);
  const [limit, setLimit] = useState<number>(3);
  const [ingesting, setIngesting] = useState(false);
  const [refMessage, setRefMessage] = useState<{
    ok: boolean;
    text: string;
  } | null>(null);
  const { arxiv_id } = useParams();

  useEffect(() => {
    api.getPaper(arxiv_id as string).then(setSinglePaper);
  }, [arxiv_id]);

  async function ingestReference() {
    setRefMessage(null);
    setIngesting(true);
    try {
      const data = await api.ingestRefs(arxiv_id as string, limit);
      setRefMessage({
        ok: true,
        text: `Ingested ${data.ingest.length}, skipped ${data.skipped.length} of ${data.total_found} found.`,
      });
    } catch (e: unknown) {
      setRefMessage({
        ok: false,
        text: e instanceof Error ? e.message : "Ingest failed.",
      });
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div className="flex flex-col ml-8 gap-4 justify-center w-[95%]">
      <div className="flex flex-col gap-2">
        {singlePaper ? (
          <div className="flex flex-col gap-4">
            <h1 className="text-2xl font-bold">{singlePaper.title}</h1>
            <p className="text-sm text-gray-600">
              {singlePaper.short_citation}
            </p>
            <p>{singlePaper.abstract}</p>
          </div>
        ) : (
          <p>Loading paper...</p>
        )}
      </div>

      <div className="flex flex-col gap-2 w-1/2">
        <div className="flex gap-4 items-center">
          <input
            type="number"
            value={limit}
            min={1}
            max={20}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="border px-3 py-2 text-sm w-20"
          />
          <Button
            onClick={ingestReference}
            disabled={!(arxiv_id as string).trim() || ingesting}
          >
            {ingesting ? "Ingesting…" : "Ingest References"}
          </Button>
        </div>
        {refMessage && (
          <p
            className={`text-sm ${refMessage.ok ? "text-green-600" : "text-red-600"}`}
          >
            {refMessage.text}
          </p>
        )}
      </div>
    </div>
  );
}
