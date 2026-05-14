"""Example 02: Branching — parallel chains and passthroughs.

Run with:
    uv run python examples/02_branching.py

Builds a "paper analyzer" that runs three analyses in parallel on the same
input. Teaches:
    - RunnableParallel: branch one input into many outputs
    - RunnablePassthrough: forward the input alongside new computations
    - itemgetter: pluck values out of a dict
    - How to build non-linear data flows
"""

from operator import itemgetter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from rich import print
from rich.rule import Rule

from scholar.config import settings  # noqa: F401
from scholar.models import get_chat_model

model = get_chat_model(temperature=0)

SAMPLE_ABSTRACT = """
We introduce a new family of generative models called diffusion models, which
gradually denoise random noise to produce samples. We show that diffusion models
achieve sample quality competitive with GANs on CIFAR-10 and ImageNet, while
being significantly more stable to train. Our key insight is that the reverse
diffusion process can be parameterized by a simple neural network trained with
a denoising score-matching objective.
"""


# ---------------------------------------------------------------------------
# Three small chains, each does one thing.
# ---------------------------------------------------------------------------
summarize = (
    ChatPromptTemplate.from_template("Summarize in one sentence: {text}")
    | model
    | StrOutputParser()
)

extract_claims = (
    ChatPromptTemplate.from_template("List the key claims in this text as bullet points:\n\n{text}")
    | model
    | StrOutputParser()
)

suggest_questions = (
    ChatPromptTemplate.from_template(
        "Generate 3 critical follow-up questions a reviewer would ask about this:\n\n{text}"
    )
    | model
    | StrOutputParser()
)


# ---------------------------------------------------------------------------
# RunnableParallel runs all branches in parallel on the SAME input.
# Output is a dict with one key per branch.
# ---------------------------------------------------------------------------
analyzer = RunnableParallel(
    summary=summarize,
    claims=extract_claims,
    questions=suggest_questions,
    original=RunnablePassthrough(),  # pass the input through unchanged
)

print(Rule("[bold cyan]Parallel analysis (3 LLM calls happen concurrently)[/bold cyan]"))
result = analyzer.invoke({"text": SAMPLE_ABSTRACT})

print("[bold green]Summary:[/bold green]")
print(result["summary"])
print("\n[bold green]Claims:[/bold green]")
print(result["claims"])
print("\n[bold green]Questions:[/bold green]")
print(result["questions"])


# ---------------------------------------------------------------------------
# A more interesting pattern: use the output of one stage as input to another.
# Here we summarize, then critique the summary.
# ---------------------------------------------------------------------------
critique = (
    ChatPromptTemplate.from_template(
        "Original text:\n{original_text}\n\nSummary:\n{summary}\n\n"
        "Is the summary accurate and complete? Note anything important it missed."
    )
    | model
    | StrOutputParser()
)

# This chain:
#   1. Receives {"text": "..."}
#   2. Computes a summary AND passes the original through (RunnableParallel)
#   3. Renames the keys to match what `critique` expects
#   4. Runs critique
summarize_and_critique = (
    RunnableParallel(
        summary=summarize,
        original_text=itemgetter("text"),
    )
    | critique
)

print(Rule("[bold cyan]Sequential: summarize then critique[/bold cyan]"))
critique_result = summarize_and_critique.invoke({"text": SAMPLE_ABSTRACT})
print(critique_result)
