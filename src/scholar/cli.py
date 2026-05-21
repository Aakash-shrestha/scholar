import re
from pathlib import Path

import typer
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from rich import print
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from scholar.corpus.db import Paper, get_engine, init_db
from scholar.corpus.repository import CorpusRepository
from scholar.ingestion.arxiv_fetch import download_paper, enrich_chunks, fetch_arxiv_metadata
from scholar.ingestion.loader import load_and_chunk
from scholar.retrieval.rag import build_rag_chain
from scholar.retrieval.vectorstore import (
    build_vectorstore,
    get_embeddings,
    load_existing_vectorstore,
)

app = typer.Typer()
load_dotenv()


@app.command()
def ask(
    question: str, paper: Path = typer.Option(Path("data/papers/1706.03762.pdf"), "--paper")
) -> None:
    """Ask a question about a paper. Retrieves relevant context and answers with citations."""
    if not paper.exists():
        typer.echo(f"Error: paper not found: {paper}", err=True)
        raise typer.Exit(code=1)

    persistent_dir = Path("data/chroma") / paper.stem
    embeddings = get_embeddings()
    vectorstore = load_existing_vectorstore(persistent_dir, embeddings)
    if vectorstore is None:
        chunks = load_and_chunk(paper)
        vectorstore = build_vectorstore(chunks, persistent_dir, embeddings)

    retriever = vectorstore.as_retriever(search_kwargs={"k": 8})
    model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    rag_chain = build_rag_chain(retriever, model)
    response = rag_chain.invoke(question)
    print(Rule(f"[bold cyan]{question}[/bold cyan]"))
    print(response)


@app.command()
def ingest(source: str) -> None:
    """Ingest a paper from a source (currently only arXiv is supported). This will fetch the paper's
    metadata, download the PDF, chunk it, enrich the chunks with metadata, and store the chunks in a
    persistent vectorstore for retrieval."""
    engine = get_engine()
    init_db(engine)  # initializes the db if the paper db does not already exists
    corpus_repository = CorpusRepository(engine)

    arxiv_id = re.sub(r"^arxiv:", "", source, flags=re.IGNORECASE)  # remove arxiv:
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)  # remove versioning v1..

    if corpus_repository.get(arxiv_id) is not None:
        print(f"[bold yellow]Paper {arxiv_id} already ingested. Skipping ingestion.[/bold yellow]")
        raise typer.Exit()

    paper_metadata = fetch_arxiv_metadata(arxiv_id)
    paper_path = download_paper(paper_metadata)

    chunks = load_and_chunk(paper_path)
    enriched_chunks = enrich_chunks(chunks, paper_metadata)
    persistent_dir = Path("data/chroma") / arxiv_id

    embeddings = get_embeddings()
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

    print(Rule(f"[bold green]Ingested {paper_metadata.arxiv_id}[/bold green]"))
    print(f"Title: {paper_metadata.title}")
    print(f"Citation: {paper_metadata.short_citation}")
    print(f"Stored at: {persistent_dir}")


@app.command(name="list")
def list_papers() -> None:
    """Show all ingested papers as a table, or a message if none exist."""
    engine = get_engine()
    init_db(engine)
    corpus_repository = CorpusRepository(engine)
    all_papers = corpus_repository.list_all()

    if not all_papers:
        print("[bold green]No paper ingested yet[/bold green]")
        return

    table = Table(title="Corpus")
    table.add_column("arxiv_id", style="cyan")
    table.add_column("title", overflow="ellipsis")
    table.add_column("citation", style="green", overflow="ellipsis")
    table.add_column("year", justify="right")

    for paper in all_papers:
        table.add_row(paper.arxiv_id, paper.title, paper.short_citation, str(paper.year))

    console = Console()
    console.print(table)
