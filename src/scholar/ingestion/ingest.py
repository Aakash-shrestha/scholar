from pathlib import Path

from langchain_core.embeddings import Embeddings
from rich import print
from rich.rule import Rule

from scholar.corpus.db import Paper
from scholar.corpus.repository import CorpusRepository
from scholar.ingestion.arxiv_fetch import download_paper, enrich_chunks, fetch_arxiv_metadata
from scholar.ingestion.loader import load_and_chunk
from scholar.retrieval.vectorstore import (
    build_abstract_vectorstore,
    build_vectorstore,
)


def ingest_paper(
    arxiv_id: str, corpus_repository: CorpusRepository, embeddings: Embeddings
) -> bool:
    """
    Ingest a single paper. Returns True if ingested, False if already exists.
    """
    if corpus_repository.get(arxiv_id) is not None:
        print(f"[bold yellow]Paper {arxiv_id} already ingested. Skipping ingestion.[/bold yellow]")
        return False

    paper_metadata = fetch_arxiv_metadata(arxiv_id)
    paper_path = download_paper(paper_metadata)

    chunks = load_and_chunk(paper_path)
    enriched_chunks = enrich_chunks(chunks, paper_metadata)
    persistent_dir = Path("data/chroma") / arxiv_id

    build_vectorstore(enriched_chunks, persistent_dir, embeddings)
    paper_record = Paper(
        arxiv_id=arxiv_id,
        title=paper_metadata.title,
        short_citation=paper_metadata.short_citation,
        year=paper_metadata.year,
        abstract=paper_metadata.abstract,
        pdf_path=str(paper_path),
        persist_dir=str(Path("data/chroma") / arxiv_id),
    )

    corpus_repository.add(paper_record)
    build_abstract_vectorstore(paper_metadata, embeddings)
    print(Rule(f"[bold green]Ingested {paper_metadata.arxiv_id}[/bold green]"))
    print(f"Title: {paper_metadata.title}")
    print(f"Citation: {paper_metadata.short_citation}")
    print(f"Stored at: {persistent_dir}")
    return True
