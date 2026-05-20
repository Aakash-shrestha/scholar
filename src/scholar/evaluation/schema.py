import json
from enum import Enum
from pathlib import Path
from textwrap import dedent

import pydantic
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    """Categorizes eval questions by reasoning pattern required."""

    FACTUAL = "factual"
    DEFINITIONAL = "definitional"
    SYNTHESIS = "synthesis"
    COMPARISON = "comparison"
    NEGATIVE = "negative"


class EvalQuestion(BaseModel):
    """A single test case for Scholar's RAG quality."""

    model_config = {"extra": "forbid"}
    id: str = Field(description="unique simple identifier like q001")
    question: str = Field(description="question a user asks to scholar")
    question_type: QuestionType
    expected_arxiv_ids: list[str] = Field(
        default_factory=list,
        description=dedent("""papers that should be the source
        of the answer""").strip(),
    )
    expected_pages: list[int] = Field(
        default_factory=list,
        description="page number (1-indexed) where the answers can be found within a paper",
    )
    reference_answer: str = Field(description="correct answer, used by llm-as-judge for grading")
    notes: str | None = Field(default=None, description="optional human notes")


def load_questions(path: Path) -> list[EvalQuestion]:
    questions: list[EvalQuestion] = []
    with path.open() as f:
        for line_no, raw in enumerate(f, start=1):
            if not raw.strip():
                continue
            data = json.loads(raw)
            try:
                questions.append(EvalQuestion(**data))
            except pydantic.ValidationError as e:
                raise ValueError(f"Invalid question at line {line_no}: {e}") from e
    return questions
