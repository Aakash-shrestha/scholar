import json
from textwrap import dedent
from typing import Any, cast

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from scholar.config import settings
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
    model = get_chat_model(pro=False, fast=True)
    prompt = ChatPromptTemplate.from_template(
        dedent("""
           Classify the following question into exactly one of these categories.
           Categories:
               - FACTUAL – asks for a specific fact, date, number, or event (e.g. "When was X founded?")
               - DEFINITIONAL – asks for the meaning or explanation of a term (e.g. "What is X?")
               - COMPARISON – asks to compare or contrast two or more things (e.g. "How does X differ from Y?")
               - NEGATIVE – asks what is not the case, or involves negation (e.g. "What does X not include?")
               - SYNTHESIS – requires tracing evolution, progression, or combining insights across
                 multiple works over time (e.g. "How has X evolved from A to B?",
                 "What are the combined implications of X and Y?")
           Question: {question}
           Respond ONLY with a JSON object like: {{"question_type": "FACTUAL"}}
           No other text.
           """).strip()
    )
    chain = prompt | model | StrOutputParser()
    raw = chain.invoke({"question": state["question"]})
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(clean)
    return {"question_type": QuestionType(data["question_type"].lower())}


def find_relevant_paper_node(
    state: ScholarState, stores: dict[str, Chroma], embeddings: Embeddings
) -> dict[str, Any]:
    if (state["question_type"]) in (QuestionType.DEFINITIONAL, QuestionType.SYNTHESIS):
        return {"relevant_paper_ids": list(stores.keys())}
    collection = Chroma(
        persist_directory=str(settings.chroma_dir / "abstracts"),
        embedding_function=embeddings,
    )
    query = state["question"]
    results = collection.similarity_search(query, k=3)
    arxiv_ids = [doc.metadata["arxiv_id"] for doc in results]
    return {"relevant_paper_ids": arxiv_ids}


def retrieve_baseline_node(state: ScholarState, stores: dict[str, Chroma]) -> dict[str, Any]:
    merged_docs: list[Document] = []
    relevant_paper_ids = state["relevant_paper_ids"] or list(stores.keys())
    for arxiv_id, store in stores.items():
        if arxiv_id not in relevant_paper_ids:
            continue
        retriever = store.as_retriever(search_kwargs={"k": 8})
        retrieved_docs = retriever.invoke(state["question"])
        merged_docs.extend(retrieved_docs[:3])
    return {"retrieved_docs": merged_docs}


def retrieve_hybrid_node(
    state: ScholarState, stores: dict[str, Chroma], chunks: dict[str, list[Document]]
) -> dict[str, Any]:
    merged_docs: list[Document] = []
    relevant_paper_ids = state["relevant_paper_ids"] or list(stores.keys())

    for arxiv_id, store in stores.items():
        if arxiv_id not in relevant_paper_ids:
            continue
        paper_chunk = chunks[arxiv_id]
        retriever = get_hybrid_retriever(paper_chunk, store)
        retrieved_docs = retriever.invoke(state["question"])
        merged_docs.extend(retrieved_docs[:3])
    return {"retrieved_docs": merged_docs}


def decompose_node(state: ScholarState) -> dict[str, Any]:
    model = get_chat_model(pro=False, fast=True)
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
    relevant_paper_ids = state["relevant_paper_ids"] or list(stores.keys())

    for question in sub_questions:
        for arxiv_id, store in stores.items():
            if arxiv_id not in relevant_paper_ids:
                continue
            retriever = store.as_retriever(search_kwargs={"k": 3})
            retrieved_docs = retriever.invoke(question)
            merged_docs.extend(retrieved_docs[:1])

    return {"sub_questions_docs": merged_docs}


def generate_node(state: ScholarState) -> dict[str, Any]:
    docs: list[Document] = []

    if state["sub_questions_docs"]:
        docs = state["sub_questions_docs"]
    else:
        docs = state["retrieved_docs"]

    model = get_chat_model(pro=False, fast=True)

    rag_chain = build_rag_chain_from_docs(docs, model)
    answer = rag_chain.invoke(state["question"])

    return {"generated_answer": answer}
