"use client";

import { api } from "@/lib/api";
import { Paper } from "@/lib/types";
import { useState, useEffect } from "react";
import Link from "next/link";
import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";

export default function Papers() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [arxivId, setArxivId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [ingestMessage, setIngestMessage] = useState<{
    ok: boolean;
    text: string;
  } | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

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
      setIngestMessage({ ok: true, text: `"${data.title}" ingested successfully.` });
    } catch (e: unknown) {
      setIngestMessage({
        ok: false,
        text: e instanceof Error ? e.message : "Ingest failed.",
      });
    }
  }

  function toggleRow(id: string) {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        Loading papers...
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto w-full">
      {/* Page header */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Research Library</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Browse and query your ingested papers
          </p>
        </div>
        <div className="flex flex-col gap-1.5 items-end shrink-0">
          <p className="text-xs font-medium text-muted-foreground">Add from arXiv</p>
          <div className="flex items-center gap-2">
            <Input
              type="text"
              value={arxivId}
              onChange={(e) => {
                setArxivId(e.target.value);
                setIngestMessage(null);
              }}
              onKeyDown={(e) => e.key === "Enter" && arxivId.trim() && handleIngest()}
              placeholder="e.g. 2301.00001"
              className="w-52"
            />
            <Button onClick={handleIngest} disabled={!arxivId.trim()}>
              Add Paper
            </Button>
          </div>
          {ingestMessage && (
            <p
              className={`text-xs ${
                ingestMessage.ok ? "text-green-600 dark:text-green-400" : "text-destructive"
              }`}
            >
              {ingestMessage.text}
            </p>
          )}
        </div>
      </div>

      {/* Table */}
      {papers.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No papers ingested yet. Enter an arXiv ID above to get started.
        </p>
      ) : (
        <>
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-muted/80 backdrop-blur-sm">
                <TableRow className="hover:bg-transparent border-b border-border">
                  <TableHead className="w-[42%] pl-4">Title</TableHead>
                  <TableHead className="w-[28%]">Citation</TableHead>
                  <TableHead className="w-[7%]">Year</TableHead>
                  <TableHead className="w-[13%]">arXiv ID</TableHead>
                  <TableHead className="w-[9%]">Ingested</TableHead>
                  <TableHead className="w-8" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {papers.map((paper) => {
                  const isExpanded = expandedRows.has(paper.arxiv_id);
                  return (
                    <React.Fragment key={paper.arxiv_id}>
                      <TableRow
                        className="cursor-pointer group"
                        onClick={() => toggleRow(paper.arxiv_id)}
                      >
                        <TableCell className="whitespace-normal pl-4 py-3 align-top">
                          <Link
                            href={`/papers/${paper.arxiv_id}`}
                            className="font-medium text-foreground hover:text-primary hover:underline leading-snug line-clamp-2"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {paper.title}
                          </Link>
                        </TableCell>
                        <TableCell className="whitespace-normal py-3 align-top text-muted-foreground text-xs leading-relaxed">
                          {paper.short_citation}
                        </TableCell>
                        <TableCell className="py-3 align-top">
                          <Badge variant="secondary" className="font-mono text-xs">
                            {paper.year}
                          </Badge>
                        </TableCell>
                        <TableCell className="py-3 align-top">
                          <a
                            href={`https://arxiv.org/abs/${paper.arxiv_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-mono text-xs text-primary hover:underline inline-flex items-center gap-1"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {paper.arxiv_id}
                            <ExternalLink className="size-3 shrink-0" />
                          </a>
                        </TableCell>
                        <TableCell className="py-3 align-top text-muted-foreground text-xs">
                          {new Date(paper.ingested_at).toLocaleDateString(undefined, {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}
                        </TableCell>
                        <TableCell className="py-3 align-top pr-3">
                          {isExpanded ? (
                            <ChevronUp className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                          ) : (
                            <ChevronDown className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                          )}
                        </TableCell>
                      </TableRow>
                      {isExpanded && (
                        <TableRow className="bg-muted/30 hover:bg-muted/30">
                          <TableCell
                            colSpan={6}
                            className="!whitespace-normal break-words px-6 py-4 align-top"
                          >
                            <p className="text-sm text-muted-foreground leading-relaxed w-full text-justify">
                              <span className="font-semibold text-foreground mr-2">Abstract</span>
                              {paper.abstract}
                            </p>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-muted-foreground">
            {papers.length} paper{papers.length !== 1 ? "s" : ""} &middot; Click any row to expand the abstract
          </p>
        </>
      )}
    </div>
  );
}
