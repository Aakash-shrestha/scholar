"use client";

import { api } from "@/lib/api";
import { Paper } from "@/lib/types";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, BookOpen, ExternalLink, Library } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
        text: `Ingested ${data.ingest.length} new · skipped ${data.skipped.length} already known · ${data.total_found} total references found.`,
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
    <div className="flex h-svh flex-col overflow-hidden">
      {/* Breadcrumb */}
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-6 py-3">
        <Link
          href="/papers"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Research Library
        </Link>
        {singlePaper && (
          <>
            <span className="text-muted-foreground/40">/</span>
            <span className="max-w-sm truncate text-sm text-foreground/60">
              {singlePaper.title}
            </span>
          </>
        )}
      </div>

      {/* Body */}
      <div className="flex min-h-0 flex-1">
        {/* ── Left panel ── */}
        <div className="flex w-[360px] shrink-0 flex-col gap-6 overflow-y-auto border-r border-border p-6">
          {!singlePaper ? (
            <div className="space-y-4">
              <div className="flex gap-2">
                <Skeleton className="h-5 w-28" />
                <Skeleton className="h-5 w-12" />
              </div>
              <Skeleton className="h-7 w-full" />
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : (
            <>
              {/* Identifiers */}
              <div className="flex flex-wrap items-center gap-2">
                <a
                  href={`https://arxiv.org/abs/${singlePaper.arxiv_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-mono text-xs text-primary hover:underline"
                >
                  arxiv:{singlePaper.arxiv_id}
                  <ExternalLink className="size-3" />
                </a>
                <Badge variant="secondary" className="font-mono text-xs">
                  {singlePaper.year}
                </Badge>
              </div>

              {/* Title + authors */}
              <div className="space-y-1.5">
                <h1 className="text-xl font-semibold leading-snug tracking-tight">
                  {singlePaper.title}
                </h1>
                <p className="text-sm text-muted-foreground">
                  {singlePaper.short_citation}
                </p>
              </div>

              {/* Abstract */}
              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  Abstract
                </p>
                <div className="border border-border bg-muted/20 p-4">
                  <p className="text-justify text-sm leading-relaxed text-foreground/80">
                    {singlePaper.abstract}
                  </p>
                </div>
              </div>

              {/* Reference ingestion */}
              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  References
                </p>
                <div className="space-y-4 border border-border p-4">
                  <div className="space-y-1">
                    <p className="text-sm font-medium">Ingest Cited Papers</p>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      Crawl this paper&apos;s reference list and add cited works
                      to your knowledge base so you can query across them.
                    </p>
                  </div>
                  <div className="space-y-3">
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">
                        Max papers to ingest
                      </label>
                      <Input
                        type="number"
                        value={limit}
                        min={1}
                        max={10}
                        onChange={(e) => setLimit(Number(e.target.value))}
                        className="w-24 font-mono text-sm"
                      />
                    </div>
                    <Button
                      onClick={ingestReference}
                      disabled={ingesting}
                      variant="outline"
                      className="w-full gap-2"
                    >
                      <Library className="size-3.5" />
                      {ingesting ? "Ingesting…" : "Ingest References"}
                    </Button>
                  </div>
                  {refMessage && (
                    <p
                      className={`text-xs leading-relaxed ${
                        refMessage.ok
                          ? "text-green-600 dark:text-green-400"
                          : "text-destructive"
                      }`}
                    >
                      {refMessage.text}
                    </p>
                  )}
                </div>
              </div>

              {/* Ingested timestamp */}
              <p className="text-xs text-muted-foreground">
                Added to library{" "}
                {new Date(singlePaper.ingested_at).toLocaleDateString(
                  undefined,
                  { year: "numeric", month: "long", day: "numeric" }
                )}
              </p>
            </>
          )}
        </div>

        {/* ── Right panel — PDF viewer ── */}
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <BookOpen className="size-3.5 text-muted-foreground" />
              Full Paper
            </div>
            {singlePaper && (
              <a
                href={`/api/pdf/${singlePaper.arxiv_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                Open in new tab
                <ExternalLink className="size-3" />
              </a>
            )}
          </div>
          <div className="min-h-0 flex-1 bg-muted/10">
            <iframe
              src={`/api/pdf/${arxiv_id}`}
              className="h-full w-full"
              allow="fullscreen"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
