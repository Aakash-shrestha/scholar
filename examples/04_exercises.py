"""Example 04: YOUR TURN.

These exercises make sure the concepts stuck. Don't skip these — the only
way to learn LangChain is to build with it.

For each, write your solution in this file and run it. Share your solutions
or any blockers when you're done.

----------------------------------------------------------------------------
EXERCISE 1 — Few-shot prompting
----------------------------------------------------------------------------
Build a chain that classifies paper abstracts into one of:
    "theoretical", "empirical", "survey", "applied"

Use a ChatPromptTemplate with FOUR example abstracts + labels in the system
message, then ask it to classify a new abstract. Use .with_structured_output()
so the result is a Pydantic enum, not a string.

Why this matters: few-shot prompting is the single most reliable trick for
making LLMs follow specific output conventions.


----------------------------------------------------------------------------
EXERCISE 2 — A two-stage chain
----------------------------------------------------------------------------
Build a chain that:
    1. Takes a paper abstract
    2. Extracts the main claims (use structured output — list[str])
    3. For each claim, generates ONE specific experiment that would test it

The tricky part: step 3 has a list as input. You can either:
    (a) loop in Python and call the model for each claim
    (b) use .batch() to do it in parallel (better!)
    (c) ask the LLM to do it all in one call with structured output (best?)

Try all three approaches. Which feels cleanest? Which is fastest? Most reliable?
Mind your free-tier quota — Gemini's free tier is ~10-15 RPM, so (b) might
hit rate limits at scale.


----------------------------------------------------------------------------
EXERCISE 3 — Streaming structured output
----------------------------------------------------------------------------
Take Exercise 2's solution and make it stream. With structured output,
chunks arrive as PARTIAL objects (some fields filled, some not yet).

Watch what happens. This is exactly how production apps build "the AI is
writing..." UIs that show structured data appearing field by field.


----------------------------------------------------------------------------
EXERCISE 4 — Provider swap
----------------------------------------------------------------------------
If you got a Groq key, try this: copy `get_chat_model` from src/scholar/
models.py, modify it to return a Groq model (`ChatGroq` from langchain_groq,
model "llama-3.3-70b-versatile"), and rerun examples 1-3.

Goal: see for yourself that the rest of the code doesn't care.

If you didn't get a Groq key, skip this — we'll demonstrate the same idea
in Phase 6 with deployment.


----------------------------------------------------------------------------
EXERCISE 5 — Open-ended
----------------------------------------------------------------------------
Build any small chain that solves a problem YOU actually have. Anything.
A code-review summarizer. A meeting-notes extractor. A flashcard generator
from your textbook. The goal is to feel comfortable composing | chains
without thinking about it.

----------------------------------------------------------------------------

When done, share your solutions or paste any errors. Then we'll move to
Phase 1 Part 2: actual RAG over a real PDF.
"""
