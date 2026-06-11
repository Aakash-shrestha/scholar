import gc
import json
import re
import resource
import threading
import time
from contextlib import asynccontextmanager

# Raise the soft FD limit to avoid "Too many open files" with many papers
try:
    _soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (min(65536, _hard), _hard))
except Exception:
    pass

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response, StreamingResponse

from scholar.api.schemas import (
    AskRequest,
    AskResponse,
    GraphEdgeSchema,
    GraphNodeSchema,
    GraphSchema,
    IngestPaperRequest,
    IngestRefPaperRequest,
    IngestRefPaperResponse,
    PaperResponse,
    ReferenceItem,
)
from scholar.corpus.db import Paper, get_engine, init_db
from scholar.corpus.repository import CitationRepository, CorpusRepository, ReferenceRepository
from scholar.graph.graph import create_graph
from scholar.ingestion.arxiv_fetch import search_arxiv_by_title
from scholar.ingestion.ingest import ingest_paper, ingest_ref_paper
from scholar.models import get_chat_model
from scholar.retrieval.vectorstore import get_embeddings


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    init_db(engine)
    app.state.repo = CorpusRepository(engine)
    app.state.cite_repo = CitationRepository(engine)
    app.state.ref_repo = ReferenceRepository(engine)
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


@app.get("/suggestions", response_model=list[str])
def get_suggestions():
    papers = app.state.repo.list_all()
    if not papers:
        return []

    paper_list = "\n".join(f"- {p.title} ({p.year})" for p in papers[:10])
    prompt = (
        f"A researcher has these papers in their library:\n{paper_list}\n\n"
        "Generate exactly 4 short, specific research questions they might want to ask. "
        "Cover different angles: a concept definition, a methodology detail, a comparison, and a broader implication. "
        "Each question must be under 12 words. "
        "Return ONLY the 4 questions, one per line, no numbering, no bullets, no extra text."
    )
    from langchain_core.messages import HumanMessage

    model = get_chat_model(pro=False, fast=True)
    response = model.invoke([HumanMessage(content=prompt)])
    raw = response.content if hasattr(response, "content") else str(response)

    questions = []
    for line in raw.strip().split("\n"):
        clean = re.sub(r"^[\d\.\-\*\)\s]+", "", line).strip()
        if clean:
            questions.append(clean)
    return questions[:4]


@app.post("/papers", response_model=PaperResponse)
def add_paper(request: IngestPaperRequest):
    arxiv_id = re.sub(r"^arxiv:", "", request.arxiv_id, flags=re.IGNORECASE)  # remove arxiv:
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)  # remove versioning v1..
    if app.state.repo.get(arxiv_id) is not None:
        raise HTTPException(
            status_code=400, detail=f"Paper with arXiv ID {arxiv_id} already exists"
        )
    is_ingested = ingest_paper(arxiv_id, app.state.repo, app.state.ref_repo, app.state.embeddings)
    if is_ingested:
        gc.collect()  # release old Chroma stores before loading new graph
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


@app.post("/papers/{source_id}/citations/{cited_id}", status_code=201)
def add_citation(source_id: str, cited_id: str):
    if app.state.repo.get(source_id) is None:
        raise HTTPException(status_code=404, detail=f"Paper {source_id} not found")
    if app.state.repo.get(cited_id) is None:
        raise HTTPException(status_code=404, detail=f"Paper {cited_id} not found")
    app.state.cite_repo.add(source_id, cited_id)
    return Response(status_code=201)


@app.post("/papers/{arxiv_id}/refs", response_model=IngestRefPaperResponse)
def add_ref_paper(arxiv_id: str, request: IngestRefPaperRequest):
    if app.state.repo.get(arxiv_id) is None:
        raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found")

    references, ingested, skipped, total_found = ingest_ref_paper(
        arxiv_id,
        app.state.repo,
        app.state.cite_repo,
        app.state.ref_repo,
        app.state.embeddings,
        request.limit,
    )

    return IngestRefPaperResponse(
        ingest=ingested,
        skipped=skipped,
        total_found=total_found,
    )


@app.get("/graph", response_model=GraphSchema)
def get_graph():
    papers = app.state.repo.list_all()
    citations = app.state.cite_repo.list_all()
    paper_ids = {p.arxiv_id for p in papers}
    nodes = [
        GraphNodeSchema(id=p.arxiv_id, title=p.title, year=p.year, short_citation=p.short_citation)
        for p in papers
    ]
    edges = [
        GraphEdgeSchema(source=c.source_arxiv_id, target=c.cited_arxiv_id)
        for c in citations
        if c.source_arxiv_id in paper_ids and c.cited_arxiv_id in paper_ids
    ]
    return GraphSchema(nodes=nodes, edges=edges)


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
            "relevant_paper_ids": request.paper_ids or None,
            "retry_count": 0,
            "needs_retry": False,
            "history": [{"question": h.question, "answer": h.answer} for h in request.history],
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


@app.post("/ask/stream")
async def ask_stream(request: AskRequest):
    if app.state.graph is None:
        raise HTTPException(status_code=503, detail="No papers ingested yet. Ingest a paper first.")

    # input state for graph
    input_state = {
        "question": request.question,
        "question_type": None,
        "retrieved_docs": [],
        "sub_questions": None,
        "sub_questions_docs": None,
        "generated_answer": None,
        "relevant_paper_ids": request.paper_ids or None,
        "retry_count": 0,
        "needs_retry": False,
        "history": [{"question": h.question, "answer": h.answer} for h in request.history],
    }

    async def generate():
        start = time.perf_counter()
        relevant_paper_ids = []
        question_type = None

        async for event in app.state.graph.astream_events(input_state, version="v2"):
            if event["event"] == "on_chat_model_stream":
                if event.get("metadata", {}).get("langgraph_node") == "generate":
                    token = event["data"]["chunk"].content
                    if token:
                        yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
            elif event["event"] == "on_chain_end" and event["name"] == "LangGraph":
                output = event["data"].get("output", {})
                question_type = output.get("question_type")
                relevant_paper_ids = output.get("relevant_paper_ids") or []

        latency = int((time.perf_counter() - start) * 1000)
        qt = getattr(question_type, "value", question_type) or "factual"
        retrieved_papers = []
        for pid in relevant_paper_ids:
            p = app.state.repo.get(pid)
            if p:
                retrieved_papers.append({"arxiv_id": pid, "title": p.title, "abstract": p.abstract})
        yield f"data: {json.dumps({'type': 'done', 'question_type': qt, 'retrieved_papers': retrieved_papers, 'latency': latency})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/papers/{arxiv_id}/pdf")
async def get_paper_pdf(arxiv_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://arxiv.org/pdf/{arxiv_id}", follow_redirects=True)
    return Response(content=r.content, media_type="application/pdf")


@app.get("/papers/{arxiv_id}/references", response_model=list[ReferenceItem])
def get_paper_references(arxiv_id: str):
    if app.state.repo.get(arxiv_id) is None:
        raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found")
    refs = app.state.ref_repo.get_by_source(arxiv_id)
    result = []

    for ref in refs:
        ref_id = ref.arxiv_id
        if ref_id is None:
            found = search_arxiv_by_title(ref.title)
            if found is None:
                continue  # not available in arxiv
            ref_id = found.arxiv_id
        ref_id = re.sub(r"v\d+$", "", ref_id)  # strip version suffix (e.g. 1412.6980v9 → 1412.6980)
        if not re.match(r"^\d{4}\.\d{4,5}$", ref_id):
            continue  # old-format ID (e.g. hep-ex/0612020) — skip, breaks URL routing
        if ref.arxiv_id != ref_id:
            app.state.ref_repo.update_arxiv_id(arxiv_id, ref.title, ref_id)
        is_ingested = app.state.repo.get(ref_id) is not None
        result.append(ReferenceItem(title=ref.title, arxiv_id=ref_id, is_ingested=is_ingested))

    return result


@app.delete("/papers/{arxiv_id}", status_code=204)
def delete_paper(arxiv_id: str):
    deleted = app.state.repo.delete(arxiv_id, app.state.embeddings)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found")

    # rebuild the graph without the deelete paper
    gc.collect()

    def rebuild():
        try:
            app.state.graph = create_graph()
            print("[scholar] Graph rebuilt after deletion.")
        except FileNotFoundError:
            app.state.graph = None

    threading.Thread(target=rebuild, daemon=True).start()
    return Response(status_code=204)
