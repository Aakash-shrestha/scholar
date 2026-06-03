from textwrap import dedent
from typing import Any, cast

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from scholar.evaluation.schema import QuestionType
from scholar.graph.state import ScholarState
from scholar.models import get_chat_model
from scholar.retrieval.hybrid import get_hybrid_retriever
from scholar.retrieval.rag import build_rag_chain_from_docs


class Classification(BaseModel):
    question_type: QuestionType


class Decomposition(BaseModel):
    sub_questions: list[str]


def classify_node(state: ScholarState) -> dict[str, Any]:
    model = get_chat_model(pro=False)
    prompt = ChatPromptTemplate.from_template(
        dedent("""
        Classify the following question into exactly one of these categories.

        Categories:
        - FACTUAL – asks for a specific fact, date, number, or event (e.g. "When was X founded?")
        - DEFINITIONAL – asks for the meaning or explanation of a term (e.g. "What is X?")
        - COMPARISON – asks to compare or contrast two or more things (e.g. "How does X differ from Y?")
        - NEGATIVE – asks what is not the case, or involves negation (e.g. "What does X not include?")
        - SYNTHESIS – requires the question to be decomposed into sub question (eg. "What is X and How is X different from Y?")

        Question: {question}
        """).strip()
    )
    structured_model = model.with_structured_output(Classification)
    result = cast(
        Classification, (prompt | structured_model).invoke({"question": state["question"]})
    )
    return {"question_type": result.question_type}


def retrieve_baseline_node(state: ScholarState, stores: dict[str, Chroma]) -> dict[str, Any]:
    merged_docs: list[Document] = []
    for store in stores.values():
        retriever = store.as_retriever(search_kwargs={"k": 8})
        retrieved_docs = retriever.invoke(state["question"])
        merged_docs.extend(retrieved_docs)
    return {"retrieved_docs": merged_docs}


def retrieve_hybrid_node(
    state: ScholarState, stores: dict[str, Chroma], chunks: dict[str, list[Document]]
) -> dict[str, Any]:
    merged_docs: list[Document] = []
    for arxiv_id, store in stores.items():
        paper_chunk = chunks[arxiv_id]
        retriever = get_hybrid_retriever(paper_chunk, store)
        retrieved_docs = retriever.invoke(state["question"])
        merged_docs.extend(retrieved_docs)
    return {"retrieved_docs": merged_docs}


def decompose_node(state: ScholarState) -> dict[str, Any]:
    model = get_chat_model(pro=False)
    prompt = ChatPromptTemplate.from_template(
        dedent("""
            You are a question decomposition assistant.

            Break down the following question into clear, focused sub-questions that together
            cover the full scope of the original question.

            Rules:
            - Each sub-question must be self-contained and answerable independently
            - Avoid redundancy between sub-questions
            - Preserve the original intent and scope
            - If the question is already atomic (cannot be broken down), return it as-is
            - Generate between 2 to 4 sub questions, not more than that

            Question: {question}
        """).strip()
    )

    structured_model = model.with_structured_output(Decomposition)
    result = cast(
        Decomposition, (prompt | structured_model).invoke({"question": state["question"]})
    )
    return {"sub_questions": result.sub_questions}


def retrieve_multi_node(state: ScholarState, stores: dict[str, Chroma]) -> dict[str, Any]:
    sub_questions = state["sub_questions"]
    assert sub_questions is not None

    merged_docs: list[Document] = []

    for question in sub_questions:
        for store in stores.values():
            retriever = store.as_retriever(search_kwargs={"k": 8})
            retrieved_docs = retriever.invoke(question)
            merged_docs.extend(retrieved_docs)

    return {"sub_questions_docs": merged_docs}


def generate_node(state: ScholarState) -> dict[str, Any]:
    docs: list[Document] = []

    if state["sub_questions_docs"]:
        docs = state["sub_questions_docs"]
    else:
        docs = state["retrieved_docs"]

    model = get_chat_model(pro=False)

    rag_chain = build_rag_chain_from_docs(docs, model)
    answer = rag_chain.invoke(state["question"])

    return {"generated_answer": answer}
