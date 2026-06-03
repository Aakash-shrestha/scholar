from pathlib import Path

from langchain_chroma.vectorstores import Chroma
from langchain_core.documents.base import Document
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from scholar.config import settings
from scholar.ingestion.arxiv_fetch import ArxivMetadata


def get_embeddings() -> Embeddings:
    """Returns a huggingface embedding instance"""
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return embeddings


def load_existing_vectorstore(persist_dir: Path, embeddings: Embeddings) -> Chroma | None:
    """returns existing store if it exists, or None if it does not"""
    if not persist_dir.exists():
        return None
    return Chroma(persist_directory=str(persist_dir), embedding_function=embeddings)


def build_vectorstore(
    chunks: list[Document], persist_dir: str | Path, embeddings: Embeddings
) -> Chroma:
    """Create a new Chroma vectorstore from chunks and embedding instance in a persistent_dir
    Args:
        chunks: a list of chunked documents
        persistent_dir: path to persistent storage, where vectorstore are stored
        embeddings: insatnce of Huggingface embedding
    Returns:
        a chroma vector database instance, which is either created from the chunks
    """

    return Chroma.from_documents(
        documents=chunks, embedding=embeddings, persist_directory=str(persist_dir)
    )


def load_all_vectorstore() -> tuple[dict[str, Chroma], dict[str, list[Document]]]:
    embeddings = get_embeddings()
    dirs = [d for d in settings.chroma_dir.iterdir() if d.is_dir() and d.name != "abstracts"]
    if not dirs:
        raise FileNotFoundError(f"No vectorstores found in {settings.chroma_dir}")
    stores: dict[str, Chroma] = {
        d.name: s for d in dirs if (s := load_existing_vectorstore(d, embeddings)) is not None
    }
    chunks: dict[str, list[Document]] = {}
    for name, store in stores.items():
        raw = store.get()
        chunks[name] = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(raw["documents"], raw["metadatas"])
        ]

    return stores, chunks


def build_abstract_vectorstore(metadata: ArxivMetadata, embeddings: Embeddings) -> Chroma:
    persist_dir = str(settings.chroma_dir / "abstracts")
    collection = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    document = Document(page_content=metadata.abstract, metadata={"arxiv_id": metadata.arxiv_id})
    collection.add_documents([document])
    return collection
