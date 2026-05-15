from textwrap import dedent

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from rich import print
from rich.rule import Rule

load_dotenv()


class PaperAnalysis(BaseModel):
    one_sentence_summary: str = Field(description="One sentence summary of the abstract")
    domain: str = Field(description="a single domain in which the abstract belongs to")
    key_contribution: str = Field(description="what's new in the abstract")
    novelty_score: int = Field(description="rate the abstract between 1 through 10", ge=1, le=10)
    reviewer_objections: list[str] = Field(
        description="""two skeptical questions a reviewer may ask after reading abstract"""
    )


abstract: str = dedent("""
GPT-style language models have shown impressive few-shot learning, but require massive parameter
counts. We introduce DistillLM, a knowledge distillation framework that compresses a 175B-parameter
teacher into a 7B-parameter student while retaining 95% of the few-shot performance on the SuperGLUE
benchmark.
    """).strip()

model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
structured_model = model.with_structured_output(PaperAnalysis)  # wrap the pydantic model inside the
# model

analyzer = (
    ChatPromptTemplate.from_template(
        dedent("""You're an expert paper analyzer. Analyze the following abstract:
            \n\n {abstract}""").strip()
    )
    | structured_model
)


response = analyzer.invoke({"abstract": abstract})
print(type(response).__name__)

print(Rule("[bold cyan]One Sentence Summary[/bold cyan]"))
print(response.one_sentence_summary)

print(Rule("[bold cyan]Domain[/bold cyan]"))
print(response.domain)

print(Rule("[bold cyan]Key Contribution[/bold cyan]"))
print(response.key_contribution)

print(Rule("[bold cyan]Novelty Score[/bold cyan]"))
print(f"{response.novelty_score} / 10")

print(Rule("[bold cyan]Reviewer Objections[/bold cyan]"))
print(response.reviewer_objections)
