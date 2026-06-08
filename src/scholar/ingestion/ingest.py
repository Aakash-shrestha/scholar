import gc
import re
import time
from pathlib import Path

from langchain_core.embeddings import Embeddings
from rich import print
from rich.rule import Rule

from scholar.corpus.db import Paper, Reference
from scholar.corpus.repository import CitationRepository, CorpusRepository, ReferenceRepository
from scholar.ingestion.arxiv_fetch import (
    download_paper,
    enrich_chunks,
    fetch_arxiv_metadata,
    search_arxiv_by_title,
)
from scholar.ingestion.extract_references import ExtractedReference, extract_references
from scholar.ingestion.loader import load_and_chunk
from scholar.retrieval.vectorstore import (
    build_abstract_vectorstore,
    build_vectorstore,
)


def ingest_paper(
    arxiv_id: str,
    corpus_repository: CorpusRepository,
    reference_repository: ReferenceRepository,
    embeddings: Embeddings,
) -> bool:
    """
    Ingest a single paper. Returns True if ingested, False if already exists.
    """
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)  # normalize: "1412.6980v9" → "1412.6980"
    if corpus_repository.get(arxiv_id) is not None:
        print(f"[bold yellow]Paper {arxiv_id} already ingested. Skipping ingestion.[/bold yellow]")
        return False

    paper_metadata = fetch_arxiv_metadata(arxiv_id)
    paper_path = download_paper(paper_metadata)

    chunks = load_and_chunk(paper_path)
    enriched_chunks = enrich_chunks(chunks, paper_metadata)
    persistent_dir = Path("data/chroma") / arxiv_id

    build_vectorstore(enriched_chunks, persistent_dir, embeddings)
    gc.collect()  # release Chroma PersistentClient before next paper
    paper_record = Paper(
        arxiv_id=arxiv_id,
        title=paper_metadata.title,
        short_citation=paper_metadata.short_citation,
        year=paper_metadata.year,
        abstract=paper_metadata.abstract,
        persist_dir=str(Path("data/chroma") / arxiv_id),
    )
    references: list[ExtractedReference] = extract_references(paper_path)
    for reference in references:
        clean_id = re.sub(r"v\d+$", "", reference.arxiv_id) if reference.arxiv_id else None
        reference_repository.add(arxiv_id, reference.title, clean_id)
    corpus_repository.add(paper_record)
    paper_path.unlink()  # delete the downloaded pdf to save space

    build_abstract_vectorstore(paper_metadata, embeddings)
    gc.collect()
    print(Rule(f"[bold green]Ingested {paper_metadata.arxiv_id}[/bold green]"))
    print(f"Title: {paper_metadata.title}")
    print(f"Citation: {paper_metadata.short_citation}")
    print(f"Stored at: {persistent_dir}")
    return True


def ingest_ref_paper(
    arxiv_id: str,
    corpus_repository: CorpusRepository,
    citation_repository: CitationRepository,
    reference_repository: ReferenceRepository,
    embeddings: Embeddings,
    limit: int = 5,
) -> tuple[list[Reference], list[str], list[str], int]:
    """
    Extract and ingest references for a paper.
    Returns (references, ingested, skipped, total_found).
    """
    paper = corpus_repository.get(arxiv_id)
    if paper is None:
        raise ValueError(f"Paper {arxiv_id} not found. Ingest it first.")

    ingested_ids: set[str] = {p.arxiv_id for p in corpus_repository.list_all()}

    ingested_papers: list[str] = []
    skipped_papers: list[str] = []
    references = reference_repository.get_by_source(arxiv_id)
    for reference in references:
        if len(ingested_papers) >= limit:
            break
        if reference.arxiv_id is None:
            result = search_arxiv_by_title(reference.title)
            if result is None:
                skipped_papers.append(reference.title)
                continue
            ref_arxiv_id = result.arxiv_id
        else:
            ref_arxiv_id = re.sub(r"v\d+$", "", reference.arxiv_id)  # strip version from stored ID

        if ref_arxiv_id in ingested_ids:
            citation_repository.add(arxiv_id, ref_arxiv_id)
            skipped_papers.append(ref_arxiv_id)
            continue

        time.sleep(5)
        is_ingested = ingest_paper(
            ref_arxiv_id, corpus_repository, reference_repository, embeddings
        )

        if is_ingested:
            ingested_papers.append(ref_arxiv_id)
            ingested_ids.add(ref_arxiv_id)  # keep set current for the rest of the loop
            citation_repository.add(arxiv_id, ref_arxiv_id)
        else:
            skipped_papers.append(ref_arxiv_id)
    return (references, ingested_papers, skipped_papers, len(references))
