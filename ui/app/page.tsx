"use client";

import { useState, useRef, useEffect, FormEvent, KeyboardEvent } from "react";
import { ArrowUp, Clock, FileText } from "lucide-react";
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
import type { AskResponse } from "@/lib/types";

type Message = {
  id: number;
  question: string;
  response: AskResponse;
};

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

const SUGGESTIONS: { text: string; bg: string; border: string }[] = [
  { text: "What is multi-head attention?", bg: "#95C8F3", border: "#75b2e6" },
  { text: "How does RLHF work?", bg: "#7DE198", border: "#5acc7c" },
  {
    text: "Explain the transformer architecture.",
    bg: "#AEB5FF",
    border: "#9099f5",
  },
  { text: "What is contrastive learning?", bg: "#FFDC74", border: "#f0c640" },
];

const DOT_COLORS = ["#95C8F3", "#DEACF9", "#7DE198"];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingQuestion]);

  async function submit() {
    const question = input.trim();
    if (!question || loading) return;
    setInput("");
    setError(null);
    setLoading(true);
    setPendingQuestion(question);
    try {
      const response: AskResponse = await api.ask(question);
      setMessages((prev) => [...prev, { id: Date.now(), question, response }]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Request failed.");
    } finally {
      setLoading(false);
      setPendingQuestion(null);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submit();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
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
            <EmptyState onSuggest={setInput} />
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
                      <div
                        className="flex-none mt-0.5 size-5 flex items-center justify-center shrink-0"
                        style={{ backgroundColor: "#AEB5FF" }}
                      >
                        <span
                          className="text-[9px] font-bold leading-none"
                          style={{ color: "#2e32a6" }}
                        >
                          Q
                        </span>
                      </div>
                      <p className="text-lg font-semibold leading-6 tracking-[-0.01em]">
                        {pendingQuestion}
                      </p>
                    </div>
                    <LoadingBlock />
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
          <div className="flex items-end gap-2 border border-input bg-muted/40 px-3.5 py-2.5 focus-within:border-ring focus-within:bg-background transition-all duration-150">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a research question…"
              rows={1}
              className="flex-1 min-h-6 border-0 bg-transparent p-0 shadow-none focus-visible:ring-0 rounded-none text-sm resize-none leading-6"
            />
            <Button
              type="submit"
              size="icon-sm"
              disabled={!input.trim() || loading}
              className="flex-none mb-0.5"
            >
              <ArrowUp className="size-3.5" />
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground text-center font-normal">
            Answers are grounded in your ingested corpus · Shift+Enter for
            newline
          </p>
        </form>
      </footer>
    </div>
  );
}

function MessageBlock({ message }: { message: Message }) {
  const { question, response } = message;
  const meta = TYPE_META[response.question_type] ?? {
    label: response.question_type,
    bg: "#e5e7eb",
    text: "#374151",
    border: "#d1d5db",
  };

  return (
    <div className="space-y-5">
      {/* Question */}
      <div className="flex items-center gap-3">
        <div
          className="flex-none mt-0.5 size-8 p-0 flex items-center justify-center shrink-0"
          style={{ backgroundColor: "#AEB5FF" }}
        >
          <span
            className="text-[12px]  font-extrabold leading-none"
            style={{ color: "#2e32a6" }}
          >
            Q
          </span>
        </div>
        <p className="text-lg font-semibold leading-6 tracking-[-0.01em]">
          {question.charAt(0).toUpperCase() + question.slice(1)}
        </p>
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
        {response.retrieved_arxiv_ids.length > 0 && (
          <div className="pt-3 border-t border-border space-y-2.5">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
              Sources
            </p>
            <div className="flex flex-wrap gap-1.5">
              {response.retrieved_arxiv_ids.map((id) => (
                <a
                  key={id}
                  href={`https://arxiv.org/abs/${id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 border border-border px-2.5 py-1 text-[11px] text-muted-foreground font-normal hover:border-foreground/25 hover:text-foreground transition-colors"
                >
                  <FileText className="size-3" />
                  {id}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState({ onSuggest }: { onSuggest: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[52vh] gap-8 text-center">
      <div className="space-y-1.5">
        <p className="text-base font-semibold tracking-[-0.02em]">
          What would you like to explore?
        </p>
        <p className="text-sm text-muted-foreground font-normal">
          Ask questions across your ingested research papers.
        </p>
      </div>
      <div className="w-full max-w-sm space-y-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.text}
            onClick={() => onSuggest(s.text)}
            className="w-full text-left text-sm border px-4 py-2.5 transition-all duration-100 cursor-pointer font-normal hover:opacity-80"
            style={{
              backgroundColor: s.bg + "33",
              borderColor: s.border + "88",
              color: "inherit",
            }}
          >
            {s.text}
          </button>
        ))}
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
