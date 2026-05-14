"""Example 03: Structured output.

Run with:
    uv run python examples/03_structured_output.py

Production LLM apps rarely want raw strings — they want validated, typed data.
This example teaches you:
    - Defining schemas with Pydantic
    - .with_structured_output() — the modern, recommended approach
    - How structured output is implemented under the hood (Gemini uses
      JSON schema response constraint; Claude/OpenAI use tool calling —
      LangChain hides that difference from you)
    - Why this is one of the most useful features in LangChain
"""

from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from rich import print
from rich.rule import Rule

from scholar.config import settings  # noqa: F401
from scholar.models import get_chat_model


# ---------------------------------------------------------------------------
# Define what we want back as a Pydantic model. The field descriptions are
# critical — the LLM reads them as instructions.
# ---------------------------------------------------------------------------
class PaperMetadata(BaseModel):
    """Structured metadata extracted from a paper's abstract."""

    title: str = Field(description="The paper's title")
    main_contribution: str = Field(
        description="The single most important contribution, in one sentence"
    )
    methods: list[str] = Field(description="Technical methods or techniques used (max 5)")
    domain: Literal["nlp", "computer_vision", "rl", "theory", "other"] = Field(
        description="The primary research domain"
    )
    novelty_score: int = Field(
        description="How novel this work seems on a scale of 1-10",
        ge=1,
        le=10,
    )


# ---------------------------------------------------------------------------
# .with_structured_output() wraps the model so it returns validated objects.
# ---------------------------------------------------------------------------
model = get_chat_model(temperature=0)
structured_model = model.with_structured_output(PaperMetadata)

prompt = ChatPromptTemplate.from_template(
    "Extract structured metadata from this paper abstract:\n\n{abstract}"
)

extractor = prompt | structured_model

ABSTRACT = """
Attention Is All You Need. The dominant sequence transduction models are based
on complex recurrent or convolutional neural networks. We propose a new simple
network architecture, the Transformer, based solely on attention mechanisms,
dispensing with recurrence and convolutions entirely. Experiments on two machine
translation tasks show these models to be superior in quality while being more
parallelizable and requiring significantly less time to train.
"""

print(Rule("[bold cyan]Structured extraction[/bold cyan]"))
result: PaperMetadata = extractor.invoke({"abstract": ABSTRACT})

# `result` is now a real Pydantic object — typed, validated, autocomplete-able
print(f"[bold]Title:[/bold] {result.title}")
print(f"[bold]Contribution:[/bold] {result.main_contribution}")
print(f"[bold]Methods:[/bold] {result.methods}")
print(f"[bold]Domain:[/bold] {result.domain}")
print(f"[bold]Novelty (LLM judgment):[/bold] {result.novelty_score}/10")

# It's still a Pydantic model, so:
print(f"\n[dim]As dict:[/dim] {result.model_dump()}")
print(f"[dim]As JSON:[/dim] {result.model_dump_json(indent=2)}")
