import datetime
import json
import time
from pathlib import Path

import pydantic
from langchain_chroma import Chroma
from langchain_core.documents import Document
from pydantic import BaseModel

from scholar.evaluation.schema import EvalQuestion
from scholar.models import get_chat_model
from scholar.retrieval.config import RetrieverConfig, build_retriever
from scholar.retrieval.rag import build_rag_chain
from scholar.retrieval.vectorstore import get_embeddings, load_existing_vectorstore


class RetrievedChunk(BaseModel):
    """One chunk that the retriever returned"""

    arxiv_id: str
    page: int
    short_citation: str
    text_preview: str  # first 200 chars, for human inspection
    rank: int


class EvalRun(BaseModel):
    """Result of running on evalQuestions through scholar"""

    question_id: str
    question: str
    config_name: str

    retrieved_chunks: list[RetrievedChunk]
    generated_answer: str

    latency_ms: int
    timestamp: datetime.datetime


def run_eval(
    questions: list[EvalQuestion],
    config: RetrieverConfig,
    output_path: Path,
) -> list[EvalRun]:
    """Run every question through Scholar and save results."""
    chroma = Path("data/chroma")
    papers = {p.name for p in chroma.iterdir() if p.is_dir()}

    embeddings = get_embeddings()
    model = get_chat_model()

    eval_run_result: list[EvalRun] = []
    # load every paper vectorstore + chunk once
    stores_and_chunks: dict[str, tuple[Chroma, list[Document]]] = {}
    for paper_dir in chroma.iterdir():
        if not paper_dir.is_dir():
            continue
        vs = load_existing_vectorstore(paper_dir, embeddings)
        if vs is None:
            continue
        raw = vs.get()
        chunks = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(raw["documents"], raw["metadatas"])
        ]
        stores_and_chunks[paper_dir.name] = (vs, chunks)
    papers = set(stores_and_chunks.keys())

    for question in questions:
        expected_arxiv_ids: list[str] = question.expected_arxiv_ids

        available_papers = [arxiv_id for arxiv_id in expected_arxiv_ids if arxiv_id in papers]
        unavailable_papers = [arxiv_id for arxiv_id in expected_arxiv_ids if arxiv_id not in papers]

        if unavailable_papers:
            print(f"[{question.id}] not indexed in chroma: {unavailable_papers}")
        if not available_papers:
            print(f"[{question.id}] skipping — no papers available")
            continue

        all_chunks: list[RetrievedChunk] = []
        first_retriever = None

        for arxiv_id in available_papers:
            vectorstore, chunks = stores_and_chunks[arxiv_id]
            retriever = build_retriever(config, chunks, vectorstore)
            if retriever is None:
                continue

            if first_retriever is None:
                first_retriever = retriever  # baseline: answer using the first paper
                assert first_retriever is not None
            docs = retriever.invoke(question.question)
            for rank, doc in enumerate(docs):
                page = doc.metadata.get("page")
                if page is None:
                    page = -1  # for mssing pages
                all_chunks.append(
                    RetrievedChunk(
                        arxiv_id=arxiv_id,
                        page=page,
                        short_citation=doc.metadata.get("short_citation", "?"),
                        text_preview=doc.page_content[:200],
                        rank=rank,
                    )
                )

        if first_retriever is None:
            continue

        rag_chain = build_rag_chain(first_retriever, model)

        start = time.perf_counter()
        answer = rag_chain.invoke(question.question)
        latency_ms = int((time.perf_counter() - start) * 1000)

        eval_run_result.append(
            EvalRun(
                question_id=question.id,
                question=question.question,
                config_name=config.name,
                retrieved_chunks=all_chunks,
                generated_answer=answer,
                latency_ms=latency_ms,
                timestamp=datetime.datetime.now(),
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        for run in eval_run_result:
            f.write(run.model_dump_json() + "\n")

    return eval_run_result


def load_eval_runs(path: Path) -> list[EvalRun]:
    """
    Load eval runs from a JSONL file at the given path.
    """
    eval_runs: list[EvalRun] = []
    with path.open() as f:
        for line_no, raw in enumerate(f, start=1):
            if not raw.strip():
                continue
            data = json.loads(raw)
            try:
                eval_runs.append(EvalRun(**data))
            except pydantic.ValidationError as e:
                raise ValueError(f"Invalid run at line {line_no}: {e}") from e
    return eval_runs
