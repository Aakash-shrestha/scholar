---
title: Scholar API
emoji: 📚
colorFrom: gray
colorTo: gray
sdk: docker
pinned: false
---

# Scholar

A research assistant for academic papers. Built with LangChain and evaluated with a custom LLM-as-judge benchmark.

## What it does

Today, Scholar lets you build a small corpus of arXiv papers and ask grounded, cited questions about them:

- **Ingest papers from arXiv** by ID, with metadata, chunking, and per-paper vector stores
- **Maintain a corpus database** tracking ingested papers (SQLite + SQLAlchemy)
- **Answer questions with citations** using configurable retrieval strategies (semantic, hybrid BM25+semantic, or reranked)
- **Evaluate retrieval quality** with a hand-written test set and an LLM-as-judge harness that scores faithfulness and helpfulness
- **Compare retrieval configurations** with a Markdown report generator showing per-config metrics

The CLI exposes everything: `scholar ingest`, `scholar list`, `scholar ask`, `scholar eval`, `scholar judge`, `scholar report`.

## Live Demo
Frontend: https://scholar-research.vercel.app
Backend: Self-hosted (run locally with uvicorn), now changed to huggingface spaces

## Why this exists

Scholar is built around that workflow — with a reproducible evaluation harness 
to measure quality at each stage.
## Tech stack

- **Orchestration:** LangChain, LangGraph
- **LLM:** Groq Llama-3.3-70B and meta-llama/Llama-4-Scout-17B-16E
- **Embeddings:** `BAAI/bge-small-en-v1.5` via HuggingFace (local, free)
- **Reranker:** `BAAI/bge-reranker-base` cross-encoder (local, free)
- **Vector store:** Chroma (persistent, per-paper)
- **Database:** SQLite + SQLAlchemy 2.0
- **PDF parsing:** PyMuPDF via `langchain-pymupdf4llm`
- **CLI:** Typer + Rich
- **Observability:** LangSmith (free tier)

## Running locally

Scholar has two parts: a **FastAPI backend** and a **Next.js frontend**. You need both running at the same time, plus ngrok if you want to connect a remotely hosted frontend to your local backend.

### 1. Backend (FastAPI)

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install dependencies
git clone https://github.com/Aakash-shrestha/scholar
cd scholar
uv sync

# Copy and fill in your API keys
cp .env.example .env
# Required: GOOGLE_API_KEY  → https://aistudio.google.com/apikey (free)
# Optional: GROQ_API_KEY    → https://console.groq.com/keys (free)
# Optional: LANGSMITH_*     → https://smith.langchain.com (free, for tracing)

# Start the backend server (runs on http://localhost:8000)
uv run uvicorn scholar.api.app:app --reload
```

### 2. Expose backend via ngrok (optional, needed if frontend is hosted remotely)

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000
# Copy the https://xxxx.ngrok-free.app URL — you'll need it for the frontend
```

### 3. Frontend (Next.js)

```bash
cd ui

# Set the backend URL
cp .env.example .env.local
# Edit .env.local and set:
# NEXT_PUBLIC_API_URL=http://localhost:8000        (if running frontend locally)
# NEXT_PUBLIC_API_URL=https://xxxx.ngrok-free.app  (if using ngrok)

# Install dependencies and start
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

### Quick start (CLI only, no frontend)

```bash
uv run scholar ingest arxiv:1706.03762
uv run scholar ask "What is multi-head attention?"
```


## Evaluation

See [evaluation/](./evaluation/) for the test set and reproducible benchmarks comparing retrieval strategies.

## Retrieval Quality

Scholar's RAG pipeline is evaluated against a hand-written test set of 28 questions
across 6 papers (Transformer, BERT, GAN, CNN survey, GPT-3, LLaMA). Each generated
answer is scored on two dimensions by an LLM-as-judge:

- **Faithfulness** (1–5): is the answer grounded in the retrieved context, or does
  it state claims the chunks don't support?
- **Helpfulness** (1–5): does the answer correctly and completely address the
  question?

These can dissociate. An answer that refuses ("the context doesn't say") is
maximally faithful but unhelpful; an answer that hallucinates a correct fact is
helpful but unfaithful. Measuring both separately surfaces which failure mode
dominates.

### Configurations Tested

| Configuration | Retrieval strategy |
|---------------|--------------------|
| `baseline`    | Semantic similarity over BGE embeddings (k=8) |
| `hybrid`      | BM25 + semantic via `EnsembleRetriever`, weighted 0.5/0.5 (k=8) |
| `reranked`    | Hybrid candidates (k=20) re-ranked by `BAAI/bge-reranker-base` to top 5 |

### Results


| Configuration | n | Faithfulness | Helpfulness |
|---------------|---|--------------|-------------|
| baseline | 28 | 4.57 ± 0.88 (1–5) | 3.64 ± 1.57 (1–5) |
| hybrid | 28 | 4.82 ± 0.61 (2–5) | 4.11 ± 1.45 (1–5) |
| reranked | 28 | 4.43 ± 1.07 (1–5) | 3.75 ± 1.40 (1–5) |
| graph | 28 | 4.68 ± 0.90 (1–5) | 3.93 ± 1.30 (1–5) |

Hybrid retrieval is the strongest configuration overall, improving both
faithfulness (+0.25) and helpfulness (+0.47) over the semantic-only baseline.
BM25 reliably surfaces chunks containing distinctive lexical markers
("28.4 BLEU", "175 billion parameters") that pure embedding similarity misses.
Graph retrievel also have a strong result overall, but just behind hybrid, it is
partially because, the eval question does not have alot of synthesis question kind,
which would possibly help improve the score of graph as well. 

### Findings

**Hybrid wins for single-paper questions.** Adding BM25 to semantic retrieval
recovers exact-match content that embeddings drown in conceptually-similar noise.

**Baseline (semantic) holds up better for cross-paper comparison questions.**
Comparison questions tend to hinge on conceptual relationships rather than
specific terminology, where embeddings have an edge over keyword matching.

**Cross-encoder reranking underperformed expectations.** On this corpus and
question set, reranking with `bge-reranker-base` reduced both metrics slightly.
The reranker appears to over-prioritize lexical overlap with the question,
sometimes filtering out useful but differently-phrased context. A larger
reranker or more training-aligned model may behave differently.

**Query rewriting (LLM-expanded queries before retrieval) helped on cross-paper
questions** by adding technical terminology that aligned the query with both
papers' vocabularies. Not shown above; tested as a follow-up.

### Limitations

The eval suite is honest about what it does and doesn't measure:

1. **Judge sees only 200-char chunk previews.** Long answers grounded in content
   outside the preview window can be incorrectly scored as unfaithful. Affects
   absolute scores; relative comparisons across configurations stay valid since
   all suffer the same truncation.

2. **Self-preference bias.** The same model family (Llama) is used for both
   generation and judging. Judges tend to rate answers from familiar models more
   favorably. A different judge model (`llama-3.1-8b-instant`) produced
   different rankings — absolute scores should be read with this in mind.

3. **Optimistic test set construction.** Questions were hand-written by the
   project author with known ground-truth answers and `expected_arxiv_ids`
   pre-tagged. Real user queries are messier and would likely score lower.

4. **Small sample size.** 28 questions is enough for relative comparison but
   too small for tight confidence intervals on the mean. The ±0.6 to ±1.6
   standard deviations are wider than the deltas between configurations for
   helpfulness — the hybrid > baseline conclusion is suggestive, not statistically
   significant.

## Note
scholar ingest_refs <arxiv_id> --limit N — extracts references from an ingested paper and auto-ingests up to N cited papers, storing citation relationships in SQLite. ArXiv API rate limits apply; use small --limit values.

## License

MIT
testing PRism
