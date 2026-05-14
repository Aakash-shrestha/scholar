"""Example 01: The four primitives of LangChain.

Run with:
    uv run python examples/01_basics.py

By the end you'll understand:
    - How to call a chat model
    - How prompt templates work
    - What LCEL (the | operator) actually does
    - How streaming differs from invoking

NOTE ON THE PROVIDER:
    We're using Google Gemini (free tier). Notice that we import the
    model through `scholar.models.get_chat_model()`. To switch to Claude,
    OpenAI, Groq, etc., you'd change exactly ONE function in src/scholar/
    models.py. Everything below would work unchanged. That portability is
    the central design promise of LangChain.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from rich import print
from rich.rule import Rule

from scholar.config import settings  # noqa: F401 — loads env vars
from scholar.models import get_chat_model

# ---------------------------------------------------------------------------
# 1. A chat model is a Runnable. Input: messages or a string. Output: AIMessage.
# ---------------------------------------------------------------------------
model = get_chat_model(temperature=0)

print(Rule("[bold cyan]1. Calling the model directly[/bold cyan]"))
response = model.invoke("In one sentence, what is the transformer architecture?")
print(response)
print()
print(f"[dim]Just the text:[/dim] {response.content}\n")


# ---------------------------------------------------------------------------
# 2. A prompt template is a Runnable. Input: dict of vars. Output: messages.
# ---------------------------------------------------------------------------
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a precise technical explainer. Be concise."),
        (
            "user",
            "Explain {topic} to someone with a {level} background. Max {sentences} sentences.",
        ),
    ]
)

print(Rule("[bold cyan]2. Prompt templates produce messages[/bold cyan]"))
messages = prompt.invoke({"topic": "attention mechanisms", "level": "CS undergrad", "sentences": 2})
print(messages)
print()


# ---------------------------------------------------------------------------
# 3. The pipe operator chains Runnables. Output of left → input of right.
#    This is the heart of LangChain.
# ---------------------------------------------------------------------------
chain = prompt | model | StrOutputParser()
#       └─────┘   └───┘   └──────────────┘
#       dict →    msgs→   AIMessage →
#       msgs      AIMsg   string

print(Rule("[bold cyan]3. Chaining with | [/bold cyan]"))
answer = chain.invoke({"topic": "diffusion models", "level": "CS undergrad", "sentences": 3})
print(answer)
print()


# ---------------------------------------------------------------------------
# 4. Every Runnable supports .stream() — yields chunks as they arrive.
#    This is how you build "typing" UIs.
# ---------------------------------------------------------------------------
print(Rule("[bold cyan]4. Streaming[/bold cyan]"))
print("[dim]Watch this print token by token:[/dim]")

# Build a streaming-enabled version
streaming_chain = prompt | get_chat_model(temperature=0, streaming=True) | StrOutputParser()
for chunk in streaming_chain.stream(
    {
        "topic": "the curse of dimensionality",
        "level": "CS undergrad",
        "sentences": 3,
    }
):
    print(chunk, end="", flush=True)
print("\n")


# ---------------------------------------------------------------------------
# 5. .batch() runs many inputs in parallel — useful for evals.
#    With Gemini's free tier rate limits, batch sizes matter — watch your quota.
# ---------------------------------------------------------------------------
print(Rule("[bold cyan]5. Batching (parallel calls)[/bold cyan]"))
topics = ["BERT", "GPT", "T5"]
results = chain.batch([{"topic": t, "level": "CS undergrad", "sentences": 1} for t in topics])
for topic, result in zip(topics, results):
    print(f"[bold]{topic}:[/bold] {result}")
