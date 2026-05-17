from pathlib import Path

from langchain_chroma.vectorstores import Chroma
from langchain_core.documents.base import Document
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings


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
