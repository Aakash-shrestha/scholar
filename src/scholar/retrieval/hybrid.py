from langchain_chroma.vectorstores import Chroma
from langchain_classic.retrievers.ensemble import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document


def get_hybrid_retriever(
    chunks: list[Document],
    vectorstore: Chroma,
    k: int = 8,
    weights: list[float] = [0.5, 0.5],
) -> EnsembleRetriever:
    """Build a hybrid retriever combining BM25 and semantic search.

    Args:
        chunks: full list of chunks (needed by BM25 to build its index)
        vectorstore: existing Chroma store (provides the semantic retriever)
        k: total chunks to return after merging
        weights: [bm25_weight, semantic_weight], should sum to 1.0
    """
    bm25 = BM25Retriever.from_documents(chunks)  # bm25 uses chunks instead of embedding because it
    # builds its own index based on the raw text. The vectorstore is only used for the semantic
    # retriever.
    bm25.k = k  # retrieves top k results
    semantic = vectorstore.as_retriever(search_kwargs={"k": k})
    return EnsembleRetriever(retrievers=[bm25, semantic], weights=weights)
