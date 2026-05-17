import os
from zipfile import Path

from langchain_chroma.vectorstores import Chroma
from langchain_core.documents.base import Document
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings


def get_embeddings() -> Embeddings:
    """Returns a huggingface embedding instance"""
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return embeddings


def build_or_load_vectorstore(
    chunks: list[Document], persistent_dir: str | Path, embeddings: Embeddings
) -> Chroma:
    """Create a Chroma vectorstore from chunks and embedding instance in a persistent_dir
    Args:
        chunks: a list of chunked documents
        persistent_dir: path to persistent storage, where vectorstore are stored
        embeddings: insatnce of Huggingface embedding
    Returns:
        a chroma vector database instance, which is either created from the chunks or loaded from
        persistent_dir if it already exists
    """

    if not os.path.exists(persistent_dir if persistent_dir is str else str(persistent_dir)):
        vectorstore = Chroma.from_documents(
            documents=chunks, persistent_directory=persistent_dir, embedding=embeddings
        )
    else:
        vectorstore = Chroma(persist_directory=str(persistent_dir), embedding_function=embeddings)
    return vectorstore
