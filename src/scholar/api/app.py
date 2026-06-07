import re
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from scholar.api.schemas import (
    AskRequest,
    AskResponse,
    IngestPaperRequest,
    IngestRefPaperRequest,
    IngestRefPaperResponse,
    PaperResponse,
)
from scholar.corpus.db import Paper, get_engine, init_db
from scholar.corpus.repository import CitationRepository, CorpusRepository
from scholar.graph.graph import create_graph
from scholar.ingestion.ingest import ingest_paper, ingest_ref_paper
from scholar.retrieval.vectorstore import get_embeddings


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    init_db(engine)
    app.state.repo = CorpusRepository(engine)
    app.state.cite_repo = CitationRepository(engine)
    app.state.embeddings = get_embeddings()
    try:
        app.state.graph = create_graph()
        print("[scholar] Graph loaded successfully.")
    except FileNotFoundError as e:
        print(f"[scholar] Graph not loaded: {e}")
        app.state.graph = None

    yield


app = FastAPI(title="Scholar API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/papers", response_model=list[PaperResponse])
def list_papers():
    papers: list[Paper] = app.state.repo.list_all()
    return [
        PaperResponse(
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            short_citation=paper.short_citation,
            abstract=paper.abstract,
            year=paper.year,
            ingested_at=paper.ingested_at,
        )
        for paper in papers
    ]


@app.post("/papers", response_model=PaperResponse)
def add_paper(request: IngestPaperRequest):
    arxiv_id = re.sub(r"^arxiv:", "", request.arxiv_id, flags=re.IGNORECASE)  # remove arxiv:
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)  # remove versioning v1..
    if app.state.repo.get(arxiv_id) is not None:
        raise HTTPException(
            status_code=400, detail=f"Paper with arXiv ID {arxiv_id} already exists"
        )
    is_ingested = ingest_paper(arxiv_id, app.state.repo, app.state.embeddings)
    if is_ingested:
        app.state.graph = create_graph()
        paper = app.state.repo.get(arxiv_id)
        return PaperResponse(
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            short_citation=paper.short_citation,
            abstract=paper.abstract,
            year=paper.year,
            ingested_at=paper.ingested_at,
        )
    raise HTTPException(status_code=500, detail="Failed to ingest paper")


@app.get("/papers/{arxiv_id}", response_model=PaperResponse)
def get_paper_by_id(arxiv_id: str):
    paper = app.state.repo.get(arxiv_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"Paper with arXiv ID {arxiv_id} not found")
    return PaperResponse(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        short_citation=paper.short_citation,
        abstract=paper.abstract,
        year=paper.year,
        ingested_at=paper.ingested_at,
    )


@app.post("/papers/{arxiv_id}/refs", response_model=IngestRefPaperResponse)
def add_ref_paper(arxiv_id: str, request: IngestRefPaperRequest):
    if app.state.repo.get(arxiv_id) is None:
        raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found")

    references, ingested, skipped, total_found = ingest_ref_paper(
        arxiv_id, app.state.repo, app.state.cite_repo, app.state.embeddings, request.limit
    )

    return IngestRefPaperResponse(
        ingest=ingested,
        skipped=skipped,
        total_found=total_found,
    )


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    if app.state.graph is None:
        raise HTTPException(status_code=503, detail="No papers ingested yet. Ingest a paper first.")
    start = time.perf_counter()
    result = app.state.graph.invoke(
        {
            "question": request.question,
            "question_type": None,
            "retrieved_docs": [],
            "sub_questions": None,
            "sub_questions_docs": None,
            "generated_answer": None,
            "relevant_paper_ids": None,
            "retry_count": 0,
            "needs_retry": False,
        }
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    return AskResponse(
        answer=result["generated_answer"],
        question=request.question,
        retrieved_arxiv_ids=result["relevant_paper_ids"] or [],
        question_type=result["question_type"],
        latency=latency_ms,
    )
