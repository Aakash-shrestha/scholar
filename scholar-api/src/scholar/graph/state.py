from typing import TypedDict

from langchain_core.documents import Document

from scholar.evaluation.schema import QuestionType


class HistoryTurn(TypedDict):
    question: str
    answer: str


class ScholarState(TypedDict):
    question: str
    question_type: QuestionType | None
    retrieved_docs: list[Document]
    sub_questions: list[str] | None
    sub_questions_docs: list[Document] | None
    generated_answer: str | None
    relevant_paper_ids: list[str] | None
    retry_count: int
    needs_retry: bool
    history: list[HistoryTurn]
