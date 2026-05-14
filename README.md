# Scholar

An autonomous research assistant for academic papers. Built with LangChain, LangGraph, and Google Gemini.

> **Status:**  In active development. See the [roadmap](#roadmap) for what's working and what's coming.

## What it does

Scholar helps researchers and curious learners go deep on any academic topic. Give it a question, point it at a corpus of papers, and it will:

- **Ingest papers** from arXiv, Semantic Scholar, or PDFs you upload
- **Build a citation graph** linking papers to what they cite and what cites them
- **Answer multi-hop questions** by retrieving and synthesizing across many papers
- **Surface contradictions** when papers disagree — with verbatim quotes from each
- **Generate literature reviews** as structured, fully-cited surveys
- **Stream its reasoning** so you can watch the agents think and intervene

## Why this exists

LLMs are great at summarizing one paper. They struggle with the real research workflow: synthesizing across dozens of sources, tracking who claimed what, and noticing when the literature contradicts itself. Scholar is built around that workflow.

## Architecture

```
                    ┌─────────────┐
                    │   Planner   │  breaks question into sub-questions
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │Researcher│  │Researcher│  │Researcher│  parallel retrieval
        └────┬────┘  └────┬────┘  └────┬────┘
             └────────────┼────────────┘
                          ▼
                    ┌─────────┐
                    │  Critic │  flags gaps, can route back
                    └────┬────┘
                         ▼
                    ┌─────────┐
                    │  Writer │  synthesizes with citations
                    └─────────┘
```

## Tech stack

- **Orchestration:** LangChain + LangGraph
- **LLM:** Google Gemini 2.5 Flash (free tier, no credit card needed)
- **Embeddings:** Gemini `text-embedding-004` (also free)
- **Vector store:** Chroma (dev) → pgvector (production)
- **PDF parsing:** PyMuPDF + pymupdf4llm
- **Observability:** LangSmith (free tier)
- **Backend (later):** FastAPI + LangServe
- **Frontend (later):** Next.js + Vercel AI SDK

## Quick start

```bash
# 1. Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and install
git clone https://github.com/YOU/scholar
cd scholar
uv sync

# 3. Set up your env (only GOOGLE_API_KEY is strictly required)
cp .env.example .env
# Then get keys at:
#   - https://aistudio.google.com/apikey  (free, no card)
#   - https://smith.langchain.com         (free)

# 4. Try the examples
uv run python examples/01_basics.py
uv run python examples/02_branching.py
uv run python examples/03_structured_output.py
```

## Roadmap

- [x] Phase 1 — Foundations & first working RAG
- [ ] Phase 2 — Robust paper ingestion (arXiv, citation extraction)
- [ ] Phase 3 — Advanced retrieval (hybrid, re-ranking, eval suite)
- [ ] Phase 4 — Multi-agent LangGraph system
- [ ] Phase 5 — Contradiction detection & literature reviews
- [ ] Phase 6 — Web UI, deployment, full polish

## Evaluation

See [evaluation/](./evaluation/) for the test set and reproducible benchmarks comparing retrieval strategies.

## License

MIT
