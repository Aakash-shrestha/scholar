"use client";

import { api } from "@/lib/api";
import { Paper, ReferenceType } from "@/lib/types";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  BookOpen,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Library,
} from "lucide-react";
import { toast } from "sonner";

export default function SinglePaper() {
  const [singlePaper, setSinglePaper] = useState<Paper | null>(null);
  const [limit, setLimit] = useState<number>(3);
  const [ingesting, setIngesting] = useState(false);
  const [showRefs, setShowRefs] = useState(false);
  const [refs, setRefs] = useState<ReferenceType[]>([]);
  const [refsLoading, setRefsLoading] = useState(false);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const { arxiv_id } = useParams();

  useEffect(() => {
    api.getPaper(arxiv_id as string).then(setSinglePaper);
  }, [arxiv_id]);

  async function ingestReference() {
    setIngesting(true);
    const toastId = toast.loading("Ingesting references…");
    try {
      const data = await api.ingestRefs(arxiv_id as string, limit);
      toast.success(
        `Ingested ${data.ingest.length} new · skipped ${data.skipped.length} already known · ${data.total_found} total found.`,
        { id: toastId },
      );
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Ingest failed.", {
        id: toastId,
      });
    } finally {
      setIngesting(false);
    }
  }

  async function loadReferences() {
    if (showRefs) {
      setShowRefs(false);
      return;
    }
    setShowRefs(true);
    if (refs.length > 0) return; // already loaded
    setRefsLoading(true);
    try {
      const data = await api.getReferences(arxiv_id as string);
      setRefs(data);
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : "Failed to load references.",
      );
      setShowRefs(false);
    } finally {
      setRefsLoading(false);
    }
  }

  function handleRefIngested(ingestedId: string) {
    setRefs((prev) =>
      prev.map((r) =>
        r.arxiv_id === ingestedId ? { ...r, is_ingested: true } : r,
      ),
    );
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
        <div className="flex w-120 shrink-0 flex-col gap-6 overflow-y-auto border-r border-border p-6">
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
                </div>

                {/* Reference list */}
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-between text-xs"
                  onClick={loadReferences}
                >
                  <span>
                    {showRefs ? "Hide reference list" : "View reference list"}
                  </span>
                  {showRefs ? (
                    <ChevronUp className="size-3.5" />
                  ) : (
                    <ChevronDown className="size-3.5" />
                  )}
                </Button>

                {showRefs && (
                  <div className="border border-border">
                    {refsLoading ? (
                      <div className="space-y-2 p-3">
                        {[...Array(4)].map((_, i) => (
                          <Skeleton key={i} className="h-8 w-full" />
                        ))}
                        <p className="text-[10px] text-muted-foreground text-center pt-1">
                          Resolving arXiv IDs — first load may take a moment…
                        </p>
                      </div>
                    ) : refs.length === 0 ? (
                      <p className="p-3 text-xs text-muted-foreground">
                        No arXiv references found.
                      </p>
                    ) : (
                      <div>
                        <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
                          <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                            Title
                          </span>
                          <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                            {refs.filter((r) => r.is_ingested).length}/
                            {refs.length} ingested
                          </span>
                        </div>
                        {refs.map((ref) => (
                          <RefRow
                            key={ref.title}
                            item={ref}
                            onIngested={handleRefIngested}
                            onPreview={setPreviewId}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Ingested timestamp */}
              <p className="text-xs text-muted-foreground">
                Added to library{" "}
                {new Date(singlePaper.ingested_at).toLocaleDateString(
                  undefined,
                  { year: "numeric", month: "long", day: "numeric" },
                )}
              </p>
            </>
          )}
        </div>

        {/* ── Right panel — PDF viewer ── */}
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-3">
            <div className="flex min-w-0 items-center gap-2 text-sm font-medium">
              <BookOpen className="size-3.5 shrink-0 text-muted-foreground" />
              {previewId ? (
                <span className="truncate text-sm">
                  {refs.find((r) => r.arxiv_id === previewId)?.title ??
                    previewId}
                </span>
              ) : (
                "Full Paper"
              )}
            </div>
            <div className="flex shrink-0 items-center gap-3">
              {previewId && (
                <button
                  onClick={() => setPreviewId(null)}
                  className="inline-flex items-center gap-1.5 text-xs text-primary transition-colors hover:text-primary/80"
                >
                  <ArrowLeft className="size-3" />
                  Back to original Paper:{" "}
                  <span className="font-bold">{singlePaper?.title}</span>
                </button>
              )}
              {singlePaper && (
                <a
                  href={`/api/pdf/${previewId ?? singlePaper.arxiv_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  Open in new tab
                  <ExternalLink className="size-3" />
                </a>
              )}
            </div>
          </div>
          <div className="min-h-0 flex-1 bg-muted/10">
            <iframe
              src={`/api/pdf/${previewId ?? arxiv_id}`}
              className="h-full w-full"
              allow="fullscreen"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function RefRow({
  item,
  onIngested,
  onPreview,
}: {
  item: ReferenceType;
  onIngested: (id: string) => void;
  onPreview: (id: string) => void;
}) {
  const [ingesting, setIngesting] = useState(false);
  const router = useRouter();

  async function handleIngest(e: React.MouseEvent) {
    e.stopPropagation();
    setIngesting(true);
    const toastId = toast.loading(`Ingesting ${item.arxiv_id}…`);
    try {
      await api.ingestPaper(item.arxiv_id);
      toast.success("Ingested successfully.", { id: toastId });
      onIngested(item.arxiv_id);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed.", {
        id: toastId,
      });
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div
      onClick={() =>
        item.is_ingested && router.push(`/papers/${item.arxiv_id}`)
      }
      className={`flex items-center gap-2 border-b border-border px-3 py-2.5 last:border-0 ${
        item.is_ingested ? "cursor-pointer hover:bg-muted/40" : "cursor-default"
      }`}
    >
      <div className="min-w-0 flex-1">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onPreview(item.arxiv_id);
          }}
          className="line-clamp-2 text-left text-xs leading-relaxed hover:underline hover:text-foreground transition-colors"
        >
          {item.title}
        </button>
        <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
          {item.arxiv_id}
        </p>
      </div>
      {item.is_ingested ? (
        <Badge
          variant="secondary"
          className="shrink-0 text-[10px] text-green-600 dark:text-green-400"
        >
          Ingested
        </Badge>
      ) : (
        <Button
          size="sm"
          variant="outline"
          onClick={handleIngest}
          disabled={ingesting}
          className="shrink-0 h-6 text-[10px] px-2"
        >
          {ingesting ? "…" : "Ingest"}
        </Button>
      )}
    </div>
  );
}
