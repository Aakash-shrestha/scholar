"use client";

import { useState, useRef, useEffect, FormEvent, KeyboardEvent, ChangeEvent } from "react";
import { ArrowUp, Clock, FileText, Square, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { AskResponse, Paper, RetrievedPaper } from "@/lib/types";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { useChatHistory, type Message } from "@/lib/chat-context";
import { Skeleton } from "@/components/ui/skeleton";

const TYPE_META: Record<
  string,
  { label: string; bg: string; text: string; border: string }
> = {
  factual: {
    label: "Factual",
    bg: "#95C8F3",
    text: "#1a4c7c",
    border: "#75b2e6",
  },
  definitional: {
    label: "Definitional",
    bg: "#AEB5FF",
    text: "#2e32a6",
    border: "#9099f5",
  },
  synthesis: {
    label: "Synthesis",
    bg: "#FFDC74",
    text: "#7c5600",
    border: "#f0c640",
  },
  comparison: {
    label: "Comparison",
    bg: "#7DE198",
    text: "#155a30",
    border: "#5acc7c",
  },
  negative: {
    label: "Negative",
    bg: "#FF8C87",
    text: "#9a1c1c",
    border: "#f06060",
  },
};

type SuggestionItem = { text: string };

const DOT_COLORS = ["#95C8F3", "#DEACF9", "#7DE198"];

export default function Home() {
  const { messages, setMessages } = useChatHistory();
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [streamingAnswer, setStreamingAnswer] = useState<string>("");

  // @ mention state
  const [allPapers, setAllPapers] = useState<Paper[]>([]);
  const [pinnedPapers, setPinnedPapers] = useState<Paper[]>([]);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionIndex, setMentionIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Dynamic suggestions state
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(true);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingQuestion]);

  useEffect(() => {
    api.getPapers().then(setAllPapers).catch(() => {});
  }, []);

  useEffect(() => {
    api.getSuggestions()
      .then((qs) => setSuggestions(qs.map((text) => ({ text }))))
      .catch(() => {})
      .finally(() => setSuggestionsLoading(false));
  }, []);

  // Papers matching the current @ query, excluding already-pinned ones
  const mentionResults = mentionQuery === null
    ? []
    : allPapers
        .filter((p) => !pinnedPapers.some((pp) => pp.arxiv_id === p.arxiv_id))
        .filter(
          (p) =>
            mentionQuery === "" ||
            p.title.toLowerCase().includes(mentionQuery.toLowerCase()) ||
            p.arxiv_id.includes(mentionQuery),
        )
        .slice(0, 6);

  function handleInputChange(e: ChangeEvent<HTMLTextAreaElement>) {
    const value = e.target.value;
    setInput(value);

    // Detect an @ that hasn't been closed by a space yet
    const cursor = e.target.selectionStart ?? value.length;
    const textUpToCursor = value.slice(0, cursor);
    const match = textUpToCursor.match(/@(\w*)$/);
    if (match) {
      setMentionQuery(match[1]);
      setMentionIndex(0);
    } else {
      setMentionQuery(null);
    }
  }

  function selectMention(paper: Paper) {
    // Strip the @query text that triggered the popup, then add the paper chip
    setInput((prev) => prev.replace(/@\w*$/, "").trimEnd());
    setPinnedPapers((prev) => [...prev, paper]);
    setMentionQuery(null);
    setMentionIndex(0);
    textareaRef.current?.focus();
  }

  function removePinned(arxivId: string) {
    setPinnedPapers((prev) => prev.filter((p) => p.arxiv_id !== arxivId));
  }

  function handleStop() {
    abortRef.current?.abort();
  }

  async function submit() {
    const question = input.trim();
    if (!question || loading) return;

    const paperIds = pinnedPapers.length > 0
      ? pinnedPapers.map((p) => p.arxiv_id)
      : undefined;
    const savedPinned = [...pinnedPapers];

    // Send the last 5 turns as context — enough for coherent follow-ups without bloating the prompt
    const history = messages
      .slice(-5)
      .map((m) => ({ question: m.question, answer: m.response.answer }));

    const controller = new AbortController();
    abortRef.current = controller;

    setInput("");
    setPinnedPapers([]);
    setMentionQuery(null);
    setError(null);
    setLoading(true);
    setPendingQuestion(question);
    setStreamingAnswer("");

    try {
      let fullAnswer = "";

      for await (const event of api.askStream(question, paperIds, controller.signal, history)) {
        if (event.type === "token") {
          fullAnswer += event.token;
          setStreamingAnswer(fullAnswer);
        } else if (event.type === "done") {
          const response: AskResponse = {
            question,
            answer: fullAnswer,
            question_type: event.question_type,
            retrieved_papers: event.retrieved_papers ?? [],
            latency: event.latency,
          };
          setMessages((prev) => [
            ...prev,
            { id: Date.now(), question, pinnedPapers: savedPinned, response },
          ]);
          setStreamingAnswer("");
        }
      }
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") {
        // User stopped the stream — commit whatever was generated so far
        if (streamingAnswer) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now(),
              question,
              pinnedPapers: savedPinned,
              response: {
                question,
                answer: streamingAnswer,
                question_type: "factual",
                retrieved_papers: [],
                latency: 0,
              },
            },
          ]);
        }
        setStreamingAnswer("");
      } else {
        setError(e instanceof Error ? e.message : "Request failed.");
      }
    } finally {
      abortRef.current = null;
      setLoading(false);
      setPendingQuestion(null);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submit();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Intercept keyboard events when the mention popup is open
    if (mentionQuery !== null && mentionResults.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setMentionIndex((i) => Math.min(i + 1, mentionResults.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setMentionIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        selectMention(mentionResults[mentionIndex]);
        return;
      }
      if (e.key === "Escape") {
        setMentionQuery(null);
        return;
      }
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const hasContent = messages.length > 0 || pendingQuestion !== null;

  return (
    <div className="flex flex-col h-[calc(100vh-var(--navbar-height,73px))] bg-background text-foreground">
      {/* Feed */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-8 py-10">
          {!hasContent ? (
            <EmptyState
              onSuggest={setInput}
              suggestions={suggestions}
              loading={suggestionsLoading}
            />
          ) : (
            <div className="space-y-10">
              {messages.map((msg, i) => (
                <div key={msg.id}>
                  {i > 0 && <Separator className="mb-10" />}
                  <MessageBlock message={msg} />
                </div>
              ))}

              {/* Pending question + loading */}
              {pendingQuestion && (
                <div>
                  {messages.length > 0 && <Separator className="mb-10" />}
                  <div className="space-y-5">
                    <div className="flex items-start gap-3">
                      ...
                      <p className="text-lg font-semibold">{pendingQuestion}</p>
                    </div>

                    {streamingAnswer ? (
                      <div className="ml-8 prose prose-sm prose-gray ...">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm, remarkMath]}
                          rehypePlugins={[rehypeKatex]}
                        >
                          {streamingAnswer}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <LoadingBlock />
                    )}
                  </div>
                </div>
              )}

              {error && (
                <p className="text-xs text-destructive ml-8 mt-2">{error}</p>
              )}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input bar */}
      <footer className="flex-none border-t border-border bg-background px-8 py-4">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto space-y-2.5">
          {/* Wrapper is relative so the popup can anchor to it */}
          <div className="relative">
            {/* @ mention popup — floats above the input */}
            {mentionQuery !== null && mentionResults.length > 0 && (
              <div className="absolute bottom-full mb-1.5 left-0 right-0 border border-border bg-background shadow-lg z-50 overflow-hidden">
                {mentionResults.map((p, i) => (
                  <button
                    key={p.arxiv_id}
                    type="button"
                    className={cn(
                      "w-full text-left px-3 py-2.5 flex flex-col gap-0.5 transition-colors",
                      i === mentionIndex ? "bg-muted" : "hover:bg-muted/50",
                    )}
                    // onMouseDown instead of onClick so the textarea doesn't lose focus
                    onMouseDown={(e) => {
                      e.preventDefault();
                      selectMention(p);
                    }}
                  >
                    <span className="text-sm font-medium line-clamp-1">
                      {p.title}
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">
                      {p.short_citation} · {p.arxiv_id}
                    </span>
                  </button>
                ))}
              </div>
            )}

            <div className="flex items-end gap-2 border border-input bg-muted/40 px-3.5 py-2.5 focus-within:border-ring focus-within:bg-background transition-all duration-150">
              <div className="flex-1 flex flex-col gap-2 min-w-0">
                {/* Pinned paper chips */}
                {pinnedPapers.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {pinnedPapers.map((p) => (
                      <span
                        key={p.arxiv_id}
                        className="inline-flex items-center gap-1 text-[11px] border border-border px-2 py-0.5 bg-muted/60"
                      >
                        <FileText className="size-3 shrink-0 text-muted-foreground" />
                        <span className="max-w-[160px] truncate font-medium">
                          {p.title}
                        </span>
                        <button
                          type="button"
                          className="ml-0.5 text-muted-foreground hover:text-foreground transition-colors"
                          onClick={() => removePinned(p.arxiv_id)}
                        >
                          <X className="size-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                <Textarea
                  ref={textareaRef}
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a research question… (type @ to pin papers)"
                  rows={1}
                  className="flex-1 min-h-6 border-0 bg-transparent p-0 shadow-none focus-visible:ring-0 rounded-none text-sm resize-none leading-6"
                />
              </div>
              {loading ? (
                <Button
                  type="button"
                  size="icon-sm"
                  onClick={handleStop}
                  className="flex-none mb-0.5"
                >
                  <Square className="size-3 fill-current" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  size="icon-sm"
                  disabled={!input.trim()}
                  className="flex-none mb-0.5"
                >
                  <ArrowUp className="size-3.5" />
                </Button>
              )}
            </div>
          </div>
          <p className="text-[11px] text-muted-foreground text-center font-normal">
            Answers are grounded in your ingested corpus · Shift+Enter for
            newline · type @ to pin specific papers
          </p>
        </form>
      </footer>
    </div>
  );
}

function MessageBlock({ message }: { message: Message }) {
  const { question, pinnedPapers, response } = message;
  const meta = TYPE_META[response.question_type] ?? {
    label: response.question_type,
    bg: "#e5e7eb",
    text: "#374151",
    border: "#d1d5db",
  };

  return (
    <div className="space-y-5">
      {/* Question */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div
            className="flex-none mt-0.5 size-8 p-0 flex items-center justify-center shrink-0"
            style={{ backgroundColor: "#AEB5FF" }}
          >
            <span
              className="text-[12px] font-extrabold leading-none"
              style={{ color: "#2e32a6" }}
            >
              Q
            </span>
          </div>
          <p className="text-lg font-semibold leading-6 tracking-[-0.01em]">
            {question.charAt(0).toUpperCase() + question.slice(1)}
          </p>
        </div>

        {/* Pinned paper chips (shown in the message history) */}
        {pinnedPapers.length > 0 && (
          <div className="flex flex-wrap gap-1.5 ml-11">
            {pinnedPapers.map((p) => (
              <span
                key={p.arxiv_id}
                className="inline-flex items-center gap-1 text-[10px] border border-border px-1.5 py-0.5 bg-muted/40 text-muted-foreground font-mono"
              >
                <FileText className="size-2.5 shrink-0" />
                {p.arxiv_id}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Answer */}
      <div className="ml-8 space-y-4">
        <div
          className="prose prose-sm prose-gray max-w-none text-foreground/80
          prose-headings:font-semibold prose-headings:text-foreground
          prose-p:leading-7 prose-p:text-foreground/80
          prose-strong:text-foreground prose-strong:font-semibold
          prose-code:text-foreground prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:text-xs prose-code:font-mono prose-code:before:content-none prose-code:after:content-none
          prose-pre:bg-muted prose-pre:border prose-pre:border-border prose-pre:text-xs
          prose-li:text-foreground/80 prose-li:leading-7
          prose-a:text-foreground prose-a:underline-offset-2"
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
          >
            {response.answer}
          </ReactMarkdown>
        </div>

        {/* Badge + latency */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <Badge
            variant="outline"
            className={cn("font-semibold text-[11px] px-2 py-0.5 border")}
            style={{
              backgroundColor: meta.bg,
              color: meta.text,
              borderColor: meta.border,
            }}
          >
            {meta.label}
          </Badge>
          <span className="flex items-center gap-1 text-[11px] text-muted-foreground font-normal">
            <Clock className="size-3" />
            {response.latency.toLocaleString()}ms
          </span>
        </div>

        {/* Citations */}
        {response.retrieved_papers.length > 0 && (
          <div className="pt-3 border-t border-border space-y-2.5">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
              Sources
            </p>
            <div className="flex flex-wrap gap-1.5">
              {response.retrieved_papers.map((paper) => (
                <CitationCard key={paper.arxiv_id} paper={paper} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CitationCard({ paper }: { paper: RetrievedPaper }) {
  return (
    <HoverCard>
      <HoverCardTrigger>
        <a
          href={`/papers/${paper.arxiv_id}`}
          className="inline-flex items-center gap-1.5 border border-border px-2.5 py-1 text-[11px] text-muted-foreground font-normal hover:border-foreground/25 hover:text-foreground transition-colors"
        >
          <FileText className="size-3" />
          {paper.arxiv_id}
        </a>
      </HoverCardTrigger>
      <HoverCardContent className="w-80">
        <p className="font-semibold text-sm">{paper.title}</p>
        <p className="text-xs text-muted-foreground mt-1 line-clamp-4">
          {paper.abstract}
        </p>
      </HoverCardContent>
    </HoverCard>
  );
}

function EmptyState({
  onSuggest,
  suggestions,
  loading,
}: {
  onSuggest: (q: string) => void;
  suggestions: SuggestionItem[];
  loading: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[52vh] gap-10 text-center">
      <style>{`
        @keyframes _fadeSlideUp {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0);   }
        }
      `}</style>

      <div className="space-y-1.5">
        <p className="text-[11px] font-mono font-medium uppercase tracking-[0.18em] text-muted-foreground/60">
          Suggested Inquiries
        </p>
        <p className="text-base font-semibold tracking-[-0.02em]">
          What would you like to explore?
        </p>
      </div>

      <div className="w-full max-w-md">
        {loading ? (
          <div className="divide-y divide-border">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="flex items-center gap-3.5 py-5">
                <Skeleton className="h-3 w-6 shrink-0" />
                <Skeleton className="h-4 w-full" />
              </div>
            ))}
          </div>
        ) : suggestions.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Ingest papers from the{" "}
            <a
              href="/papers"
              className="underline underline-offset-2 hover:text-foreground transition-colors"
            >
              Research Library
            </a>{" "}
            to see suggested questions.
          </p>
        ) : (
          <div className="divide-y divide-border text-left">
            {suggestions.map((s, i) => (
              <button
                key={s.text}
                onClick={() => onSuggest(s.text)}
                className="group relative w-full flex items-start gap-4 py-5 cursor-pointer"
                style={{
                  opacity: 0,
                  animation: `_fadeSlideUp 0.28s ease forwards`,
                  animationDelay: `${i * 70}ms`,
                }}
              >
                {/* Bibliography-style counter */}
                <span className="font-mono text-[11px] text-muted-foreground/40 shrink-0 mt-0.5 tabular-nums select-none group-hover:text-muted-foreground/70 transition-colors duration-150">
                  {String(i + 1).padStart(2, "0")}.
                </span>

                {/* Question text */}
                <span className="text-sm text-foreground/70 group-hover:text-foreground leading-snug transition-colors duration-150">
                  {s.text}
                </span>

                {/* Underline that draws left→right on hover */}
                <span className="pointer-events-none absolute bottom-0 left-0 h-px w-0 bg-foreground/20 transition-[width] duration-300 ease-out group-hover:w-full" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingBlock() {
  return (
    <div className="flex items-center gap-1.5 ml-8 py-1">
      {DOT_COLORS.map((color, i) => (
        <span
          key={i}
          className="size-1.5 animate-pulse"
          style={{ backgroundColor: color, animationDelay: `${i * 160}ms` }}
        />
      ))}
    </div>
  );
}
