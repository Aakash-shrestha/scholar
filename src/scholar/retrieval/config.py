from typing import Literal

from langchain_chroma import Chroma
from langchain_core.documents import Document
from pydantic import BaseModel

from scholar.evaluation.reranker import get_reranked_retriever
from scholar.retrieval.hybrid import get_hybrid_retriever


class RetrieverConfig(BaseModel):
    """Configuration for the Retriever component, which handles document retrieval and embedding."""

    name: str
    kind: Literal["semantic", "hybrid", "reranked"]
    k: int = 8
    weight: list[float] | None = None  # only used by hybrd
    top_n: int | None = None  # for reranked retriever
    rewrite: bool | None = None


def build_retriever(config: RetrieverConfig, chunks: list[Document], vectorstore: Chroma):
    """Build a retriever based on the provided configuration."""
    if config.kind == "semantic":
        return vectorstore.as_retriever(search_kwargs={"k": config.k})
    elif config.kind == "hybrid":
        return get_hybrid_retriever(
            chunks, vectorstore, k=config.k, weights=config.weight or [0.5, 0.5]
        )
    elif config.kind == "reranked":
        return get_reranked_retriever(
            base_retriever=get_hybrid_retriever(
                chunks, vectorstore, k=config.k, weights=config.weight or [0.5, 0.5]
            ),
            top_n=config.top_n or 5,
        )
