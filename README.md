# Scholar

A research assistant for academic papers. Built with LangChain and evaluated with a custom LLM-as-judge benchmark.

> **Status:** Phase 3 of 6 complete. Retrieval pipeline is built, measured, and reproducible. Multi-agent features are in development. See the [roadmap](#roadmap).

## What it does

Today, Scholar lets you build a small corpus of arXiv papers and ask grounded, cited questions about them:

- **Ingest papers from arXiv** by ID, with metadata, chunking, and per-paper vector stores
- **Maintain a corpus database** tracking ingested papers (SQLite + SQLAlchemy)
- **Answer questions with citations** using configurable retrieval strategies (semantic, hybrid BM25+semantic, or reranked)
- **Evaluate retrieval quality** with a hand-written test set and an LLM-as-judge harness that scores faithfulness and helpfulness
- **Compare retrieval configurations** with a Markdown report generator showing per-config metrics

The CLI exposes everything: `scholar ingest`, `scholar list`, `scholar ask`, `scholar eval`, `scholar judge`, `scholar report`.

## Why this exists

Scholar is built around that workflow — with a reproducible evaluation harness 
to measure quality at each stage.
## Tech stack

- **Orchestration:** LangChain (LangGraph coming in Phase 4)
- **LLM:** Groq Llama-3.3-70B (free tier)
- **Embeddings:** `BAAI/bge-small-en-v1.5` via HuggingFace (local, free)
- **Reranker:** `BAAI/bge-reranker-base` cross-encoder (local, free)
- **Vector store:** Chroma (persistent, per-paper)
- **Database:** SQLite + SQLAlchemy 2.0
- **PDF parsing:** PyMuPDF via `langchain-pymupdf4llm`
- **CLI:** Typer + Rich
- **Observability:** LangSmith (free tier)

## Quick start

```bash
# 1. Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and install
git clone https://github.com/YOU/scholar
cd scholar
uv sync

# 3. Set up your env (GROQ_API_KEY is required)
cp .env.example .env
# Get keys at:
#   - https://console.groq.com/keys     (free, no card)
#   - https://smith.langchain.com       (free, optional but recommended)

# 4. Ingest a paper and ask it something
uv run scholar ingest arxiv:1706.03762
uv run scholar ask "What is multi-head attention?" 
```

## Roadmap

- [x] Phase 1 — Foundations & first working RAG
- [x] Phase 2 — Robust paper ingestion (arXiv, corpus database)
- [x] Phase 3 — Advanced retrieval (hybrid, re-ranking, query rewriting, eval suite)
- [x] Phase 4 — Multi-agent LangGraph system with parallel research and a critic agent
- [ ] Phase 5 — Citation graph, contradiction detection, and structured literature reviews
- [ ] Phase 6 — Web UI, streaming reasoning, and deployment

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

## License

MIT
