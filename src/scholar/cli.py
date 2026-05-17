from pathlib import Path

import typer
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from rich import print
from rich.rule import Rule

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
def ask(question: str, paper: Path = typer.Option(Path("data/papers/attention.pdf"), "--paper")):
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
