# Scholar Evaluation Report

Generated: 2026-06-02T16:26:49
Total Questions: 28

## Summary

| Configuration | n | Faithfulness | Helpfulness |
|---------------|---|--------------|-------------|
| baseline | 28 | 4.57 ± 0.88 (1–5) | 3.64 ± 1.57 (1–5) |
| hybrid | 28 | 4.82 ± 0.61 (2–5) | 4.11 ± 1.45 (1–5) |
| reranked | 28 | 4.43 ± 1.07 (1–5) | 3.75 ± 1.40 (1–5) |

## Notes

Scores produced by `llama-4-scout` as judge with JSON output parsing.
Context passed to judge was the first 200 chars of each retrieved chunk.
Judge model selection affects scores significantly — results with `llama-3.1-8b-instant` showed different rankings.